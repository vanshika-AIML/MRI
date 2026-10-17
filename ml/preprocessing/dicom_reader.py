"""DICOM reader and metadata extraction utility.

Handles loading .dcm files, extracting clinical DICOM attributes into structured Pydantic
schemas, and converting raw pixel data into windowed/normalized NumPy arrays or PNG slices.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional, Tuple, Union

import numpy as np
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class DICOMMetadata(BaseModel):
    """Extracted metadata from a DICOM image file."""

    patient_id: Optional[str] = Field(None, description="Patient ID")
    patient_name: Optional[str] = Field(None, description="Patient Name")
    patient_birth_date: Optional[str] = Field(None, description="Patient Birth Date (YYYYMMDD)")
    patient_sex: Optional[str] = Field(None, description="Patient Sex (M/F/O)")
    
    study_instance_uid: Optional[str] = Field(None, description="Study Instance UID")
    study_date: Optional[str] = Field(None, description="Study Date (YYYYMMDD)")
    study_description: Optional[str] = Field(None, description="Study Description")
    modality: Optional[str] = Field("MR", description="Modality (MR, CT, etc.)")
    
    series_instance_uid: Optional[str] = Field(None, description="Series Instance UID")
    series_number: Optional[int] = Field(None, description="Series Number")
    series_description: Optional[str] = Field(None, description="Series Description")
    
    sop_instance_uid: Optional[str] = Field(None, description="SOP Instance UID")
    instance_number: Optional[int] = Field(None, description="Instance (Slice) Number")
    
    rows: int = Field(..., description="Image height (rows)")
    columns: int = Field(..., description="Image width (columns)")
    pixel_spacing: Optional[Tuple[float, float]] = Field(None, description="Pixel Spacing (row, col) in mm")
    slice_thickness: Optional[float] = Field(None, description="Slice Thickness in mm")
    slice_location: Optional[float] = Field(None, description="Slice Location in mm")
    
    window_center: Optional[float] = Field(None, description="DICOM Window Center")
    window_width: Optional[float] = Field(None, description="DICOM Window Width")
    rescale_intercept: float = Field(0.0, description="Rescale Intercept")
    rescale_slope: float = Field(1.0, description="Rescale Slope")
    
    photometric_interpretation: Optional[str] = Field(None, description="MONOCHROME1, MONOCHROME2, etc.")


class DICOMReader:
    """Utility class to read, parse, and process DICOM files."""

    def __init__(self, file_path: Union[str, Path]):
        """Initialize DICOM reader with a file path."""
        self.file_path = Path(file_path)
        if not self.file_path.exists():
            raise FileNotFoundError(f"DICOM file not found: {self.file_path}")
        self._dataset = None

    def read(self) -> Any:
        """Lazy read DICOM dataset using pydicom."""
        import pydicom

        if self._dataset is None:
            self._dataset = pydicom.dcmread(str(self.file_path), force=True)
        return self._dataset

    def extract_metadata(self) -> DICOMMetadata:
        """Extract DICOM header metadata into structured DICOMMetadata Pydantic object."""
        ds = self.read()

        def get_val(attr: str, default: Any = None) -> Any:
            val = getattr(ds, attr, default)
            if val is not None:
                val = str(val)
            return val if val != "" else default

        def get_int(attr: str) -> Optional[int]:
            try:
                val = getattr(ds, attr, None)
                return int(val) if val is not None else None
            except (ValueError, TypeError):
                return None

        def get_float(attr: str) -> Optional[float]:
            try:
                val = getattr(ds, attr, None)
                return float(val) if val is not None else None
            except (ValueError, TypeError):
                return None

        # Extract pixel spacing tuple
        pixel_spacing = None
        if hasattr(ds, "PixelSpacing") and ds.PixelSpacing:
            try:
                pixel_spacing = (float(ds.PixelSpacing[0]), float(ds.PixelSpacing[1]))
            except (IndexError, ValueError, TypeError):
                pixel_spacing = None

        # Extract window center / width (can be MultiValue)
        wc = getattr(ds, "WindowCenter", None)
        ww = getattr(ds, "WindowWidth", None)
        if hasattr(wc, "__getitem__"):
            wc = wc[0]
        if hasattr(ww, "__getitem__"):
            ww = ww[0]

        return DICOMMetadata(
            patient_id=get_val("PatientID"),
            patient_name=get_val("PatientName"),
            patient_birth_date=get_val("PatientBirthDate"),
            patient_sex=get_val("PatientSex"),
            study_instance_uid=get_val("StudyInstanceUID"),
            study_date=get_val("StudyDate"),
            study_description=get_val("StudyDescription"),
            modality=get_val("Modality", "MR"),
            series_instance_uid=get_val("SeriesInstanceUID"),
            series_number=get_int("SeriesNumber"),
            series_description=get_val("SeriesDescription"),
            sop_instance_uid=get_val("SOPInstanceUID"),
            instance_number=get_int("InstanceNumber"),
            rows=int(getattr(ds, "Rows", 0)),
            columns=int(getattr(ds, "Columns", 0)),
            pixel_spacing=pixel_spacing,
            slice_thickness=get_float("SliceThickness"),
            slice_location=get_float("SliceLocation"),
            window_center=float(wc) if wc is not None else None,
            window_width=float(ww) if ww is not None else None,
            rescale_intercept=get_float("RescaleIntercept") or 0.0,
            rescale_slope=get_float("RescaleSlope") or 1.0,
            photometric_interpretation=get_val("PhotometricInterpretation"),
        )

    def get_pixel_array(self, apply_rescale: bool = True) -> np.ndarray:
        """Extract raw pixel array, applying RescaleSlope/Intercept if requested."""
        ds = self.read()
        pixel_array = ds.pixel_array.astype(np.float32)

        if apply_rescale:
            intercept = float(getattr(ds, "RescaleIntercept", 0.0))
            slope = float(getattr(ds, "RescaleSlope", 1.0))
            pixel_array = pixel_array * slope + intercept

        # Invert MONOCHROME1 if applicable (0 is white in MONOCHROME1)
        photometric = getattr(ds, "PhotometricInterpretation", "")
        if photometric == "MONOCHROME1":
            pixel_array = np.max(pixel_array) - pixel_array

        return pixel_array

    def get_normalized_image(
        self,
        window_center: Optional[float] = None,
        window_width: Optional[float] = None,
        output_8bit: bool = True,
    ) -> np.ndarray:
        """Apply windowing or min-max normalization to produce an image array (0-255 or 0.0-1.0)."""
        pixel_array = self.get_pixel_array(apply_rescale=True)
        meta = self.extract_metadata()

        wc = window_center if window_center is not None else meta.window_center
        ww = window_width if window_width is not None else meta.window_width

        if wc is not None and ww is not None and ww > 0:
            min_val = wc - (ww / 2.0)
            max_val = wc + (ww / 2.0)
            img = np.clip(pixel_array, min_val, max_val)
            img = (img - min_val) / ww
        else:
            # Fallback to percentile clipping (1st to 99th percentile) to handle high-intensity outliers
            p1, p99 = np.percentile(pixel_array, (1, 99))
            if p99 > p1:
                img = np.clip(pixel_array, p1, p99)
                img = (img - p1) / (p99 - p1)
            else:
                img = np.zeros_like(pixel_array, dtype=np.float32)

        if output_8bit:
            return (img * 255.0).astype(np.uint8)
        return img.astype(np.float32)
