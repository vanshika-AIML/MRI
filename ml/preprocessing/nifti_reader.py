"""NIfTI reader and volume processing utility.

Handles loading 3D/4D NIfTI (.nii, .nii.gz) medical volumes, extracting affine matrix,
voxel spacing, orientation, and slicing into axial, sagittal, and coronal planes.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional, Tuple, Union

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class NIfTIMetadata(BaseModel):
    """Metadata extracted from a NIfTI volume."""

    dimensions: Tuple[int, ...] = Field(..., description="Volume dimensions (x, y, z, ...)")
    voxel_spacing: Tuple[float, ...] = Field(..., description="Voxel dimensions (mm)")
    datatype: str = Field(..., description="Data type of pixel array")
    qform_code: int = Field(0, description="NIfTI qform code")
    sform_code: int = Field(0, description="NIfTI sform code")
    affine: List[List[float]] = Field(..., description="4x4 affine transformation matrix")
    orientation: str = Field("UNKNOWN", description="Voxel orientation code (e.g., RAS, LPS)")


PlaneType = Literal["axial", "sagittal", "coronal"]


class NIfTIReader:
    """Utility class for loading and slicing 3D/4D NIfTI volumes."""

    def __init__(self, file_path: Union[str, Path]):
        """Initialize NIfTI reader with a file path."""
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"NIfTI file not found: {self.file_path}")
        self._img = None

    def read(self) -> Any:
        """Lazy load NIfTI image dataset using nibabel."""
        import nibabel as nib

        if self._img is None:
            self._img = nib.load(str(self.file_path))
        return self._img

    def extract_metadata(self) -> NIfTIMetadata:
        """Extract spatial and voxel metadata from the NIfTI header."""
        import nibabel as nib

        img = self.read()
        header = img.header

        shape = tuple(int(s) for s in img.shape)
        zooms = tuple(float(z) for z in header.get_zooms())
        affine = img.affine.tolist()

        try:
            orientation = "".join(nib.aff2axcodes(img.affine))
        except Exception:
            orientation = "UNKNOWN"

        return NIfTIMetadata(
            dimensions=shape,
            voxel_spacing=zooms,
            datatype=str(header.get_data_dtype()),
            qform_code=int(header.get("qform_code", 0)),
            sform_code=int(header.get("sform_code", 0)),
            affine=affine,
            orientation=orientation,
        )

    def get_fdata(self) -> np.ndarray:
        """Get 3D floating-point volume array."""
        img = self.read()
        return np.asanyarray(img.dataobj, dtype=np.float32)

    def get_slice(
        self,
        slice_index: int,
        plane: PlaneType = "axial",
        volume_index: int = 0,
    ) -> np.ndarray:
        """Extract a single 2D slice along the specified plane.

        Args:
            slice_index: Index of the slice to extract along the orthogonal axis.
            plane: Axis plane - 'axial' (z), 'sagittal' (x), or 'coronal' (y).
            volume_index: For 4D MRI volumes (e.g. fMRI / diffusion), index of 3D frame.

        Returns:
            2D numpy float32 array for the slice.
        """
        data = self.get_fdata()
        if data.ndim == 4:
            data = data[..., volume_index]

        shape = data.shape
        if plane == "axial":
            # Slice along z-axis (axis 2)
            idx = max(0, min(slice_index, shape[2] - 1))
            slice_2d = data[:, :, idx]
            # Rotate for standard anatomical display (upright)
            slice_2d = np.rot90(slice_2d)
        elif plane == "sagittal":
            # Slice along x-axis (axis 0)
            idx = max(0, min(slice_index, shape[0] - 1))
            slice_2d = data[idx, :, :]
            slice_2d = np.rot90(slice_2d)
        elif plane == "coronal":
            # Slice along y-axis (axis 1)
            idx = max(0, min(slice_index, shape[1] - 1))
            slice_2d = data[:, idx, :]
            slice_2d = np.rot90(slice_2d)
        else:
            raise ValueError(f"Unsupported plane: {plane}. Must be 'axial', 'sagittal', or 'coronal'.")

        return slice_2d

    def get_middle_slices(self) -> Dict[str, np.ndarray]:
        """Extract middle slices along axial, sagittal, and coronal views."""
        data = self.get_fdata()
        if data.ndim == 4:
            data = data[..., 0]

        shape = data.shape
        mid_x, mid_y, mid_z = shape[0] // 2, shape[1] // 2, shape[2] // 2

        return {
            "axial": self.get_slice(mid_z, plane="axial"),
            "sagittal": self.get_slice(mid_x, plane="sagittal"),
            "coronal": self.get_slice(mid_y, plane="coronal"),
        }
