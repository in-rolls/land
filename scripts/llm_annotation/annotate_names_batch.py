#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List, Dict, Any, Iterator, Tuple, Optional

import pyarrow.parquet as pq
from tqdm import tqdm


SYSTEM_PROMPT = """You are annotating account-holder name strings from Bihar land records (Hindi/Devanagari).

# TASK
The user message will include ITEMS_JSON: a JSON array of objects, each with:
- idx: integer
- name: string

Return one annotation per input item. Preserve correspondence by echoing the same idx.
Do NOT deduplicate. Do NOT skip items. If uncertain, output "cannot decide" and lower confidence.

Return ONLY valid JSON. No commentary.

# DATA QUALITY
Input names may contain noise from OCR and PDF parsing: extra spaces (e.g., "र ा म" instead of "राम"), missing or broken matras, stray punctuation, inconsistent zero-width characters, and irregular transliteration. Normalize mentally before classifying—do not let formatting artifacts change your annotation.

# OUTPUT SCHEMA
Return a single JSON object with one key "rows".
Each element of "rows" is a 10-element array in this exact order:

[idx,
 entity_type,
 entity_confidence,
 organization_type,
 organization_confidence,
 gender,
 prop_women,
 religion,
 prop_hindu,
 prop_muslim]

Where:
- entity_type: "human" | "non-human"
- entity_confidence: float in [0,1]
- organization_type: "not_applicable" | "religious" | "state" | "cooperative" | "commercial" | "commercial_farm" | "educational" | "trust_ngo" | "other" | "cannot_decide"
- organization_confidence: float in [0,1]
- gender: "man" | "woman" | "cannot decide"
- prop_women: float in [0,1] or null
- religion: "hindu" | "muslim" | "other religion" | "cannot decide"
- prop_hindu: float in [0,1]
- prop_muslim: float in [0,1]

Example output shape:
{"rows":[[0,"human",0.99,"not_applicable",1.0,"woman",0.98,"hindu",0.94,0.04], ...]}

# GENDER

**For non-human entities:** gender = "cannot decide", prop_women = null

**For humans, infer gender from the name itself.** Most names in Bihar land records are identifiably male or female based on common Bihari naming conventions. This is your primary signal. Use your knowledge of common Hindi/Bihari/Maithili/Bhojpuri/Magahi names to classify.

Honorifics and relationship markers, when present, provide strong confirmation but most entries will lack them:
- Woman: श्रीमती, श्रीमति, सुश्री, कुमारी, बीबी, बेगम, खातुन, खातून, मुसम्मत, मुस्समत, W/O, D/O, पत्नी, पुत्री
- Man: श्री (alone, without मती), Mr., S/O, पुत्र, बेटा

Set prop_women to your probability estimate that this person is a woman. Use "cannot decide" only when genuinely uncertain (prop_women ≈ 0.5).

# RELIGION

Applies to BOTH humans and non-humans (organizations can have religious affiliation).

**For humans, infer religion from the name itself.** Bihar has distinct Hindu and Muslim naming traditions, and most names are classifiable from the name alone. This is your primary signal. Use your knowledge of common names, surnames, and naming patterns across religious communities in Bihar.

Honorifics and markers, when present, provide strong confirmation but most entries will lack them:
- Hindu: पंडित, ठाकुर, मंदिर, देवस्थान, आश्रम
- Muslim: मो०, मोहम्मद, शेख, मौलाना, हाजी, हाफिज, मस्जिद, वक्फ, दरगाह, मदरसा
- Other: गुरुद्वारा (Sikh), चर्च/गिरजाघर (Christian)

**Proportions:**
- prop_hindu + prop_muslim ≤ 1.0 (remainder is implicit other/unknown)
- If clearly Hindu: prop_hindu ≈ 0.95, prop_muslim ≈ 0.03
- If clearly Muslim: prop_muslim ≈ 0.95, prop_hindu ≈ 0.03
- If name is shared across communities (e.g., राजू, राम could be either in some regions): spread probability accordingly, e.g., prop_hindu ≈ 0.70, prop_muslim ≈ 0.20
- If genuinely ambiguous: prop_hindu ≈ 0.50, prop_muslim ≈ 0.40, religion = "cannot decide"

# ENTITY TYPE

## Human indicators
- Personal names (the vast majority of entries)
- Honorifics: श्री, श्रीमती, मो०, कुमारी
- Alias markers: उर्फ
- Deceased markers: स्व०, स्व0, स्व.
- Relationship patterns: S/O, W/O, D/O, पुत्र, पत्नी, पुत्री

## Non-human indicators
Institutions, government bodies, or land categories—not persons.

**State/Government:**
बिहार सरकार, भारत सरकार, शिक्षा विभाग, वन विभाग, राजस्व, जिला परिषद, ग्राम पंचायत, प्रखंड, अंचल, थाना, पुलिस, रेलवे
Land categories: गैरमजरूआ, गैरमजरूआ आम, गैरमजरूआ खास

**Cooperative:**
सहकारी, सहकारिता, कोऑपरेटिव, PACS, पैक्स

**Commercial:**
कंपनी, प्रा. लि., Pvt, Ltd, एंटरप्राइजेज, इंडस्ट्रीज, फैक्ट्री, मिल, बैंक
⚠️ Short tokens like "लि" inside personal names are NOT commercial indicators—only count when clearly abbreviated (e.g., "प्रा. लि." with punctuation/space).

**Educational:**
विद्यालय, स्कूल, महाविद्यालय, कॉलेज, विश्वविद्यालय, पाठशाला, मदरसा

**Religious institutions:**
- Hindu: मंदिर, देवस्थान, आश्रम, धर्मशाला, ठाकुरबाड़ी
- Muslim: मस्जिद (variants: मसजिद, मस्जीद), ईदगाह, दरगाह, कब्रिस्तान, खानकाह, तकिया, मदरसा, मकतब, वक्फ/वकफ, मतवली/मुतवल्ली
- Sikh: गुरुद्वारा
- Christian: चर्च, गिरजाघर
⚠️ "मठ" can be a name component (e.g., "मठु")—only institutional when standalone.

**Trust/NGO:**
समिति, ट्रस्ट, न्यास, धर्मार्थ, सोसाइटी, संगठन, फाउंडेशन, प्रतिष्ठान

## Organization type
- If entity_type == "human": organization_type = "not_applicable", organization_confidence = 1.0
- If entity_type == "non-human": classify using categories above
"""


def load_done_names(path: Path) -> set[str]:
    if not path.exists():
        return set()
    done: set[str] = set()
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            try:
                obj = json.loads(line)
                nm = obj.get("name")
                if nm:
                    done.add(nm)
            except json.JSONDecodeError:
                continue
    return done


def iter_names(parquet_path: str, column: str, max_rows: int) -> Iterator[str]:
    pf = pq.ParquetFile(parquet_path)
    seen = 0
    for batch in pf.iter_batches(batch_size=50_000, columns=[column]):
        for raw in batch.column(0).to_pylist():
            if raw is None:
                continue
            name = str(raw).strip()
            if not name:
                continue
            seen += 1
            if max_rows > 0 and seen > max_rows:
                return
            yield name


def make_user_content(items: List[Tuple[int, str]]) -> str:
    payload = [{"idx": i, "name": s} for i, s in items]
    return (
        f"You are given exactly {len(items)} items. Each has idx and name.\n"
        "Return JSON ONLY: {\"rows\": [...]} as specified by the system prompt.\n"
        "Minify JSON (no whitespace). Echo idx values.\n\n"
        "ITEMS_JSON:\n"
        f"{json.dumps(payload, ensure_ascii=False, separators=(',',':'))}"
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Create OpenAI Batch requests.jsonl + manifest.jsonl for name annotation")
    ap.add_argument("--input", required=True, help="Input parquet")
    ap.add_argument("--column", required=True, help="Name column")
    ap.add_argument("--requests", required=True, help="Output requests.jsonl path")
    ap.add_argument("--manifest", required=True, help="Output manifest.jsonl path (maps custom_id -> names)")
    ap.add_argument("--model", default="gpt-4o-mini")
    ap.add_argument("--chunk-size", type=int, default=250)
    ap.add_argument("--max-rows", type=int, default=0)
    ap.add_argument("--skip-annotated", default="", help="Optional existing annotations JSONL to skip already-done names")
    ap.add_argument("--max-output-tokens", type=int, default=4096)
    ap.add_argument("--temperature", type=float, default=0.0)
    args = ap.parse_args()

    done = load_done_names(Path(args.skip_annotated)) if args.skip_annotated else set()

    req_path = Path(args.requests)
    man_path = Path(args.manifest)
    req_path.parent.mkdir(parents=True, exist_ok=True)
    man_path.parent.mkdir(parents=True, exist_ok=True)

    buffer: List[str] = []
    chunk_id = 0
    total_written = 0

    # Best-effort total for tqdm
    pf = pq.ParquetFile(args.input)
    total = pf.metadata.num_rows
    if args.max_rows > 0:
        total = min(total, args.max_rows)

    with open(req_path, "w", encoding="utf-8") as req_f, open(man_path, "w", encoding="utf-8") as man_f:
        for name in tqdm(iter_names(args.input, args.column, args.max_rows), total=total, desc="Preparing", unit="name"):
            if name in done:
                continue
            buffer.append(name)
            if len(buffer) >= args.chunk_size:
                custom_id = f"chunk_{chunk_id:06d}"
                items = list(enumerate(buffer))

                body: Dict[str, Any] = {
                    "model": args.model,
                    "instructions": SYSTEM_PROMPT,
                    "input": [{"role": "user", "content": make_user_content(items)}],
                    "max_output_tokens": args.max_output_tokens,
                }
                # Keep it deterministic-ish
                if args.temperature is not None:
                    body["temperature"] = args.temperature

                # Batch request line format
                req_line = {
                    "custom_id": custom_id,
                    "method": "POST",
                    "url": "/v1/responses",
                    "body": body,
                }
                req_f.write(json.dumps(req_line, ensure_ascii=False, separators=(",", ":")) + "\n")

                man_line = {"custom_id": custom_id, "names": buffer}
                man_f.write(json.dumps(man_line, ensure_ascii=False, separators=(",", ":")) + "\n")

                total_written += len(buffer)
                buffer = []
                chunk_id += 1

        if buffer:
            custom_id = f"chunk_{chunk_id:06d}"
            items = list(enumerate(buffer))
            body = {
                "model": args.model,
                "instructions": SYSTEM_PROMPT,
                "input": [{"role": "user", "content": make_user_content(items)}],
                "max_output_tokens": args.max_output_tokens,
            }
            if args.temperature is not None:
                body["temperature"] = args.temperature
            req_line = {"custom_id": custom_id, "method": "POST", "url": "/v1/responses", "body": body}
            req_f.write(json.dumps(req_line, ensure_ascii=False, separators=(",", ":")) + "\n")

            man_line = {"custom_id": custom_id, "names": buffer}
            man_f.write(json.dumps(man_line, ensure_ascii=False, separators=(",", ":")) + "\n")

            total_written += len(buffer)

    print(f"Wrote requests for {total_written:,} names in {chunk_id + (1 if buffer else 0):,} chunks.")
    print(f"Requests JSONL:  {req_path}")
    print(f"Manifest JSONL:  {man_path}")


if __name__ == "__main__":
    main()