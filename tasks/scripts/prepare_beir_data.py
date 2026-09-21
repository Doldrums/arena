#!/usr/bin/env python3
"""Fetch the three exact, small RankEvolve BEIR archives; never replace datasets."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tempfile
import urllib.request
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from autoresearch_tasks.registry import get_task
from autoresearch_tasks.runner import checkout_path, verify_source_checkout


def verify_files(checkout, row):
    for relative, digest in row["files"].items():
        path = (checkout / relative).resolve()
        if not path.is_relative_to(checkout.resolve()) or not path.is_file():
            raise ValueError(f"Missing pinned dataset file: {relative}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"Dataset file hash mismatch: {relative}")
    return {"dataset": row["dataset"], "verified_files": len(row["files"])}


def install_archive(archive, checkout, row):
    raw = Path(archive).read_bytes()
    if len(raw) != row["zip_bytes"] or hashlib.sha256(raw).hexdigest() != row["sha256"]:
        raise ValueError("BEIR archive differs from the registered SHA-256 or size")
    # The published MD5 is historical upstream evidence; SHA-256 is enforced too.
    if hashlib.md5(raw).hexdigest() != row["official_md5"]:
        raise ValueError("BEIR archive differs from its officially published MD5")
    target = checkout / "datasets/beir"
    target.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=target, prefix=".beir-") as temporary:
        extracted = Path(temporary)
        with zipfile.ZipFile(archive) as zipped:
            total = 0
            for member in zipped.infolist():
                path = (extracted / member.filename).resolve()
                if not path.is_relative_to(extracted.resolve()):
                    raise ValueError("Unsafe BEIR archive path")
                total += member.file_size
            if total != sum(row["file_sizes"].values()):
                raise ValueError("BEIR extracted byte count differs from its lock")
            zipped.extractall(extracted)
        for relative, digest in row["files"].items():
            name = Path(relative).relative_to("datasets/beir")
            source = extracted / name
            if not source.is_file() or hashlib.sha256(source.read_bytes()).hexdigest() != digest:
                raise ValueError(f"BEIR extracted file hash mismatch: {relative}")
        destination = target / row["dataset"]
        if destination.exists():
            # Do not overwrite a user's altered dataset when verification fails.
            return verify_files(checkout, row)
        shutil.move(str(extracted / row["dataset"]), destination)
    return verify_files(checkout, row)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", choices=("nfcorpus", "scifact", "arguana"))
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args(argv)
    lock = json.loads((ROOT / "catalog/rankevolve-data-lock.json").read_text())
    results = []
    for row in lock["datasets"]:
        if args.dataset and row["dataset"] != args.dataset:
            continue
        task = get_task(ROOT, row["task_id"])
        checkout = checkout_path(ROOT, task["execution"])
        verify_source_checkout(checkout, task["execution"])
        if args.verify_only or (checkout / "datasets/beir" / row["dataset"]).exists():
            results.append(verify_files(checkout, row))
            continue
        with tempfile.TemporaryDirectory(prefix="beir-download-") as temporary:
            archive = Path(temporary) / "dataset.zip"
            with urllib.request.urlopen(row["url"], timeout=60) as response, archive.open("wb") as output:
                total = 0
                while block := response.read(1024 * 1024):
                    total += len(block)
                    if total > row["download_cap_bytes"]:
                        raise ValueError("BEIR response exceeded the locked download size")
                    output.write(block)
            results.append(install_archive(archive, checkout, row))
    print(json.dumps({"datasets": results}, indent=2))


if __name__ == "__main__":
    main()
