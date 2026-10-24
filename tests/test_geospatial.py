import unittest
import numpy as np
from backend.app.geospatial.indices import (
    calculate_ndwi,
    calculate_mndwi,
    compute_otsu_threshold,
    create_cloud_mask_scl,
    detect_flood_extent
)
from backend.app.geospatial.raster_processor import calculate_projected_area, assess_settlement_impacts
from backend.app.services.validation_service import ValidationService

class TestGeospatial(unittest.TestCase):
    def test_water_indices_math(self):
        green = np.array([[0.15, 0.10], [0.12, 0.08]], dtype=np.float32)
        nir = np.array([[0.02, 0.40], [0.03, 0.35]], dtype=np.float32)

        # Pixel (0,0): Water (high green 0.15, low nir 0.02) -> NDWI = (0.15 - 0.02)/(0.15 + 0.02) = 0.13 / 0.17 = 0.764
        ndwi = calculate_ndwi(green, nir)
        self.assertGreater(ndwi[0, 0], 0.7)
        # Pixel (0,1): Vegetation (low green 0.10, high nir 0.40) -> NDWI is strongly negative
        self.assertLess(ndwi[0, 1], -0.5)

    def test_zero_division_protection(self):
        green = np.zeros((3, 3), dtype=np.float32)
        nir = np.zeros((3, 3), dtype=np.float32)
        ndwi = calculate_ndwi(green, nir)
        self.assertFalse(np.isnan(ndwi).any())
        self.assertFalse(np.isinf(ndwi).any())

    def test_cloud_masking_scl(self):
        # SCL values: 3=cloud shadow, 8=cloud med, 9=cloud high, 4=vegetation, 6=water
        scl = np.array([[4, 6], [9, 3]], dtype=np.uint8)
        mask = create_cloud_mask_scl(scl)
        self.assertFalse(mask[0, 0]) # Vegetation is clear
        self.assertFalse(mask[0, 1]) # Water is clear
        self.assertTrue(mask[1, 0])  # Cloud high is masked
        self.assertTrue(mask[1, 1])  # Cloud shadow is masked

    def test_flood_detection_change_logic(self):
        pre_water = np.array([[1, 0], [0, 0]], dtype=np.uint8)
        post_water = np.array([[1, 1], [0, 1]], dtype=np.uint8)
        pre_cloud = np.array([[False, False], [False, False]], dtype=bool)
        post_cloud = np.array([[False, False], [False, True]], dtype=bool)

        detection = detect_flood_extent(
            pre_water=pre_water,
            post_water=post_water,
            pre_cloud=pre_cloud,
            post_cloud=post_cloud,
            filter_permanent=True,
            min_mmu_pixels=1
        )

        newly = detection["newly_inundated"]
        self.assertFalse(newly[0, 0]) # Permanent water excluded
        self.assertTrue(newly[0, 1])  # Newly inundated flood detected
        self.assertFalse(newly[1, 0]) # Dry land
        self.assertFalse(newly[1, 1]) # Cloud-masked pixel excluded

    def test_projected_area_dynamic_utm(self):
        # Eastern/Central Nepal: Koshi Basin (lon > 84°E) -> UTM 45N (EPSG:32645)
        bbox_koshi = [86.75, 26.35, 87.35, 26.85]
        sqkm_k, ha_k, crs_k = calculate_projected_area(1000, bbox_koshi, 500, 400)
        self.assertGreater(sqkm_k, 0.0)
        self.assertLess(abs(ha_k - (sqkm_k * 100.0)), 0.5)
        self.assertIn("32645", crs_k)

        # Western Nepal: West Rapti Basin (lon < 84°E) -> UTM 44N (EPSG:32644)
        bbox_rapti = [81.50, 27.80, 82.00, 28.20]
        sqkm_r, ha_r, crs_r = calculate_projected_area(1000, bbox_rapti, 500, 400)
        self.assertGreater(sqkm_r, 0.0)
        self.assertIn("32644", crs_r)

    def test_honest_validation_without_reference(self):
        val_service = ValidationService()
        detected = np.array([[True, True], [False, False]], dtype=bool)
        valid = np.ones((2, 2), dtype=bool)
        bbox = [86.75, 26.35, 87.35, 26.85]

        metrics = val_service.validate_detection(
            detected_flood_mask=detected,
            valid_observation_mask=valid,
            bbox=bbox,
            study_area_id="koshi_basin"
        )

        self.assertEqual(metrics.validation_status, "UNAVAILABLE_REFERENCE_DATA")
        self.assertIsNone(metrics.precision)
        self.assertIsNone(metrics.recall)
        self.assertIsNone(metrics.f1_score)

    def test_validation_confusion_matrix_with_reference(self):
        val_service = ValidationService()
        detected = np.array([[True, True], [False, False]], dtype=bool)
        reference = np.array([[True, False], [True, False]], dtype=bool)
        valid = np.ones((2, 2), dtype=bool)
        bbox = [86.75, 26.35, 87.35, 26.85]

        metrics = val_service.calculate_confusion_matrix(
            detected_flood_mask=detected,
            reference_water_mask=reference,
            valid_observation_mask=valid,
            bbox=bbox,
            ref_name="Ground_Truth_Test"
        )

        self.assertEqual(metrics.validation_status, "VERIFIED_REFERENCE")
        self.assertAlmostEqual(metrics.precision, 0.5, places=2)
        self.assertAlmostEqual(metrics.recall, 0.5, places=2)
        self.assertAlmostEqual(metrics.f1_score, 0.5, places=2)
        self.assertAlmostEqual(metrics.iou_jaccard, 1/3, places=2)

if __name__ == "__main__":
    unittest.main()
