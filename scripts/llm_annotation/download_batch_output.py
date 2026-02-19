#!/usr/bin/env python3
from __future__ import annotations

import argparse
import time
from pathlib import Path
from openai import OpenAI

def download_file(client: OpenAI, file_id: str, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    data = client.files.content(file_id).read()
    out_path.write_bytes(data)

def main() -> None:
    ap = argparse.ArgumentParser(description="Poll a batch job and download its output/error files")
    ap.add_argument("--batch-id", required=True, help="batch_... id")
    ap.add_argument("--out", default="results.jsonl", help="Where to write output file (jsonl)")
    ap.add_argument("--err", default="errors.jsonl", help="Where to write error file (jsonl)")
    ap.add_argument("--poll-seconds", type=int, default=30)
    args = ap.parse_args()

    client = OpenAI()
    out_path = Path(args.out)
    err_path = Path(args.err)

    while True:
        b = client.batches.retrieve(args.batch_id)
        status = getattr(b, "status", None)
        print("Status:", status)
        if status in ("completed", "failed", "expired", "cancelled"):
            break
        time.sleep(max(5, args.poll_seconds))

    if getattr(b, "output_file_id", None):
        print("Downloading output_file_id:", b.output_file_id)
        download_file(client, b.output_file_id, out_path)
        print("Wrote:", out_path)

    if getattr(b, "error_file_id", None):
        print("Downloading error_file_id:", b.error_file_id)
        download_file(client, b.error_file_id, err_path)
        print("Wrote:", err_path)

    print("Done. Parse with parse_batch_results.py")

if __name__ == "__main__":
    main()