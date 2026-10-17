"""Training dependencies are optional in the lean inference deployment."""
import json
import numpy as np
import pytest
import sys

torch = pytest.importorskip("torch")
import nibabel as nib
from ml.models.tumor_unet import TumorUNet
from ml.training.train_tumor import load_case, validate_manifest, score_counts


def test_unet_gradient_and_shape():
    model = TumorUNet()
    x = torch.randn(2, 1, 32, 40)
    y = model(x)
    assert y.shape == x.shape
    y.mean().backward()
    assert model.out.weight.grad is not None
    assert torch.isfinite(y).all()


def test_manifest_rejects_patient_leakage(tmp_path):
    manifest = {"target": "whole_tumor_label_gt_0", "modality": "FLAIR", "cases": []}
    for i, split in enumerate(("train", "val", "test")):
        image = np.random.default_rng(i).normal(size=(8, 8, 4)).astype(np.float32)
        for key, value in (("image", image), ("label", (image > 1).astype(np.uint8))):
            nib.save(nib.Nifti1Image(value, np.eye(4)), tmp_path / f"{key}{i}.nii.gz")
        manifest["cases"].append({"patient_id": str(i), "split": split, "image": f"image{i}.nii.gz", "label": f"label{i}.nii.gz"})
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    assert len(validate_manifest(path)["cases"]) == 3
    x, y = load_case(tmp_path, manifest["cases"][0], 0, 16, 1)
    assert x.shape == y.shape == (4, 1, 16, 16)
    assert set(y.unique().tolist()) <= {0., 1.}
    manifest["modality_index"] = True
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="modality_index"):
        validate_manifest(path)
    manifest.pop("modality_index")
    manifest["cases"][0].pop("image")
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="image path"):
        validate_manifest(path)
    manifest["cases"][0]["image"] = "image0.nii.gz"
    manifest["cases"][1]["patient_id"] = "0"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError, match="Duplicate patient"):
        validate_manifest(path)


def test_metrics_use_false_negatives_and_false_positives():
    metrics = score_counts(8, 2, 4, 16)
    assert metrics["dice"] == pytest.approx(16/22)
    assert metrics["sensitivity"] == pytest.approx(8/12)
    assert metrics["specificity"] == pytest.approx(16/18)


def test_custom_candidate_training_writes_reproducible_verified_run(tmp_path, monkeypatch):
    from ml.training import train_tumor

    cases = []
    for index, split in enumerate(("train", "val", "test")):
        image = np.random.default_rng(index).normal(size=(8, 8, 4)).astype(np.float32)
        label = np.zeros((8, 8, 4), dtype=np.uint8)
        label[2:5, 2:5, 1:3] = 1
        image_path = tmp_path / f"image-{index}.nii.gz"
        label_path = tmp_path / f"label-{index}.nii.gz"
        nib.save(nib.Nifti1Image(image, np.eye(4)), image_path)
        nib.save(nib.Nifti1Image(label, np.eye(4)), label_path)
        cases.append(
            {
                "patient_id": f"case-{index}",
                "split": split,
                "image": image_path.name,
                "label": label_path.name,
            }
        )
    manifest_path = tmp_path / "custom-manifest.json"
    manifest_path.write_text(
        json.dumps(
            {
                "target": "whole_tumor_label_gt_0",
                "modality": "FLAIR",
                "modality_index": 0,
                "cases": cases,
            }
        ),
        encoding="utf-8",
    )
    output = tmp_path / "candidate-run"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "train_tumor",
            "--manifest",
            str(manifest_path),
            "--output",
            str(output),
            "--epochs",
            "1",
            "--size",
            "16",
            "--stride",
            "1",
            "--batch-size",
            "4",
            "--device",
            "cpu",
        ],
    )

    train_tumor.main()

    evaluation = json.loads((output / "evaluation.json").read_text(encoding="utf-8"))
    assert evaluation["research_only"] is True
    assert evaluation["patient_counts"] == {"train": 1, "val": 1, "test": 1}
    assert evaluation["modality_index"] == 0
    assert evaluation["weights_sha256"] == train_tumor.digest(output / "weights.pt")
