"""Reproducible patient-separated FLAIR segmentation training and held-out evaluation.

Accepts the downloaded MSD manifest or a local custom manifest with the same schema.
Never uses validation/test patients for gradient updates. Test is evaluated once,
after selecting the checkpoint by validation Dice. Outputs are research artifacts.
"""
import argparse
import hashlib
import json
from pathlib import Path
import random
import time

import nibabel as nib
import numpy as np
import torch
from torch.nn import functional as F
from torch.utils.data import DataLoader, TensorDataset

from ml.models.tumor_unet import TumorUNet


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def validate_manifest(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError("Manifest must contain a JSON object")
    if data.get("target") != "whole_tumor_label_gt_0" or data.get("modality") != "FLAIR":
        raise ValueError("This model requires FLAIR and whole_tumor_label_gt_0 labels")
    cases = data.get("cases")
    if not isinstance(cases, list) or not cases:
        raise ValueError("Manifest must contain a non-empty cases list")
    modality_index = data.get("modality_index", 0)
    if type(modality_index) is not int or modality_index < 0:
        raise ValueError("modality_index must be a non-negative integer")
    ids, files, hashes, splits = set(), set(), set(), set()
    for case in cases:
        if not isinstance(case, dict):
            raise ValueError("Every manifest case must be an object")
        patient_id = case.get("patient_id")
        if not isinstance(patient_id, str) or not patient_id.strip():
            raise ValueError("Every case requires a non-empty pseudonymous patient_id")
        normalized_id = patient_id.strip().casefold()
        if normalized_id in ids:
            raise ValueError("Duplicate patient: split leakage")
        ids.add(normalized_id)
        if case.get("split") not in ("train", "val", "test"):
            raise ValueError("Each patient needs an explicit train/val/test split")
        splits.add(case["split"])
        for key in ("image", "label"):
            relative_path = case.get(key)
            if not isinstance(relative_path, str) or not relative_path.strip():
                raise ValueError(f"Every case requires a non-empty {key} path")
            local = (path.parent / relative_path).resolve(strict=True)
            if not local.is_file():
                raise ValueError(f"Manifest {key} path is not a file")
            if local in files:
                raise ValueError("Repeated source file: split leakage")
            files.add(local)
            actual = digest(local)
            if case.get(key + "_sha256") and case[key + "_sha256"] != actual:
                raise ValueError("Dataset checksum mismatch")
            if key == "image":
                if actual in hashes:
                    raise ValueError("Duplicate image content: split leakage")
                hashes.add(actual)
            case[key + "_sha256"] = actual
    if splits != {"train", "val", "test"}:
        raise ValueError("All three patient splits are required")
    return data


def load_case(root, case, modality_index, size, stride):
    image_nii = nib.load(root / case["image"])
    label_nii = nib.load(root / case["label"])
    if image_nii.shape[:3] != label_nii.shape or not np.allclose(image_nii.affine, label_nii.affine):
        raise ValueError("Image/mask geometry mismatch")
    if np.prod(image_nii.shape) > 100_000_000:
        raise ValueError("Input exceeds training voxel limit")
    image_nii = nib.as_closest_canonical(image_nii)
    label_nii = nib.as_closest_canonical(label_nii)
    image = np.asarray(image_nii.dataobj, dtype=np.float32)
    if image.ndim == 4:
        if not 0 <= modality_index < image.shape[3]:
            raise ValueError("Configured FLAIR modality_index is outside the image channels")
        image = image[..., modality_index]
    elif image.ndim != 3 or modality_index != 0:
        raise ValueError("Expected a 3D FLAIR volume or a 4D volume with a valid modality_index")
    if image.ndim != 3 or not np.isfinite(image).all():
        raise ValueError("Expected finite 3D FLAIR volume")
    label = np.asarray(label_nii.dataobj)
    if not np.isfinite(label).all() or not np.isin(label, [0, 1, 2, 3]).all():
        raise ValueError("Mask labels must be integers 0..3 (positive labels are merged)")
    foreground = image[image != 0]
    if not foreground.size:
        raise ValueError("Empty image")
    # Shared with inference; normalize the entire nonzero volume, not individual slices.
    image = np.where(image != 0, np.clip((image-foreground.mean()) / max(float(foreground.std()), 1e-6), -5, 5), 0)
    x = torch.from_numpy(np.ascontiguousarray(image[:, :, ::stride].transpose(2, 0, 1)))[:, None]
    y = torch.from_numpy(np.ascontiguousarray((label[:, :, ::stride] > 0).transpose(2, 0, 1)).astype(np.float32))[:, None]
    return F.interpolate(x, (size, size), mode="bilinear", align_corners=False), F.interpolate(y, (size, size), mode="nearest")


def score_counts(tp, fp, fn, tn):
    return {"dice": 2*tp/max(2*tp+fp+fn, 1), "iou": tp/max(tp+fp+fn, 1),
            "sensitivity": tp/max(tp+fn, 1), "specificity": tn/max(tn+fp, 1)}


@torch.no_grad()
def evaluate(model, patients, device, batch_size):
    model.eval()
    results = []
    for patient_id, x, y in patients:
        counts = np.zeros(4, dtype=np.int64)
        for start in range(0, len(x), batch_size):
            pred = (model(x[start:start+batch_size].to(device)).sigmoid() >= .5).cpu()
            truth = y[start:start+batch_size] > .5
            counts += [int((pred & truth).sum()), int((pred & ~truth).sum()), int((~pred & truth).sum()), int((~pred & ~truth).sum())]
        results.append({"patient_id": patient_id, **score_counts(*counts.tolist()), "counts_tp_fp_fn_tn": counts.tolist()})
    return {"mean_patient_dice": float(np.mean([p["dice"] for p in results])), "patients": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--size", type=int, default=128)
    parser.add_argument("--stride", type=int, default=3)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--seed", type=int, default=20261016)
    parser.add_argument("--device", choices=["auto", "cpu", "cuda"], default="auto")
    args = parser.parse_args()
    if min(args.epochs, args.size, args.stride, args.batch_size) < 1 or args.size % 4:
        parser.error("Positive settings required; size must be a multiple of four")
    if args.device == "cuda" and not torch.cuda.is_available():
        parser.error("CUDA was requested but is unavailable")
    if args.output.exists() and any(args.output.iterdir()):
        parser.error("Choose a new output directory to preserve prior experiments")
    args.output.mkdir(parents=True, exist_ok=True)
    random.seed(args.seed)
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(4)
    torch.backends.cudnn.benchmark = False
    torch.backends.cudnn.deterministic = True
    device = "cuda" if args.device == "auto" and torch.cuda.is_available() else ("cpu" if args.device == "auto" else args.device)
    manifest = validate_manifest(args.manifest)
    (args.output / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    patients = {split: [] for split in ("train", "val", "test")}
    started = time.perf_counter()
    for i, case in enumerate(manifest["cases"]):
        x, y = load_case(args.manifest.parent, case, manifest.get("modality_index", 0), args.size, args.stride)
        patients[case["split"]].append((case["patient_id"], x, y))
        print(f"Loaded {i+1}/{len(manifest['cases'])} patients", flush=True)
    training = TensorDataset(torch.cat([p[1] for p in patients["train"]]), torch.cat([p[2] for p in patients["train"]]))
    loader = DataLoader(training, batch_size=args.batch_size, shuffle=True, generator=torch.Generator().manual_seed(args.seed), num_workers=0)
    model = TumorUNet().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=1e-3, weight_decay=1e-4)
    best, history = -1., []
    for epoch in range(args.epochs):
        model.train()
        losses = []
        for x, y in loader:
            x, y = x.to(device), y.to(device)
            optimizer.zero_grad(set_to_none=True)
            logits = model(x)
            probability = logits.sigmoid()
            dice = (2*(probability*y).sum((1,2,3))+1) / (probability.sum((1,2,3))+y.sum((1,2,3))+1)
            loss = F.binary_cross_entropy_with_logits(logits, y) + 1-dice.mean()
            loss.backward()
            optimizer.step()
            losses.append(loss.item())
        validation = evaluate(model, patients["val"], device, args.batch_size)
        row = {"epoch": epoch+1, "loss": float(np.mean(losses)), "validation_dice": validation["mean_patient_dice"]}
        history.append(row)
        if row["validation_dice"] > best:
            best = row["validation_dice"]
            torch.save(model.state_dict(), args.output / "weights.pt")
        print(json.dumps(row), flush=True)
        (args.output / "history.json").write_text(json.dumps(history, indent=2), encoding="utf-8")
    model.load_state_dict(torch.load(args.output / "weights.pt", map_location=device, weights_only=True))
    test = evaluate(model, patients["test"], device, args.batch_size)
    values = np.array([p["dice"] for p in test["patients"]])
    bootstrap = np.random.default_rng(args.seed).choice(values, size=(2000, len(values)), replace=True).mean(1)
    report = {"model": "compact_2d_unet", "research_only": True, "task": manifest["target"],
              "modality": "FLAIR", "modality_index": manifest.get("modality_index", 0),
              "size": args.size, "slice_stride": args.stride, "threshold": .5,
              "seed": args.seed, "torch": torch.__version__, "device": device,
              "gpu": torch.cuda.get_device_name(0) if device == "cuda" else None,
              "patient_counts": {k: len(v) for k,v in patients.items()},
              "epochs": args.epochs, "best_validation_dice": best, "test": test,
              "test_dice_bootstrap_95ci": np.quantile(bootstrap, [.025,.975]).tolist(),
              "elapsed_seconds": time.perf_counter()-started, "weights_sha256": digest(args.output / "weights.pt"),
              "limitations": ["Small public-dataset subset; not clinical validation", "Binary whole-tumor mask, no subtype or grade",
                              "Metrics measured at resized resolution on sampled axial slices", "No external-site cohort or healthy control specificity",
                              "Not approved for diagnosis; no automatic promotion to production"]}
    (args.output / "evaluation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()
