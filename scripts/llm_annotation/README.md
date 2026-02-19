# LLM Name Annotation Pipeline

Annotates Hindi/Devanagari names from Bihar land records using OpenAI's Batch API. Classifies names by entity type (human vs institutional), gender, and religion.

## Pipeline Overview

```
┌─────────────────┐     ┌──────────────┐     ┌───────────────────┐
│ Input Parquet   │────▶│ Batch Prep   │────▶│ requests.jsonl    │
│ (unique names)  │     │              │     │ manifest.jsonl    │
└─────────────────┘     └──────────────┘     └───────────────────┘
                                                      │
                                                      ▼
┌─────────────────┐     ┌──────────────┐     ┌───────────────────┐
│ annotations.jsonl│◀────│ Parse Results│◀────│ OpenAI Batch API  │
│ (final output)  │     │              │     │ (async, ~24h)     │
└─────────────────┘     └──────────────┘     └───────────────────┘
```

## Scripts

| Script | Purpose |
|--------|---------|
| `annotate_names_batch.py` | Creates batch requests from parquet input |
| `submit_batch.py` | Submits requests to OpenAI Batch API |
| `download_batch_output.py` | Polls and downloads completed results |
| `parse_results.py` | Parses results back to annotations |
| `create_annotated_parquet.py` | Merges annotations back into original parquet |
| `streaming/annotate_names.py` | Streaming alternative (direct API, no batch) |
| `streaming/prompt.py` | System prompt specification |
| `streaming/schema.py` | Pydantic validation models |

## Usage

### Batch Pipeline (recommended for large datasets)

```bash
# 1. Prepare batch requests (chunks names into groups of 250)
python annotate_names_batch.py \
    --input ../../data/unique_names.parquet \
    --column name \
    --requests requests.jsonl \
    --manifest manifest.jsonl

# 2. Submit to OpenAI Batch API
python submit_batch.py --requests requests.jsonl
# Note the batch_id from output

# 3. Poll and download results (waits for completion)
python download_batch_output.py \
    --batch-id batch_abc123 \
    --out results.jsonl

# 4. Parse results back to annotations
python parse_results.py \
    --manifest manifest.jsonl \
    --results results.jsonl \
    --output annotations.jsonl \
    --missing missing.jsonl
```

### Streaming Alternative (for smaller datasets)

```bash
python streaming/annotate_names.py \
    --input ../../data/unique_names.parquet \
    --column name \
    --output annotations.jsonl \
    --model gpt-4o-mini \
    --chunk-size 25 \
    --rpm 60
```

## Output Schema

Each annotation in `annotations.jsonl`:

```json
{
  "name": "श्रीमती फूलमती देवी",
  "entity_type": "human",
  "entity_confidence": 0.99,
  "organization_type": "not_applicable",
  "organization_confidence": 1.0,
  "gender": "woman",
  "prop_women": 0.98,
  "religion": "hindu",
  "prop_hindu": 0.94,
  "prop_muslim": 0.04
}
```

### Fields

| Field | Type | Values |
|-------|------|--------|
| `entity_type` | string | `human`, `non-human` |
| `entity_confidence` | float | 0.0 - 1.0 |
| `organization_type` | string | `not_applicable`, `religious`, `state`, `cooperative`, `commercial`, `commercial_farm`, `educational`, `trust_ngo`, `other`, `cannot_decide` |
| `gender` | string | `man`, `woman`, `cannot decide` |
| `prop_women` | float/null | 0.0 - 1.0 (null for non-humans) |
| `religion` | string | `hindu`, `muslim`, `other religion`, `cannot decide` |
| `prop_hindu` | float | 0.0 - 1.0 |
| `prop_muslim` | float | 0.0 - 1.0 |

## Prompt

The full system prompt is in `streaming/prompt.py`. Key classification rules:

**Human indicators:**
- Honorifics: श्री, श्रीमती, मो०, कुमारी
- Relationship markers: S/O, W/O, D/O, पुत्र, पत्नी, पुत्री

**Non-human indicators:**
- State: बिहार सरकार, ग्राम पंचायत, गैरमजरूआ
- Religious: मंदिर, मस्जिद, गुरुद्वारा
- Educational: विद्यालय, महाविद्यालय, मदरसा
- Commercial: कंपनी, प्रा. लि., बैंक
- Cooperative: सहकारी, PACS

**Gender indicators:**
- Woman: श्रीमती, W/O, D/O, पत्नी, पुत्री, बेगम, खातुन
- Man: श्री (alone), S/O, पुत्र

**Religion indicators:**
- Hindu: पंडित, ठाकुर, मंदिर + common Hindu names
- Muslim: मो०, मौलाना, हाजी, मस्जिद + common Muslim names

## Requirements

```
openai
pandas
pyarrow
pydantic
tqdm
```

## Environment

Set `OPENAI_API_KEY` environment variable before running.

## Archive

The `archive/` directory contains intermediate files from the batch annotation runs:

```
archive/
├── 00_initial/    # Initial run (Feb 2-9): 1.61M annotations
├── 01_retry/      # Retry 1 (Feb 15): 782K annotations
├── 02_retry/      # Retry 2 (Feb 15): 804K annotations
├── 03_retry/      # Retry 3 (Feb 15): 1.5K annotations
└── test/          # Test files
```

See `archive/README.md` for details on each round and file purposes.
