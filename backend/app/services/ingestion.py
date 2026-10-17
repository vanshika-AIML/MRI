"""Ingestion and Preprocessing Service.

Integrates DICOM and NIfTI reader pipelines with backend repositories and file storage.
Extracts clinical metadata, generates 2D preview slices, and populates database records.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from uuid import UUID

from PIL import Image as PILImage
import numpy as np
import sys

_WORKSPACE_ROOT = Path(__file__).resolve().parents[3]
if str(_WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE_ROOT))

from ml.preprocessing.dicom_reader import DICOMReader, DICOMMetadata
from ml.preprocessing.nifti_reader import NIfTIReader, NIfTIMetadata
from ml.preprocessing.transforms import apply_windowing, normalize_intensity_minmax

from app.models.patient import Patient
from app.models.study import Study
from app.models.series import Series
from app.models.image import Image as ImageModel
from app.repositories.patient import PatientRepository
from app.repositories.study import StudyRepository
from app.repositories.series import SeriesRepository
from app.repositories.image import ImageRepository

logger = logging.getLogger(__name__)


class IngestionService:
    """Service for processing medical image uploads and metadata extraction."""

    def __init__(self, db: Session, storage_dir: Optional[Union[str, Path]] = None):
        self.db = db
        self.patient_repo = PatientRepository(db)
        self.study_repo = StudyRepository(db)
        self.series_repo = SeriesRepository(db)
        self.image_repo = ImageRepository(db)

        if storage_dir is None:
            storage_dir = Path("data/storage")
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def process_dicom_file(self, dicom_file_path: Union[str, Path]) -> ImageModel:
        """Process a DICOM file: parse tags, update/create DB entities, save PNG slice."""
        dcm_path = Path(dicom_file_path)
        reader = DICOMReader(dcm_path)
        meta = reader.extract_metadata()

        # 1. Patient Entity
        patient_ext_id = meta.patient_id or "UNKNOWN-PATIENT"
        patient = self.patient_repo.get_by_external_id(patient_ext_id)
        if not patient:
            patient = self.patient_repo.create(
                external_patient_id=patient_ext_id,
            )

        # 2. Study Entity
        study_uid = meta.study_instance_uid or f"STUDY-{dcm_path.stem}"
        study = self.study_repo.get_by_uid(study_uid)
        if not study:
            study = self.study_repo.create(
                patient_id=patient.id,
                study_uid=study_uid,
                description=meta.study_description or "MRI Scan Study",
                modality=meta.modality or "MR",
            )

        # 3. Series Entity
        series_uid = meta.series_instance_uid or f"SERIES-{dcm_path.stem}"
        series = self.series_repo.get_by_series_uid(series_uid)
        if not series:
            series = self.series_repo.create(
                study_id=study.id,
                series_instance_uid=series_uid,
                series_number=meta.series_number or 1,
                series_description=meta.series_description or "T1-weighted Sequence",
            )

        # 4. Save PNG Rendered Slice to Storage
        img_8bit = reader.get_normalized_image(output_8bit=True)
        sop_uid = meta.sop_instance_uid or f"SOP-{dcm_path.stem}"
        slice_filename = f"{sop_uid}.png"
        slice_file_path = self.storage_dir / slice_filename

        pil_img = PILImage.fromarray(img_8bit)
        pil_img.save(slice_file_path)

        # 5. Image Record
        image_record = self.image_repo.create(
            series_id=series.id,
            sop_instance_uid=sop_uid,
            file_path=str(slice_file_path),
            file_format="PNG",
            slice_index=meta.instance_number or 1,
            height=meta.rows,
            width=meta.columns,
        )

        return image_record

    def process_nifti_volume(
        self,
        nifti_file_path: Union[str, Path],
        patient_ext_id: str = "NIFTI-PATIENT",
        study_uid: str = "NIFTI-STUDY-001",
    ) -> List[ImageModel]:
        """Process 3D NIfTI volume: extract middle slices and persist as Images."""
        nii_path = Path(nifti_file_path)
        reader = NIfTIReader(nii_path)
        meta = reader.extract_metadata()

        patient = self.patient_repo.get_by_external_id(patient_ext_id)
        if not patient:
            patient = self.patient_repo.create(external_patient_id=patient_ext_id)

        study = self.study_repo.get_by_uid(study_uid)
        if not study:
            study = self.study_repo.create(
                patient_id=patient.id,
                study_uid=study_uid,
                description="NIfTI 3D Brain Study",
                modality="MR",
            )

        series_uid = f"NIFTI-SERIES-{nii_path.name}"
        series = self.series_repo.get_by_series_uid(series_uid)
        if not series:
            series = self.series_repo.create(
                study_id=study.id,
                series_instance_uid=series_uid,
                series_number=1,
                series_description=f"NIfTI Volume ({meta.dimensions})",
            )

        slices_dict = reader.get_middle_slices()
        created_images = []

        for plane_name, slice_arr in slices_dict.items():
            norm_arr = normalize_intensity_minmax(slice_arr, min_val=0, max_val=255)
            img_8bit = norm_arr.astype(np.uint8)

            slice_filename = f"{series_uid}_{plane_name}.png"
            slice_file_path = self.storage_dir / slice_filename

            pil_img = PILImage.fromarray(img_8bit)
            pil_img.save(slice_file_path)

            sop_uid = f"{series_uid}-{plane_name}"
            image_record = self.image_repo.create(
                series_id=series.id,
                sop_instance_uid=sop_uid,
                file_path=str(slice_file_path),
                file_format="PNG",
                slice_index=1,
                height=img_8bit.shape[0],
                width=img_8bit.shape[1],
            )
            created_images.append(image_record)

        return created_images
