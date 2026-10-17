import base64
import gzip
import gzip
import json
import shutil
from pathlib import Path

import nibabel as nib
import numpy as np
import pytest

from ml.inference.tumor_segmenter import (
    TumorModelConfigurationError,
    TumorSegmenter,
)

RUN_DIR = Path(__file__).resolve().parents[1] / "runs" / "msd-flair-pilot"


def _nii_bytes(channels: int = 1) -> bytes:
    values = np.zeros((24, 20, 5), dtype=np.float32)
    values[3:21, 2:18, 1:4] = np.arange(18 * 16 * 3, dtype=np.float32).reshape(18, 16, 3) + 1
    volume = values if channels == 1 else np.stack(
        [values, values * 10, values * 20, values * 30], axis=3
    )
    image = nib.Nifti1Image(volume, np.diag([1.5, 2.0, 2.5, 1.0]))
    return gzip.compress(image.to_bytes(), mtime=0)


@pytest.mark.skipif(not (RUN_DIR / "weights.pt").is_file(), reason="Local pilot checkpoint is unavailable")
def test_real_checkpoint_returns_geometry_preserving_mask_and_overlay():
    segmenter = TumorSegmenter(RUN_DIR)
    result = segmenter.predict(_nii_bytes(), "research_flair.nii.gz")

    mask_bytes = gzip.decompress(base64.b64decode(result["mask_nifti_gz_base64"]))
    mask_image = nib.Nifti1Image.from_bytes(mask_bytes)
    overlay = base64.b64decode(result["overlay_png_base64"])
    decoded_mask = np.asarray(mask_image.dataobj)

    assert decoded_mask.shape == (24, 20, 5)
    assert set(np.unique(decoded_mask)).issubset({0, 1})
    assert np.allclose(mask_image.affine, np.diag([1.5, 2.0, 2.5, 1.0]))
    assert result["mask_dimensions"] == [24, 20, 5]
    assert result["predicted_voxels"] == int(decoded_mask.sum())
    assert nib.Nifti1Image.from_bytes(mask_bytes).header.get_data_dtype() == np.dtype("uint8")
    assert overlay.startswith(b"\x89PNG\r\n\x1a\n")
    assert result["input_sha256"]
    assert result["checkpoint_sha256"]

    four_channel_result = segmenter.predict(_nii_bytes(channels=4), "msd_flair.nii.gz")
    four_channel_mask = nib.Nifti1Image.from_bytes(
        gzip.decompress(base64.b64decode(four_channel_result["mask_nifti_gz_base64"]))
    )
    assert four_channel_mask.shape == decoded_mask.shape
    assert np.array_equal(np.asarray(four_channel_mask.dataobj), decoded_mask)


@pytest.mark.skipif(not (RUN_DIR / "weights.pt").is_file(), reason="Local pilot checkpoint is unavailable")
def test_model_rejects_non_nifti_and_corrupt_nifti():
    segmenter = TumorSegmenter(RUN_DIR)
    with pytest.raises(ValueError, match="requires a NIfTI"):
        segmenter.predict(b"not a scan", "scan.png")
    with pytest.raises(ValueError, match="Invalid or corrupt"):
        segmenter.predict(b"invalid", "scan.nii")


def test_model_rejects_checkpoint_hash_mismatch(tmp_path):
    if not (RUN_DIR / "weights.pt").is_file():
        pytest.skip("Local pilot checkpoint is unavailable")
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    shutil.copyfile(RUN_DIR / "weights.pt", run_dir / "weights.pt")
    metadata = json.loads((RUN_DIR / "evaluation.json").read_text(encoding="utf-8"))
    metadata["weights_sha256"] = "0" * 64
    (run_dir / "evaluation.json").write_text(json.dumps(metadata), encoding="utf-8")

    with pytest.raises(TumorModelConfigurationError, match="checksum"):
        TumorSegmenter(run_dir)
