"""Synthetic MRI Data Generator Script.

Generates realistic synthetic DICOM images (.dcm) and 3D NIfTI volumes (.nii.gz)
with synthetic brain anatomical geometry (skull, gray matter, white matter, ventricles,
and optional abnormality/lesion regions) for testing data ingestion pipelines without PHI.

Usage:
    python -m ml.scripts.generate_synthetic_data --output-dir datasets/synthetic
"""

import argparse
import logging
from pathlib import Path
from typing import Optional, Tuple

import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset, FileMetaDataset
from pydicom.uid import ExplicitVRLittleEndian, generate_uid

logger = logging.getLogger(__name__)


def generate_synthetic_brain_volume(
    shape: Tuple[int, int, int] = (64, 64, 32),
    add_lesion: bool = True,
    noise_std: float = 5.0,
) -> Tuple[np.ndarray, Optional[np.ndarray]]:
    """Generate a 3D synthetic brain volume array with anatomical structures.

    Args:
        shape: 3D dimensions (x, y, z).
        add_lesion: If True, adds a hyperintense lesion region.
        noise_std: Gaussian noise standard deviation.

    Returns:
        Tuple of (volume array float32, lesion mask boolean or None).
    """
    nx, ny, nz = shape
    volume = np.zeros(shape, dtype=np.float32)
    lesion_mask = np.zeros(shape, dtype=bool)

    # Normalized meshgrid (-1 to 1)
    x = np.linspace(-1, 1, nx)
    y = np.linspace(-1, 1, ny)
    z = np.linspace(-1, 1, nz)
    xx, yy, zz = np.meshgrid(x, y, z, indexing="ij")

    # 1. Skull / Head boundary (Ellipsoid)
    r_head = (xx / 0.85) ** 2 + (yy / 0.85) ** 2 + (zz / 0.85) ** 2
    head_mask = r_head <= 1.0
    volume[head_mask] = 120.0  # Skull intensity

    # 2. Brain Parenchyma (Inner Ellipsoid)
    r_brain = (xx / 0.75) ** 2 + (yy / 0.75) ** 2 + (zz / 0.75) ** 2
    brain_mask = r_brain <= 1.0
    volume[brain_mask] = 400.0  # Gray matter baseline

    # 3. White Matter (Core Ellipsoid)
    r_wm = (xx / 0.55) ** 2 + (yy / 0.55) ** 2 + (zz / 0.55) ** 2
    wm_mask = r_wm <= 1.0
    volume[wm_mask] = 600.0  # White matter intensity (T1-weighted hyperintense)

    # 4. Ventricles (CSF - Fluid filled, Hypointense on T1)
    r_vent1 = ((xx - 0.15) / 0.12) ** 2 + (yy / 0.35) ** 2 + (zz / 0.3) ** 2
    r_vent2 = ((xx + 0.15) / 0.12) ** 2 + (yy / 0.35) ** 2 + (zz / 0.3) ** 2
    vent_mask = (r_vent1 <= 1.0) | (r_vent2 <= 1.0)
    volume[vent_mask] = 50.0  # CSF low intensity on T1

    # 5. Optional Lesion (Hyperintense lesion in right frontal lobe)
    if add_lesion:
        r_lesion = ((xx - 0.35) / 0.12) ** 2 + ((yy - 0.2) / 0.12) ** 2 + ((zz - 0.1) / 0.15) ** 2
        lesion_mask = r_lesion <= 1.0
        volume[lesion_mask] = 950.0  # Bright hyperintense lesion signal

    # Add Gaussian Rician-like noise
    noise = np.random.normal(0, noise_std, size=shape).astype(np.float32)
    volume = np.maximum(0, volume + noise)

    return volume, (lesion_mask if add_lesion else None)


def create_synthetic_dicom_file(
    output_path: Path,
    patient_id: str = "SYNTH-PAT-001",
    patient_name: str = "DOE^SYNTHETIC",
    study_uid: str = "1.2.840.10008.1.1.1",
    series_uid: str = "1.2.840.10008.1.1.2",
    sop_uid: str = "1.2.840.10008.1.1.3",
    instance_number: int = 1,
    slice_location: float = 0.0,
    pixel_array: Optional[np.ndarray] = None,
) -> Path:
    """Create a valid synthetic DICOM file using pydicom."""
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if pixel_array is None:
        vol, _ = generate_synthetic_brain_volume(shape=(128, 128, 16))
        pixel_array = vol[:, :, 8]  # slice in middle

    rows, cols = pixel_array.shape
    pixel_data = pixel_array.astype(np.uint16)

    # File meta information header
    file_meta = FileMetaDataset()
    file_meta.MediaStorageSOPClassUID = pydicom.uid.MRImageStorage
    file_meta.MediaStorageSOPInstanceUID = sop_uid
    file_meta.TransferSyntaxUID = ExplicitVRLittleEndian

    # Main DICOM Dataset
    ds = FileDataset(str(output_path), {}, file_meta=file_meta, preamble=b"\x00" * 128)

    # Patient tags
    ds.PatientName = patient_name
    ds.PatientID = patient_id
    ds.PatientBirthDate = "19850101"
    ds.PatientSex = "M"

    # Study tags
    ds.StudyInstanceUID = study_uid
    ds.StudyDate = "20260924"
    ds.StudyTime = "120000"
    ds.StudyDescription = "Synthetic MRI Brain Protocol"
    ds.Modality = "MR"

    # Series tags
    ds.SeriesInstanceUID = series_uid
    ds.SeriesNumber = 1
    ds.SeriesDescription = "T1-weighted Axial"

    # Image/Instance tags
    ds.SOPClassUID = pydicom.uid.MRImageStorage
    ds.SOPInstanceUID = sop_uid
    ds.InstanceNumber = instance_number
    ds.SliceLocation = slice_location
    ds.SliceThickness = 3.0

    # Image Dimensions and Pixel attributes
    ds.Rows = rows
    ds.Columns = cols
    ds.PixelSpacing = [1.0, 1.0]
    ds.BitsAllocated = 16
    ds.BitsStored = 16
    ds.HighBit = 15
    ds.PixelRepresentation = 0  # Unsigned integer
    ds.PhotometricInterpretation = "MONOCHROME2"
    ds.SamplesPerPixel = 1
    ds.WindowCenter = 400
    ds.WindowWidth = 800
    ds.RescaleIntercept = 0
    ds.RescaleSlope = 1

    ds.PixelData = pixel_data.tobytes()
    ds.save_as(str(output_path), enforce_file_format=True)
    return output_path


def create_synthetic_nifti_file(
    output_path: Path,
    shape: Tuple[int, int, int] = (64, 64, 32),
    add_lesion: bool = True,
) -> Path:
    """Create a 3D synthetic NIfTI file (.nii.gz) using nibabel."""
    import nibabel as nib

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    vol, _ = generate_synthetic_brain_volume(shape=shape, add_lesion=add_lesion)

    affine = np.array(
        [
            [1.0, 0.0, 0.0, -32.0],
            [0.0, 1.0, 0.0, -32.0],
            [0.0, 0.0, 2.0, -32.0],
            [0.0, 0.0, 0.0, 1.0],
        ]
    )

    nifti_img = nib.Nifti1Image(vol, affine=affine)
    nib.save(nifti_img, str(output_path))
    return output_path


def main():
    parser = argparse.ArgumentParser(description="Generate synthetic DICOM and NIfTI files.")
    parser.add_argument(
        "--output-dir",
        type=str,
        default="datasets/synthetic",
        help="Directory to save synthetic files.",
    )
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    study_uid = generate_uid()
    series_uid = generate_uid()

    logger.info("Generating synthetic DICOM series...")
    dicom_dir = out_dir / "dicom_series"
    dicom_dir.mkdir(exist_ok=True)

    vol, _ = generate_synthetic_brain_volume(shape=(128, 128, 16))
    for i in range(16):
        sop_uid = generate_uid()
        dcm_path = dicom_dir / f"slice_{i+1:02d}.dcm"
        create_synthetic_dicom_file(
            output_path=dcm_path,
            study_uid=study_uid,
            series_uid=series_uid,
            sop_uid=sop_uid,
            instance_number=i + 1,
            slice_location=float(i * 3.0),
            pixel_array=vol[:, :, i],
        )

    logger.info("Generating synthetic NIfTI volume...")
    nifti_path = out_dir / "brain_t1.nii.gz"
    create_synthetic_nifti_file(nifti_path)

    print(f"Successfully generated synthetic DICOM series at: {dicom_dir}")
    print(f"Successfully generated synthetic NIfTI file at: {nifti_path}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
