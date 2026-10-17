"""Opt-in research inference for a trained FLAIR whole-tumor U-Net checkpoint."""
import argparse
import json
from pathlib import Path

import nibabel as nib
import numpy as np
import torch
from torch.nn import functional as F

from ml.models.tumor_unet import TumorUNet
from ml.training.train_tumor import digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--image", type=Path, required=True, help="3D FLAIR or MSD 4D image with FLAIR channel zero")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("Output already exists; choose a new file")
    metadata = json.loads((args.run / "evaluation.json").read_text(encoding="utf-8"))
    weights = args.run / "weights.pt"
    if digest(weights) != metadata["weights_sha256"]:
        raise ValueError("Checkpoint checksum mismatch")
    nii = nib.as_closest_canonical(nib.load(args.image))
    if np.prod(nii.shape) > 100_000_000:
        raise ValueError("Image exceeds voxel limit")
    volume = np.asarray(nii.dataobj, dtype=np.float32)
    if volume.ndim == 4:
        volume = volume[..., 0]
    if volume.ndim != 3 or not np.isfinite(volume).all():
        raise ValueError("Expected a finite 3D FLAIR volume")
    foreground = volume[volume != 0]
    if not foreground.size:
        raise ValueError("Empty image")
    normalized = np.where(volume != 0, np.clip((volume-foreground.mean()) / max(float(foreground.std()), 1e-6), -5, 5), 0)
    torch.set_num_threads(4)
    model = TumorUNet().eval()
    model.load_state_dict(torch.load(weights, map_location="cpu", weights_only=True))
    mask = np.zeros(volume.shape, dtype=np.uint8)
    with torch.no_grad():
        for start in range(0, volume.shape[2], 8):
            batch = torch.from_numpy(np.ascontiguousarray(normalized[:, :, start:start+8].transpose(2,0,1)))[:,None]
            resized = F.interpolate(batch, (metadata["size"], metadata["size"]), mode="bilinear", align_corners=False)
            probability = F.interpolate(model(resized).sigmoid(), volume.shape[:2], mode="bilinear", align_corners=False)
            mask[:, :, start:start+8] = (probability[:,0].numpy().transpose(1,2,0) >= metadata["threshold"]).astype(np.uint8)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    nib.save(nib.Nifti1Image(mask, nii.affine), args.output)
    result = {"research_only": True, "input_sha256": digest(args.image), "weights_sha256": metadata["weights_sha256"],
              "mask_sha256": digest(args.output), "mask": str(args.output), "orientation": "RAS canonical, NIfTI affine retained",
              "predicted_voxels": int(mask.sum()), "target": "whole_tumor_label_gt_0", "modality_required": "FLAIR",
              "warning": "Experimental segmentation; does not establish tumor presence, subtype, grade, or clinical diagnosis."}
    args.output.with_name(args.output.name + ".json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
