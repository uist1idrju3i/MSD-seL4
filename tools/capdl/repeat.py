#!/usr/bin/env python3
# SPDX-License-Identifier: BSD-3-Clause
"""Repeat already-built QEMU tests without overwriting transcripts or CSV data."""
import argparse
import csv
import hashlib
import os
from pathlib import Path
import statistics
import subprocess

ROOT = Path(__file__).resolve().parents[2]
FIELDS = ["run_id", "mode", "qemu_status", "runner_status", "request_count", "reply_count", "fault_count", "pl011_sha256", "pl011"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--positive", type=Path, required=True)
    parser.add_argument("--negative", type=Path, required=True)
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=5)
    args = parser.parse_args()
    if args.repetitions < 5:
        parser.error("at least five repetitions required")
    jobs = [(mode, build.resolve(), f"repeat-{mode}-{i}")
            for mode, build in (("positive", args.positive), ("negative", args.negative))
            for i in range(1, args.repetitions + 1)]
    if any((build / "runs" / run_id).exists() for mode, build, run_id in jobs):
        parser.error("a run directory already exists")
    rows = []
    with args.csv.open("x", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS, lineterminator="\n")
        writer.writeheader()
        for mode, build, run_id in jobs:
            result = subprocess.run([str(ROOT / "tools/qemu-capdl.sh"), str(build), mode, run_id],
                                    env={**os.environ, "QEMU_CAPDL_SKIP_BUILD": "1"}, capture_output=True)
            dest = build / "runs" / run_id
            with (dest / "harness.log").open("xb") as log:
                log.write(result.stdout + result.stderr)
            raw = (dest / "pl011.log").read_bytes()
            row = dict(run_id=run_id, mode=mode, qemu_status=int((dest / "exit-status.txt").read_text()),
                       runner_status=result.returncode, request_count=raw.count(b"serial got badge 1 from client"),
                       reply_count=raw.count(b"client checked reply"), fault_count=raw.count(b"client faulted at 0x3f201000"),
                       pl011_sha256=hashlib.sha256(raw).hexdigest(),
                       pl011=raw.decode("ascii").replace("\r", "\\r").replace("\n", "\\n"))
            writer.writerow(row)
            stream.flush()
            rows.append(row)
            print(f"{run_id}: qemu={row['qemu_status']} runner={result.returncode}", flush=True)
            if result.returncode:
                return 1
    assert len({r["run_id"] for r in rows}) == len(rows)
    for mode in ("positive", "negative"):
        selected = [r for r in rows if r["mode"] == mode]
        for key in ("request_count", "reply_count", "fault_count"):
            values = [r[key] for r in selected]
            print(f"{mode} {key}: min={min(values)} median={statistics.median(values)} max={max(values)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
