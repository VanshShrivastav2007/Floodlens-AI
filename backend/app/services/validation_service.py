"""
Validation Engine for Flood Extent Accuracy Assessment.
Provides rigorous verification against documented reference datasets (e.g., Copernicus EMS, ICIMOD).
When no verified reference dataset is configured for an event, returns an honest UNAVAILABLE_REFERENCE_DATA
status with no fabricated precision/recall/F1 metrics.
"""

import os
import json
import numpy as np
from typing import Dict, Any, List, Optional
import rasterio
from rasterio.warp import reproject, Resampling
from ..schemas.models import ValidationMetrics
from ..geospatial.raster_processor import calculate_projected_area

REFERENCE_DIR = os.path.abspath("data/reference")

class ValidationService:
    def __init__(self, reference_dir: Optional[str] = None):
        self.reference_dir = reference_dir or REFERENCE_DIR
        os.makedirs(self.reference_dir, exist_ok=True)

    def find_reference_dataset(self, study_area_id: str, event_date: Optional[str] = None) -> Optional[str]:
        """
        Locates any verified reference dataset file (.tif, .geojson) matching the study area and event date.
        Never fabricates a dataset when none exists.
        """
        if not os.path.exists(self.reference_dir):
            return None

        # Look for explicit files, e.g., koshi_basin_reference.tif or koshi_basin_ems.geojson
        candidates = [
            f"{study_area_id}_reference.tif",
            f"{study_area_id}_copernicus_ems.tif",
            f"{study_area_id}_icimod.tif",
            f"{study_area_id}_reference.geojson"
        ]

        for cand in candidates:
            p = os.path.join(self.reference_dir, cand)
            if os.path.isfile(p):
                return p

        return None

    def validate_detection(
        self,
        detected_flood_mask: np.ndarray,
        valid_observation_mask: np.ndarray,
        bbox: List[float],
        study_area_id: str = "koshi_basin",
        event_date: Optional[str] = None,
        reference_path: Optional[str] = None
    ) -> ValidationMetrics:
        """
        Calculates pixel-level confusion matrix against verified reference data.
        If no verified ground-truth dataset is available on disk, explicitly reports
        UNAVAILABLE_REFERENCE_DATA and returns None for all metric scores.
        """
        ref_file = reference_path or self.find_reference_dataset(study_area_id, event_date)

        if not ref_file or not os.path.isfile(ref_file):
            return ValidationMetrics(
                reference_dataset="None",
                reference_date="N/A",
                true_positives_sqkm=None,
                false_positives_sqkm=None,
                false_negatives_sqkm=None,
                true_negatives_sqkm=None,
                precision=None,
                recall=None,
                f1_score=None,
                iou_jaccard=None,
                overall_accuracy=None,
                validation_status="UNAVAILABLE_REFERENCE_DATA",
                notes=(
                    f"Validation unavailable: no verified ground-truth reference flood extent "
                    f"is configured for '{study_area_id}'. Place a verified reference GeoTIFF or GeoJSON "
                    f"in 'data/reference/' to enable scientific accuracy assessment."
                )
            )

        # Genuine reference dataset exists: load and evaluate
        try:
            return self._evaluate_against_file(
                ref_file=ref_file,
                detected_flood_mask=detected_flood_mask,
                valid_observation_mask=valid_observation_mask,
                bbox=bbox,
                study_area_id=study_area_id
            )
        except Exception as e:
            return ValidationMetrics(
                reference_dataset=os.path.basename(ref_file),
                reference_date="Unknown",
                true_positives_sqkm=None,
                false_positives_sqkm=None,
                false_negatives_sqkm=None,
                true_negatives_sqkm=None,
                precision=None,
                recall=None,
                f1_score=None,
                iou_jaccard=None,
                overall_accuracy=None,
                validation_status="REFERENCE_PARSE_ERROR",
                notes=f"Error evaluating reference file {os.path.basename(ref_file)}: {str(e)}"
            )

    def _evaluate_against_file(
        self,
        ref_file: str,
        detected_flood_mask: np.ndarray,
        valid_observation_mask: np.ndarray,
        bbox: List[float],
        study_area_id: str
    ) -> ValidationMetrics:
        """
        Reads reference raster, reprojects to analysis grid, and calculates genuine confusion matrix.
        """
        rows, cols = detected_flood_mask.shape

        with rasterio.open(ref_file) as src:
            # Reproject reference raster to match analysis grid
            ref_resampled = np.zeros((rows, cols), dtype=np.uint8)
            reproject(
                source=rasterio.band(src, 1),
                destination=ref_resampled,
                src_transform=src.transform,
                src_crs=src.crs,
                dst_transform=rasterio.transform.from_bounds(bbox[0], bbox[1], bbox[2], bbox[3], cols, rows),
                dst_crs="EPSG:4326",
                resampling=Resampling.nearest
            )

        reference_water_mask = (ref_resampled == 1)

        return self.calculate_confusion_matrix(
            detected_flood_mask=detected_flood_mask,
            reference_water_mask=reference_water_mask,
            valid_observation_mask=valid_observation_mask,
            bbox=bbox,
            ref_name=os.path.basename(ref_file)
        )

    def calculate_confusion_matrix(
        self,
        detected_flood_mask: np.ndarray,
        reference_water_mask: np.ndarray,
        valid_observation_mask: np.ndarray,
        bbox: List[float],
        ref_name: str = "Verified Reference"
    ) -> ValidationMetrics:
        """
        Calculates exact confusion matrix (TP, FP, FN, TN), Precision, Recall, F1, and IoU.
        Restricts evaluation strictly to valid, cloud-free observation pixels.
        """
        rows, cols = detected_flood_mask.shape

        # Restrict evaluation strictly to pixels where BOTH detected and reference data are valid
        d = detected_flood_mask & valid_observation_mask
        r = reference_water_mask & valid_observation_mask
        v = valid_observation_mask

        tp_mask = d & r
        fp_mask = d & (~r) & v
        fn_mask = (~d) & r & v
        tn_mask = (~d) & (~r) & v

        tp_pixels = int(np.sum(tp_mask))
        fp_pixels = int(np.sum(fp_mask))
        fn_pixels = int(np.sum(fn_mask))
        tn_pixels = int(np.sum(tn_mask))

        tp_sqkm, _, _ = calculate_projected_area(tp_pixels, bbox, cols, rows)
        fp_sqkm, _, _ = calculate_projected_area(fp_pixels, bbox, cols, rows)
        fn_sqkm, _, _ = calculate_projected_area(fn_pixels, bbox, cols, rows)
        tn_sqkm, _, _ = calculate_projected_area(tn_pixels, bbox, cols, rows)

        precision = tp_pixels / (tp_pixels + fp_pixels) if (tp_pixels + fp_pixels) > 0 else 0.0
        recall = tp_pixels / (tp_pixels + fn_pixels) if (tp_pixels + fn_pixels) > 0 else 0.0
        f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0
        iou = tp_pixels / (tp_pixels + fp_pixels + fn_pixels) if (tp_pixels + fp_pixels + fn_pixels) > 0 else 0.0
        total_eval = tp_pixels + fp_pixels + fn_pixels + tn_pixels
        accuracy = (tp_pixels + tn_pixels) / total_eval if total_eval > 0 else 0.0

        notes = (
            f"Evaluated against verified reference dataset '{ref_name}' across "
            f"{round(tp_sqkm + fp_sqkm + fn_sqkm + tn_sqkm, 1)} sq km cloud-free comparison area. "
            f"Evaluated valid pixels: {total_eval:,}."
        )

        return ValidationMetrics(
            reference_dataset=ref_name,
            reference_date="Verified Event Ground Truth",
            true_positives_sqkm=tp_sqkm,
            false_positives_sqkm=fp_sqkm,
            false_negatives_sqkm=fn_sqkm,
            true_negatives_sqkm=tn_sqkm,
            precision=round(precision, 4),
            recall=round(recall, 4),
            f1_score=round(f1, 4),
            iou_jaccard=round(iou, 4),
            overall_accuracy=round(accuracy, 4),
            validation_status="VERIFIED_REFERENCE",
            notes=notes
        )
