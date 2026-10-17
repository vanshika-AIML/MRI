"""Download a reproducible patient subset from the official MSD AWS mirror.

Uses HTTP ranges to avoid downloading the 7.6 GB archive and unlabeled test cases.
No web-page scraping, credentials, archive extraction, or executable data loaders.
"""
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib
import json
from pathlib import Path
import random
import tarfile
import time
import threading
import httpx

URL = "https://msd-for-monai-eu.s3.eu-west-2.amazonaws.com/Task01_BrainTumour.tar"
_local = threading.local()


def fetch(start, size):
    for attempt in range(5):
        try:
            if not hasattr(_local, "client"):
                _local.client = httpx.Client(timeout=120)
            with _local.client.stream("GET", URL, headers={"Range": f"bytes={start}-{start+size-1}"}) as response:
                if response.status_code != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {start}-"):
                    raise ValueError("Server did not honor byte range")
                data = response.read()
                if len(data) != size:
                    raise ValueError("Incomplete download")
                return data
        except Exception:
            if attempt == 4:
                raise
            time.sleep(2 ** attempt)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("ml/datasets/msd"))
    parser.add_argument("--cases", type=int, default=64)
    parser.add_argument("--seed", type=int, default=20261016)
    args = parser.parse_args()
    if not 10 <= args.cases <= 484:
        parser.error("cases must be between 10 and 484")
    args.output.mkdir(parents=True, exist_ok=True)
    # The official tar begins with a macOS metadata entry and dataset.json.
    header = tarfile.TarInfo.frombuf(fetch(1024, 512), "utf-8", "strict")
    if header.name != "Task01_BrainTumour/dataset.json":
        raise ValueError("Unexpected upstream archive layout")
    dataset = json.loads(fetch(1536, header.size))
    (args.output / "dataset.json").write_text(json.dumps(dataset, indent=2), encoding="utf-8")
    cases = sorted(dataset["training"], key=lambda row: row["image"])
    random.Random(args.seed).shuffle(cases)
    cases = cases[:args.cases]
    wanted = {"Task01_BrainTumour/" + row[key].removeprefix("./") for row in cases for key in ("image", "label")}
    index_path = args.output / "archive-index.json"
    index = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else []
    offset = index[-1]["next"] if index else 0
    indexed = {row["name"] for row in index}
    while not wanted.issubset(indexed):
        block = fetch(offset, 512)
        if block == bytes(512):
            raise ValueError("Requested files missing from upstream archive")
        member = tarfile.TarInfo.frombuf(block, "utf-8", "strict")
        next_offset = offset + 512 + ((member.size + 511) // 512) * 512
        index.append({"name": member.name, "offset": offset + 512, "size": member.size, "next": next_offset})
        indexed.add(member.name)
        offset = next_offset
        index_path.write_text(json.dumps(index), encoding="utf-8")
        if len(index) % 50 == 0:
            print(f"Indexed {len(index)} entries; found {len(wanted & indexed)}/{len(wanted)} requested files", flush=True)
    entries = {row["name"]: row for row in index}

    def download(name):
        row = entries[name]
        path = args.output / name
        path.parent.mkdir(parents=True, exist_ok=True)
        if not path.exists() or path.stat().st_size != row["size"]:
            data = fetch(row["offset"], row["size"])
            partial = path.with_suffix(path.suffix + ".part")
            partial.write_bytes(data)
            partial.replace(path)
        with path.open("rb") as stream:
            return name, hashlib.file_digest(stream, "sha256").hexdigest()

    hashes = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        for future in as_completed([pool.submit(download, name) for name in sorted(wanted)]):
            name, digest = future.result()
            hashes[name] = digest
            print(f"Downloaded/verified {len(hashes)}/{len(wanted)}: {name}", flush=True)
    n_val = max(2, args.cases // 8)
    rows = []
    for i, case in enumerate(cases):
        image = "Task01_BrainTumour/" + case["image"].removeprefix("./")
        label = "Task01_BrainTumour/" + case["label"].removeprefix("./")
        rows.append({"patient_id": Path(image).name.removesuffix(".nii.gz"), "image": image,
                     "label": label, "split": "test" if i < n_val else "val" if i < 2*n_val else "train",
                     "image_sha256": hashes[image], "label_sha256": hashes[label]})
    manifest = {"schema_version": 1, "source": URL, "license": "CC-BY-SA-4.0",
                "citation": "Simpson et al. A large annotated medical image dataset (2019), arXiv:1902.09063",
                "seed": args.seed, "modality_index": 0, "modality": "FLAIR", "target": "whole_tumor_label_gt_0",
                "cases": rows}
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"Manifest ready: {args.output / 'manifest.json'}", flush=True)


if __name__ == "__main__":
    main()
