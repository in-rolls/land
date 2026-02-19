#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from openai import OpenAI


def main() -> None:
    ap = argparse.ArgumentParser(description="Submit a Batch job for requests.jsonl (Responses API)")
    ap.add_argument("--requests", required=True, help="requests.jsonl created by make_batch_requests.py")
    ap.add_argument("--completion-window", default="24h", help="e.g., 24h")
    args = ap.parse_args()

    client = OpenAI()

    # Upload the requests file for batch processing
    file = client.files.create(file=open(args.requests, "rb"), purpose="batch")
    print("Uploaded file_id:", file.id)

    # Create the batch job. Endpoint must match the 'url' in each line (here: /v1/responses)
    batch = client.batches.create(
        input_file_id=file.id,
        endpoint="/v1/responses",
        completion_window=args.completion_window,
    )
    print("Batch job id:", batch.id)
    print("Status:", batch.status)
    print("Tip: poll with client.batches.retrieve(batch.id); when completed, download batch.output_file_id.")


if __name__ == "__main__":
    main()
