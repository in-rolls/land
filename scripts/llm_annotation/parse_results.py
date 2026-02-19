from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from tqdm import tqdm


def load_manifest(path: Path) -> Dict[str, List[str]]:
    m: Dict[str, List[str]] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            m[obj["custom_id"]] = obj["names"]
    return m


def extract_body(obj: dict) -> Optional[dict]:
    # Batch results usually: {"custom_id":..., "response":{"body":{...}}}
    resp = obj.get("response")
    if isinstance(resp, dict):
        body = resp.get("body")
        if isinstance(body, dict):
            return body
    return None


def extract_output_text(body: dict) -> Optional[str]:
    # Preferred: output_text
    t = body.get("output_text")
    if isinstance(t, str) and t.strip():
        return t

    # Fallback: output -> content[] -> {type:"output_text", text:"..."}
    out = body.get("output")
    if isinstance(out, list):
        chunks: List[str] = []
        for item in out:
            content = item.get("content")
            if isinstance(content, list):
                for c in content:
                    if c.get("type") == "output_text" and isinstance(c.get("text"), str):
                        chunks.append(c["text"])
        if chunks:
            return "".join(chunks)
    return None


def strip_code_fences(s: str) -> str:
    t = s.strip()
    if t.startswith("```"):
        # remove first fence line and last fence if present
        t = t.split("\n", 1)[1] if "\n" in t else t
        if t.endswith("```"):
            t = t[:-3]
    return t.strip()


def try_parse_json_object(s: str) -> Optional[dict]:
    s2 = strip_code_fences(s)
    # Try direct parse
    try:
        obj = json.loads(s2)
        return obj if isinstance(obj, dict) else None
    except Exception:
        # Try to locate first {...} region
        start = s2.find("{")
        end = s2.rfind("}")
        if start >= 0 and end > start:
            try:
                obj = json.loads(s2[start:end+1])
                return obj if isinstance(obj, dict) else None
            except Exception:
                return None
        return None


def normalize_payload(obj: dict) -> Tuple[Optional[List[dict]], Optional[List[Any]]]:
    """
    Return (annotations_list, rows_list) where:
      - annotations_list: list[dict] if obj["annotations"] exists
      - rows_list: list if obj["rows"] exists
    """
    anns = obj.get("annotations")
    if isinstance(anns, list):
        anns2 = [a for a in anns if isinstance(a, dict)]
        return (anns2, None)

    rows = obj.get("rows")
    if isinstance(rows, list):
        return (None, rows)

    return (None, None)


def is_truncated(body: dict) -> bool:
    # Your sample shows body["status"]="incomplete" and incomplete_details.reason="max_output_tokens"
    if body.get("status") == "incomplete":
        return True
    inc = body.get("incomplete_details")
    if isinstance(inc, dict) and inc.get("reason") == "max_output_tokens":
        return True
    return False


def try_parse_truncated_rows(text: str) -> Optional[List[Any]]:
    """
    Try to parse partial rows from truncated JSON output.
    The output looks like: {"rows":[[0,"human",...],[1,"human",...],
    We try to extract complete rows even if the JSON is truncated.
    """
    # Find the start of rows array
    start = text.find('"rows":')
    if start < 0:
        return None

    # Find the opening bracket
    bracket_start = text.find('[', start)
    if bracket_start < 0:
        return None

    # Extract everything after "rows":[
    content = text[bracket_start:]

    # Try to find complete row arrays by looking for ],[
    rows = []
    depth = 0
    current_row_start = None
    i = 0

    while i < len(content):
        c = content[i]
        if c == '[':
            if depth == 0:
                # Start of rows array, skip it
                depth = 1
            elif depth == 1:
                # Start of a row
                current_row_start = i
                depth = 2
            else:
                depth += 1
        elif c == ']':
            depth -= 1
            if depth == 1 and current_row_start is not None:
                # End of a row
                row_str = content[current_row_start:i+1]
                try:
                    row = json.loads(row_str)
                    if isinstance(row, list) and len(row) == 10:
                        rows.append(row)
                except json.JSONDecodeError:
                    pass
                current_row_start = None
            elif depth == 0:
                # End of rows array
                break
        i += 1

    return rows if rows else None


def write_missing(miss_path: Optional[Path], custom_id: str, idx: int, name: str, reason: str) -> None:
    if not miss_path:
        return
    with open(miss_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(
            {"custom_id": custom_id, "idx": idx, "name": name, "reason": reason},
            ensure_ascii=False, separators=(",", ":")
        ) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description="Parse batch results.jsonl -> annotations.jsonl (handles truncation + mapping)")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--output", required=True)
    ap.add_argument("--missing-output", default="")
    args = ap.parse_args()

    manifest = load_manifest(Path(args.manifest))
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    miss_path = Path(args.missing_output) if args.missing_output else None
    if miss_path:
        miss_path.parent.mkdir(parents=True, exist_ok=True)

    written = 0
    missing = 0
    truncated_chunks = 0
    bad_json_chunks = 0
    unexpected_shape = 0

    with open(args.results, "r", encoding="utf-8") as rf, open(out_path, "a", encoding="utf-8") as out_f:
        for line in tqdm(rf, desc="Parsing", unit="resp"):
            obj = json.loads(line)
            custom_id = obj.get("custom_id")
            if not custom_id or custom_id not in manifest:
                continue
            names = manifest[custom_id]

            body = extract_body(obj)
            if not body:
                for i, nm in enumerate(names):
                    missing += 1
                    write_missing(miss_path, custom_id, i, nm, "no_body")
                continue

            text = extract_output_text(body)
            if not text:
                for i, nm in enumerate(names):
                    missing += 1
                    write_missing(miss_path, custom_id, i, nm, "no_output_text")
                continue

            truncated = is_truncated(body)
            if truncated:
                truncated_chunks += 1

            parsed = try_parse_json_object(text)

            # If JSON parsing failed and response was truncated, try partial extraction
            if parsed is None and truncated:
                partial_rows = try_parse_truncated_rows(text)
                if partial_rows:
                    parsed = {"rows": partial_rows}
            if parsed is None:
                bad_json_chunks += 1
                for i, nm in enumerate(names):
                    missing += 1
                    write_missing(miss_path, custom_id, i, nm, "unparseable_json")
                continue

            anns, rows = normalize_payload(parsed)

            # Case 1: {"annotations":[{...}, ...]} (no idx): map by position
            if anns is not None:
                for i, nm in enumerate(names):
                    if i >= len(anns):
                        missing += 1
                        write_missing(miss_path, custom_id, i, nm, "missing_in_annotations")
                        continue
                    a = anns[i]
                    rec = {"custom_id": custom_id, "idx": i, "name": nm}
                    rec.update(a)
                    out_f.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
                    written += 1
                continue

            # Case 2: {"rows":[ ... ]} where rows may be list-of-lists OR list-of-dicts
            if rows is not None:
                # Build idx -> dict payload
                idx_map: Dict[int, dict] = {}

                for r in rows:
                    # list-of-lists with idx in [0] and fixed order (rare in your current output)
                    if isinstance(r, list) and len(r) == 10 and isinstance(r[0], int):
                        idx_map[int(r[0])] = {
                            "entity_type": r[1],
                            "entity_confidence": r[2],
                            "organization_type": r[3],
                            "organization_confidence": r[4],
                            "gender": r[5],
                            "prop_women": r[6],
                            "religion": r[7],
                            "prop_hindu": r[8],
                            "prop_muslim": r[9],
                        }
                    # list-of-dicts (your current output): no idx -> map by position later
                    elif isinstance(r, dict):
                        # If it includes idx, use it; else store later by position
                        if isinstance(r.get("idx"), int):
                            idx_map[int(r["idx"])] = r
                        else:
                            # stash by a special key using append order
                            idx_map.setdefault(-1, [])
                            idx_map[-1].append(r)

                # If we have a positional list (no idx), use it
                positional = idx_map.get(-1)
                if isinstance(positional, list):
                    for i, nm in enumerate(names):
                        if i >= len(positional):
                            missing += 1
                            write_missing(miss_path, custom_id, i, nm, "missing_in_rows_positional")
                            continue
                        rec = {"custom_id": custom_id, "idx": i, "name": nm}
                        rec.update(positional[i])
                        out_f.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
                        written += 1
                else:
                    # idx mapping
                    for i, nm in enumerate(names):
                        a = idx_map.get(i)
                        if a is None:
                            missing += 1
                            write_missing(miss_path, custom_id, i, nm, "missing_in_rows_idx")
                            continue
                        rec = {"custom_id": custom_id, "idx": i, "name": nm}
                        rec.update(a)
                        out_f.write(json.dumps(rec, ensure_ascii=False, separators=(",", ":")) + "\n")
                        written += 1

                continue

            unexpected_shape += 1
            for i, nm in enumerate(names):
                missing += 1
                write_missing(miss_path, custom_id, i, nm, "unexpected_json_shape")

    print(f"Wrote {written} rows to {out_path}")
    if miss_path:
        print(f"Missing {missing} rows logged to {miss_path}")
    print(f"Truncated chunks: {truncated_chunks} | Bad JSON chunks: {bad_json_chunks} | Unexpected shape: {unexpected_shape}")


if __name__ == "__main__":
    main()