#!/usr/bin/env python3
"""
Create clean final parquet file from annotated names JSONL.
"""

import json
import pandas as pd
from pathlib import Path


def normalize_value(value: str, valid_values: set, default: str = "cannot_decide") -> str:
    """Normalize a string value, handling 'cannot decide' variants."""
    if not isinstance(value, str):
        return default

    normalized = value.strip().lower()

    if normalized in ("cannot decide", "cannot_decide"):
        return "cannot_decide"

    if normalized in valid_values:
        return normalized

    return default


def normalize_org_type(value: str) -> str:
    """Normalize organization type, consolidating variations."""
    if not isinstance(value, str):
        return "cannot_decide"

    normalized = value.strip().lower()

    mapping = {
        "cannot decide": "cannot_decide",
        "cannot_decide": "cannot_decide",
        "non-human": "land",
        "land category": "land",
        "land_category": "land",
        "muslim": "religious",
        "hindu": "religious",
        "political": "other",
        "welfare": "other",
    }

    return mapping.get(normalized, normalized)


def load_and_clean_data(jsonl_path: Path) -> pd.DataFrame:
    """Load JSONL and clean/normalize values."""

    valid_entity_types = {"human", "non-human", "non_human"}
    valid_genders = {"man", "woman"}
    valid_religions = {"hindu", "muslim", "other_religion"}

    records = []
    errors = 0

    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)

                entity_type = normalize_value(
                    record.get("entity_type", ""),
                    valid_entity_types,
                    "cannot_decide"
                )
                if entity_type == "non-human":
                    entity_type = "non_human"

                gender = normalize_value(
                    record.get("gender", ""),
                    valid_genders,
                    "cannot_decide"
                )

                religion = normalize_value(
                    record.get("religion", ""),
                    valid_religions,
                    "cannot_decide"
                )

                def safe_float(val, default=0.0):
                    if val is None:
                        return default
                    try:
                        return float(val)
                    except (ValueError, TypeError):
                        return default

                cleaned = {
                    "name": record.get("name", ""),
                    "entity_type": entity_type,
                    "entity_confidence": safe_float(record.get("entity_confidence"), 0.0),
                    "organization_type": normalize_org_type(record.get("organization_type", "not_applicable")),
                    "gender": gender,
                    "prop_women": safe_float(record.get("prop_women"), 0.0),
                    "religion": religion,
                    "prop_hindu": safe_float(record.get("prop_hindu"), 0.0),
                    "prop_muslim": safe_float(record.get("prop_muslim"), 0.0),
                }
                records.append(cleaned)

            except (json.JSONDecodeError, ValueError, TypeError) as e:
                errors += 1
                if errors <= 10:
                    print(f"Error on line {line_num}: {e}")

    if errors > 10:
        print(f"... and {errors - 10} more errors")

    print(f"Loaded {len(records):,} records with {errors} parsing errors")

    return pd.DataFrame(records)


def print_summary_statistics(df: pd.DataFrame) -> None:
    """Print summary statistics for the dataset."""

    print("\n" + "=" * 60)
    print("SUMMARY STATISTICS")
    print("=" * 60)

    print(f"\nTotal records: {len(df):,}")

    print("\n--- Entity Type Distribution ---")
    entity_counts = df["entity_type"].value_counts()
    for entity_type, count in entity_counts.items():
        pct = 100 * count / len(df)
        print(f"  {entity_type}: {count:,} ({pct:.2f}%)")

    humans = df[df["entity_type"] == "human"]
    print(f"\n--- Gender Distribution (humans only, n={len(humans):,}) ---")
    gender_counts = humans["gender"].value_counts()
    for gender, count in gender_counts.items():
        pct = 100 * count / len(humans)
        print(f"  {gender}: {count:,} ({pct:.2f}%)")

    print(f"\n--- Religion Distribution (humans only, n={len(humans):,}) ---")
    religion_counts = humans["religion"].value_counts()
    for religion, count in religion_counts.items():
        pct = 100 * count / len(humans)
        print(f"  {religion}: {count:,} ({pct:.2f}%)")

    non_humans = df[df["entity_type"] == "non_human"]
    if len(non_humans) > 0:
        print(f"\n--- Organization Type Distribution (non-humans only, n={len(non_humans):,}) ---")
        org_counts = non_humans["organization_type"].value_counts()
        for org_type, count in org_counts.items():
            pct = 100 * count / len(non_humans)
            print(f"  {org_type}: {count:,} ({pct:.2f}%)")

    print(f"\n--- Gender × Religion Cross-tabulation (humans only) ---")
    crosstab = pd.crosstab(humans["gender"], humans["religion"], margins=True)
    print(crosstab.to_string())

    print("\n--- Confidence Statistics ---")
    print(f"  entity_confidence: mean={df['entity_confidence'].mean():.3f}, "
          f"min={df['entity_confidence'].min():.3f}, max={df['entity_confidence'].max():.3f}")
    print(f"  prop_women (humans): mean={humans['prop_women'].mean():.3f}, "
          f"min={humans['prop_women'].min():.3f}, max={humans['prop_women'].max():.3f}")
    print(f"  prop_hindu (humans): mean={humans['prop_hindu'].mean():.3f}, "
          f"min={humans['prop_hindu'].min():.3f}, max={humans['prop_hindu'].max():.3f}")
    print(f"  prop_muslim (humans): mean={humans['prop_muslim'].mean():.3f}, "
          f"min={humans['prop_muslim'].min():.3f}, max={humans['prop_muslim'].max():.3f}")

    print("\n--- Data Quality Checks ---")
    null_counts = df.isnull().sum()
    if null_counts.sum() > 0:
        print("  Null values found:")
        for col, count in null_counts[null_counts > 0].items():
            print(f"    {col}: {count}")
    else:
        print("  No null values found")

    empty_names = (df["name"] == "").sum()
    print(f"  Empty names: {empty_names}")


def main():
    base_path = Path(__file__).parent.parent.parent
    input_path = base_path / "data" / "names_annotated.jsonl"
    output_path = base_path / "data" / "names_annotated.parquet"

    print(f"Loading data from: {input_path}")
    df = load_and_clean_data(input_path)

    print(f"\nSaving parquet to: {output_path}")
    df.to_parquet(output_path, index=False)

    saved_df = pd.read_parquet(output_path)
    print(f"Verified parquet file: {len(saved_df):,} records")

    print_summary_statistics(df)

    print("\n" + "=" * 60)
    print("Column types:")
    print("=" * 60)
    print(df.dtypes.to_string())

    print("\n" + "=" * 60)
    print("Sample records:")
    print("=" * 60)
    print(df.head(5).to_string())


if __name__ == "__main__":
    main()
