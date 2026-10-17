"""Research-only FLAIR whole-tumor segmentation using a verified local run."""
import base64
import gzip
import hashlib
import io
import json
import zlib
from pathlib import Path
from threading import Lock

import nibabel as nib
import numpy as np
from PIL import Image

MAX_VOXELS = 16_777_216
MAX_DECODED_BYTES = 256 * 1024 * 1024
PREPROCESSING_VERSION = "flair-zscore-ras-v1"


class TumorModelConfigurationError(RuntimeError):
    """The configured model run is incomplete, corrupt, or incompatible."""


class TumorSegmenter:
    """Loads one immutable checkpoint and serializes model inference per process."""

    def __init__(self, run_dir: Path):
        import torch
        from ml.models.tumor_unet import TumorUNet

        self._torch = torch
        self._lock = Lock()
        self._run_dir = run_dir.resolve(strict=True)
        metadata_path = self._run_dir / "evaluation.json"
        weights_path = self._run_dir / "weights.pt"
        if not metadata_path.is_file() or not weights_path.is_file():
            raise FileNotFoundError("Configured research model run is incomplete")
        try:
            self.metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise TumorModelConfigurationError("Configured model evaluation metadata is invalid") from exc
        if not isinstance(self.metadata, dict):
            raise TumorModelConfigurationError("Configured model evaluation metadata must be an object")
        if (
            self.metadata.get("model") != "compact_2d_unet"
            or self.metadata.get("task") != "whole_tumor_label_gt_0"
            or self.metadata.get("modality") != "FLAIR"
            or self.metadata.get("research_only") is not True
        ):
            raise TumorModelConfigurationError("Configured model run is incompatible with FLAIR segmentation")
        modality_index = self.metadata.get("modality_index", 0)
        size = self.metadata.get("size")
        threshold = self.metadata.get("threshold")
        if (
            type(modality_index) is not int
            or modality_index < 0
            or type(size) is not int
            or not 0 < size <= 512
            or size % 4 != 0
            or not isinstance(threshold, (int, float))
            or not 0 < threshold < 1
        ):
            raise TumorModelConfigurationError("Configured model inference parameters are invalid")
        self.weights_path = weights_path
        self.checkpoint_sha256 = self._digest(weights_path)
        if self.checkpoint_sha256 != self.metadata.get("weights_sha256"):
            raise TumorModelConfigurationError("Configured model checkpoint checksum does not match its evaluation record")
        self.model_version = self.checkpoint_sha256[:16]
        self._model = TumorUNet().eval()
        try:
            self._model.load_state_dict(
                torch.load(weights_path, map_location="cpu", weights_only=True)
            )
        except (OSError, RuntimeError, ValueError) as exc:
            raise TumorModelConfigurationError("Configured model checkpoint cannot be loaded") from exc
        torch.set_num_threads(min(torch.get_num_threads(), 4))

    @staticmethod
    def _digest(path: Path) -> str:
        with path.open("rb") as stream:
            return hashlib.file_digest(stream, "sha256").hexdigest()

    @staticmethod
    def _decode_nifti(upload: bytes, compressed: bool) -> bytes:
        if not compressed:
            decoded = upload
        else:
            try:
                decompressor = zlib.decompressobj(16 + zlib.MAX_WBITS)
                decoded = decompressor.decompress(upload, MAX_DECODED_BYTES + 1)
                if len(decoded) > MAX_DECODED_BYTES or decompressor.unconsumed_tail:
                    raise ValueError("Compressed NIfTI exceeds the decoded size limit")
                decoded += decompressor.flush(MAX_DECODED_BYTES + 1 - len(decoded))
                if len(decoded) > MAX_DECODED_BYTES or not decompressor.eof:
                    raise ValueError("Compressed NIfTI is incomplete or exceeds the decoded size limit")
            except zlib.error as exc:
                raise ValueError("Invalid gzip-compressed NIfTI") from exc
        if len(decoded) > MAX_DECODED_BYTES:
            raise ValueError("NIfTI exceeds the decoded size limit")
        return decoded

    @staticmethod
    def _overlay_png(volume: np.ndarray, mask: np.ndarray, slice_index: int) -> bytes:
        image = np.rot90(volume[:, :, slice_index])
        slice_mask = np.rot90(mask[:, :, slice_index]) > 0
        foreground = image[np.isfinite(image) & (image != 0)]
        low, high = np.percentile(foreground, [1, 99]) if foreground.size else (0.0, 1.0)
        grayscale = np.clip((image - low) / max(float(high - low), 1e-6), 0, 1)
        rgb = np.repeat((grayscale * 255).astype(np.uint8)[..., None], 3, axis=2)
        rgb[slice_mask] = (
            rgb[slice_mask].astype(np.float32) * 0.35
            + np.array([255, 32, 32], dtype=np.float32) * 0.65
        ).astype(np.uint8)
        output = io.BytesIO()
        Image.fromarray(rgb).save(output, format="PNG", optimize=True)
        return output.getvalue()

    def predict(self, upload: bytes, filename: str) -> dict:
        """Return a compressed NIfTI mask, one overlay preview and nonclinical provenance."""
        with self._lock:
            return self._predict_locked(upload, filename)

    def _predict_locked(self, upload: bytes, filename: str) -> dict:
        if not filename.lower().endswith((".nii", ".nii.gz")):
            raise ValueError("Trained segmentation requires a NIfTI .nii or .nii.gz FLAIR volume")
        raw = self._decode_nifti(upload, filename.lower().endswith(".nii.gz"))
        try:
            image_nii = nib.Nifti1Image.from_bytes(raw)
        except Exception as exc:
            raise ValueError("Invalid or corrupt NIfTI volume") from exc
        affine = image_nii.affine
        if (
            not np.isfinite(affine).all()
            or abs(float(np.linalg.det(affine[:3, :3]))) < 1e-8
            or any(not np.isfinite(zoom) or zoom <= 0 for zoom in image_nii.header.get_zooms()[:3])
        ):
            raise ValueError("NIfTI has invalid spatial geometry")
        if image_nii.ndim not in (3, 4) or (image_nii.ndim == 4 and image_nii.shape[3] <= 0):
            raise ValueError("Trained segmentation requires a 3D FLAIR scan or a 4D scan with FLAIR channel zero")
        if (
            int(np.prod(image_nii.shape[:3])) > MAX_VOXELS
            or (image_nii.ndim == 4 and image_nii.shape[3] > 8)
        ):
            raise ValueError("NIfTI exceeds the trained-model voxel limit")
        image_nii = nib.as_closest_canonical(image_nii)
        modality_index = int(self.metadata.get("modality_index", 0))
        if image_nii.ndim == 4:
            if image_nii.shape[3] <= modality_index:
                raise ValueError("NIfTI does not contain the configured FLAIR channel")
            image = np.asarray(image_nii.dataobj[..., modality_index], dtype=np.float32)
        else:
            image = np.asarray(image_nii.dataobj, dtype=np.float32)
        if image.ndim != 3 or not np.isfinite(image).all():
            raise ValueError("FLAIR volume must contain finite numeric voxels")
        foreground = image[image != 0]
        if not foreground.size:
            raise ValueError("FLAIR volume contains no nonzero voxels")
        normalized = np.where(
            image != 0,
            np.clip((image - foreground.mean()) / max(float(foreground.std()), 1e-6), -5, 5),
            0,
        )
        size = self.metadata["size"]
        threshold = float(self.metadata["threshold"])
        mask = np.zeros(image.shape, dtype=np.uint8)
        torch = self._torch
        with torch.inference_mode():
            for start in range(0, image.shape[2], 8):
                batch = torch.from_numpy(
                    np.ascontiguousarray(
                        normalized[:, :, start : start + 8].transpose(2, 0, 1)
                    )
                )[:, None]
                resized = torch.nn.functional.interpolate(
                    batch, (size, size), mode="bilinear", align_corners=False
                )
                probabilities = self._model(resized).sigmoid()
                restored = torch.nn.functional.interpolate(
                    probabilities, image.shape[:2], mode="bilinear", align_corners=False
                )
                mask[:, :, start : start + 8] = (
                    restored[:, 0].numpy().transpose(1, 2, 0) >= threshold
                ).astype(np.uint8)
        slice_index = int(np.argmax(mask.sum(axis=(0, 1))))
        mask_image = nib.Nifti1Image(mask, image_nii.affine, image_nii.header)
        mask_image.set_data_dtype(np.uint8)
        mask_bytes = gzip.compress(mask_image.to_bytes(), mtime=0)
        overlay = self._overlay_png(image, mask, slice_index)
        return {
            "target": "whole_tumor_label_gt_0",
            "modality": "FLAIR",
            "mask_format": "application/gzip+nifti",
            "mask_nifti_gz_base64": base64.b64encode(mask_bytes).decode("ascii"),
            "overlay_format": "image/png",
            "overlay_png_base64": base64.b64encode(overlay).decode("ascii"),
            "preview_slice_index": slice_index,
            "mask_dimensions": list(mask.shape),
            "affine": image_nii.affine.tolist(),
            "voxel_spacing_mm": [
                float(zoom) for zoom in image_nii.header.get_zooms()[:3]
            ],
            "predicted_voxels": int(mask.sum()),
            "threshold": threshold,
            "preprocessing_version": PREPROCESSING_VERSION,
            "checkpoint_sha256": self.checkpoint_sha256,
            "input_sha256": hashlib.sha256(upload).hexdigest(),
            "mask_sha256": hashlib.sha256(mask_bytes).hexdigest(),
        }
