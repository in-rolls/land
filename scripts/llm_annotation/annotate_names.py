from __future__ import annotations

import argparse
import json
import random
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.parquet as pq
from openai import OpenAI
from pydantic import ValidationError
from tqdm import tqdm

from prompt import SYSTEM_PROMPT
from schema import BatchAnnotationResponse, IndexedNameAnnotationResponse, NameAnnotationRecord


# ============================================================
# TOLERANT PIPELINE:
# - Does NOT crash if the model returns fewer outputs than inputs.
# - Writes whatever validated annotations it got.
# - Logs missing items to a separate JSONL (for optional later repair).
# - Resume works by skipping names already in output JSONL.
# - Optional final "left-merge" back to original names to produce a parquet.
# ============================================================


# --------- Rate limiting + retries ----------
@dataclass
class Throttle:
    rpm: float
    last_t: float = field(default=0.0, repr=False)

    def wait(self) -> None:
        if self.rpm <= 0:
            return
        min_interval = 60.0 / self.rpm
        now = time.time()
        elapsed = now - self.last_t
        if elapsed < min_interval:
            time.sleep(min_interval - elapsed + random.uniform(0, 0.05))
        self.last_t = time.time()


def retry_with_backoff(fn, *, max_attempts: int = 8, base_delay: float = 1.0) -> Any:
    delay = base_delay
    for attempt in range(max_attempts):
        try:
            return fn()
        except Exception as e:
            msg = str(e).lower()
            transient = ("rate limit", "429", "timeout", "connection", "temporarily", "overloaded")
            if not any(sig in msg for sig in transient) or attempt == max_attempts - 1:
                raise
            time.sleep(delay + random.uniform(0, 0.2 * delay))
            delay *= 2


def _format_user_input(items: List[Tuple[int, str]]) -> str:
    """User message pins (idx,name) pairs and asks the model to echo idx."""
    n = len(items)
    payload = [{"idx": i, "name": s} for i, s in items]
    return (
        f"You are given exactly {n} items. Each item has an integer idx and a name string.\n"
        "Return ONE annotation per item.\n"
        "You MUST echo the same idx value in each annotation object.\n"
        "Do NOT deduplicate. Do NOT skip items.\n"
        "If unsure, use 'cannot decide' and lower confidence.\n\n"
        "ITEMS_JSON:\n"
        f"{json.dumps(payload, ensure_ascii=False)}"
    )


def annotate_items_once(
    client: OpenAI,
    model: str,
    items: List[Tuple[int, str]],
    max_output_tokens: int,
    throttle: Throttle,
) -> List[IndexedNameAnnotationResponse]:
    """Single attempt: may return fewer items; caller decides what to do."""

    def _call():
        throttle.wait()
        return client.responses.parse(
            model=model,
            instructions=SYSTEM_PROMPT,
            input=[{"role": "user", "content": _format_user_input(items)}],
            text_format=BatchAnnotationResponse,
            max_output_tokens=max_output_tokens,
        )

    resp = retry_with_backoff(_call)
    parsed: BatchAnnotationResponse = resp.output_parsed
    return parsed.annotations


def load_done_names(path: Path) -> set[str]:
    """Load names already written to output (for resume only)."""
    if not path.exists():
        return set()
    names: set[str] = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                nm = obj.get("name")
                if nm:
                    names.add(nm)
            except json.JSONDecodeError:
                continue
    return names


def write_missing(missing_path: Path, names: List[str], reason: str) -> None:
    missing_path.parent.mkdir(parents=True, exist_ok=True)
    with open(missing_path, "a", encoding="utf-8") as f:
        for nm in names:
            f.write(json.dumps({"name": nm, "reason": reason}, ensure_ascii=False) + "\n")


def merge_left_to_parquet(
    input_parquet: str,
    column: str,
    annotations_jsonl: Path,
    merged_parquet: Path,
) -> None:
    """
    Left-merge annotations back onto the original parquet (by exact name string).
    Output is a parquet with original columns plus annotation fields where available.
    """
    # Read original table (could be large; for unique names parquet it's usually manageable).
    left = pq.read_table(input_parquet)

    # Read annotations jsonl
    rows = []
    with open(annotations_jsonl, "r", encoding="utf-8") as f:
        for line in f:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    if not rows:
        raise RuntimeError("No annotations found; nothing to merge.")

    right = pa.Table.from_pylist(rows)

    # Ensure join key exists on both sides.
    if column not in left.column_names:
        raise KeyError(f"Column '{column}' not found in input parquet.")

    if "name" not in right.column_names:
        raise KeyError("Field 'name' not found in annotations JSONL.")

    # Left join: left[column] == right['name']
    # Use pyarrow join (requires same type)
    left_key = pc.cast(left[column], pa.string())
    right_key = pc.cast(right["name"], pa.string())

    left2 = left.set_column(left.schema.get_field_index(column), column, left_key)
    right2 = right.set_column(right.schema.get_field_index("name"), "name", right_key)

    merged = left2.join(right2, keys=[column], right_keys=["name"], join_type="left outer")

    merged_parquet.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(merged, merged_parquet)


def main() -> None:
    ap = argparse.ArgumentParser(description="Annotate Bihar land record names (tolerant, resumable)")
    ap.add_argument("--input", required=True, help="Input parquet path (should contain unique names)")
    ap.add_argument("--column", required=True, help="Column with name strings")
    ap.add_argument("--output", required=True, help="Output JSONL path for annotations")
    ap.add_argument("--missing-output", default="", help="Optional JSONL path to log missing items")
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--chunk-size", type=int, default=25)
    ap.add_argument("--max-rows", type=int, default=0, help="Cap for testing (0=all)")
    ap.add_argument("--rpm", type=float, default=60.0, help="Requests per minute (0=unlimited)")
    ap.add_argument("--max-output-tokens", type=int, default=16000)

    ap.add_argument(
        "--merged-parquet",
        default="",
        help="Optional output parquet path: left-merge annotations back onto input parquet",
    )

    args = ap.parse_args()

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    missing_path = Path(args.missing_output) if args.missing_output else None

    done_names = load_done_names(output_path)
    if done_names:
        print(f"Resuming: {len(done_names):,} names already annotated")

    pf = pq.ParquetFile(args.input)
    total_rows = pf.metadata.num_rows
    if args.max_rows > 0:
        total_rows = min(total_rows, args.max_rows)

    # Progress tracks *newly written* annotations; start at existing count.
    pbar = tqdm(total=total_rows, initial=len(done_names), desc="Names", unit="name")

    client = OpenAI()
    throttle = Throttle(rpm=args.rpm)

    buffer: List[str] = []
    seen = 0

    with open(output_path, "a", encoding="utf-8") as out_f:
        for batch in pf.iter_batches(batch_size=50_000, columns=[args.column]):
            for raw in batch.column(0).to_pylist():
                if raw is None:
                    continue

                name = str(raw).strip()
                if not name:
                    continue

                seen += 1
                if args.max_rows > 0 and seen > args.max_rows:
                    break

                if name in done_names:
                    continue

                buffer.append(name)

                if len(buffer) >= args.chunk_size:
                    items = list(enumerate(buffer))
                    try:
                        anns = annotate_items_once(
                            client=client,
                            model=args.model,
                            items=items,
                            max_output_tokens=args.max_output_tokens,
                            throttle=throttle,
                        )
                    except ValidationError as e:
                        tqdm.write(f"⚠️  Schema validation error for batch size {len(items)}: {e}")
                        if missing_path:
                            write_missing(missing_path, buffer, reason="schema_validation_error")
                        buffer.clear()
                        continue

                    # Build idx->ann map, accept only sane idxs
                    ann_map: Dict[int, IndexedNameAnnotationResponse] = {}
                    for ann in anns:
                        if 0 <= ann.idx < len(items):
                            ann_map[ann.idx] = ann

                    # Write successes; log missing; do not crash
                    successes = 0
                    missing_names: List[str] = []

                    for idx, nm in items:
                        ann = ann_map.get(idx)
                        if ann is None:
                            missing_names.append(nm)
                            continue
                        rec = NameAnnotationRecord.from_idx_and_ann(name=nm, idx=idx, ann=ann)
                        out_f.write(json.dumps(rec.model_dump(), ensure_ascii=False) + "\n")
                        done_names.add(nm)
                        successes += 1

                    out_f.flush()

                    if missing_names:
                        tqdm.write(
                            f"⚠️  Batch returned {len(ann_map)}/{len(items)} annotations; "
                            f"{len(missing_names)} missing (continuing)."
                        )
                        if missing_path:
                            write_missing(missing_path, missing_names, reason="missing_output_in_batch")

                    if successes:
                        pbar.update(successes)
                    buffer.clear()

            if args.max_rows > 0 and seen > args.max_rows:
                break

        # Flush remaining
        if buffer:
            items = list(enumerate(buffer))
            try:
                anns = annotate_items_once(
                    client=client,
                    model=args.model,
                    items=items,
                    max_output_tokens=args.max_output_tokens,
                    throttle=throttle,
                )
            except ValidationError as e:
                tqdm.write(f"⚠️  Schema validation error for final batch size {len(items)}: {e}")
                if missing_path:
                    write_missing(missing_path, buffer, reason="schema_validation_error")
                buffer.clear()
            else:
                ann_map: Dict[int, IndexedNameAnnotationResponse] = {}
                for ann in anns:
                    if 0 <= ann.idx < len(items):
                        ann_map[ann.idx] = ann

                successes = 0
                missing_names: List[str] = []
                for idx, nm in items:
                    ann = ann_map.get(idx)
                    if ann is None:
                        missing_names.append(nm)
                        continue
                    rec = NameAnnotationRecord.from_idx_and_ann(name=nm, idx=idx, ann=ann)
                    out_f.write(json.dumps(rec.model_dump(), ensure_ascii=False) + "\n")
                    done_names.add(nm)
                    successes += 1
                out_f.flush()

                if missing_names:
                    tqdm.write(
                        f"⚠️  Final batch returned {len(ann_map)}/{len(items)} annotations; "
                        f"{len(missing_names)} missing."
                    )
                    if missing_path:
                        write_missing(missing_path, missing_names, reason="missing_output_in_batch")

                if successes:
                    pbar.update(successes)

    pbar.close()
    print(f"Done. Output: {output_path}")

    if args.missing_output:
        print(f"Missing log: {args.missing_output}")

    if args.merged_parquet:
        merged_path = Path(args.merged_parquet)
        print("Merging annotations back onto input parquet (left join)...")
        merge_left_to_parquet(
            input_parquet=args.input,
            column=args.column,
            annotations_jsonl=output_path,
            merged_parquet=merged_path,
        )
        print(f"Merged parquet: {merged_path}")


if __name__ == "__main__":
    main()