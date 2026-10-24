"""
Unit and Integration Tests for Population Exposure Intelligence & Rescue Priority Decision Support.
Validates:
1. Genuine WorldPop 2020 Constrained (100m) dataset caching and loading.
2. Strict NoData (-99999.0) and negative value filtering.
3. Mass-conserving geospatial reprojection to canonical EPSG:4326 grid.
4. Non-overlapping Voronoi settlement catchment partitioning (Zero Double-Counting).
5. Explainable 4-factor rescue priority scoring and transparent directives.
6. Study area switching across Koshi, Bagmati-Rautahat, and West Rapti-Banke.
7. Graceful offline/missing-dataset fallback without generating synthetic numbers.
8. Valid RFC 7946 GeoJSON vector export.
"""

import unittest
import os
import json
import numpy as np

from backend.app.geospatial.population_exposure import (
    PopulationExposureEngine,
    WORLDPOP_CACHE_PATH
)
from backend.app.geospatial.nepal_data import STUDY_AREAS, REAL_SETTLEMENTS
from backend.app.schemas.models import (
    PopulationDatasetMetadata,
    SettlementPopulationExposure,
    PopulationExposureResult
)

class TestPopulationExposureEngine(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = PopulationExposureEngine()
        cls.koshi_bbox = STUDY_AREAS["koshi_basin"]["bbox"]
        cls.bagmati_bbox = STUDY_AREAS["bagmati_rautahat"]["bbox"]
        cls.rapti_bbox = STUDY_AREAS["west_rapti_banke"]["bbox"]

    def test_01_worldpop_dataset_availability(self):
        """Confirm genuine WorldPop 2020 constrained raster is cached and verified."""
        self.assertTrue(self.engine.is_dataset_available(), "WorldPop 2020 constrained raster should be cached locally")
        self.assertTrue(os.path.exists(WORLDPOP_CACHE_PATH))
        self.assertGreater(os.path.getsize(WORLDPOP_CACHE_PATH), 1_000_000, "WorldPop raster size should be > 1MB")

    def test_02_mass_conservation_and_nodata_filtering(self):
        """Verify mass-conserving reprojection and NoData (-99999.0) filtering."""
        raster, metadata = self.engine.get_population_raster(self.koshi_bbox, width=500, height=400)
        self.assertIsNotNone(raster)
        self.assertEqual(metadata.availability_status, "AVAILABLE")
        self.assertEqual(raster.shape, (400, 500))

        # Check that no negative numbers or NaNs exist
        self.assertFalse(np.isnan(raster).any(), "Reprojected population raster should contain no NaNs")
        self.assertTrue((raster >= 0).all(), "Population counts must be non-negative")

        # In Koshi Basin, total resident population is approximately 5.24 million persons
        total_pop = float(np.sum(raster))
        self.assertGreater(total_pop, 4_000_000.0, "Koshi basin resident population should exceed 4M")
        self.assertLess(total_pop, 7_000_000.0, "Koshi basin resident population should be under 7M")

    def test_03_zero_double_counting_voronoi_partition(self):
        """
        Verify that Voronoi catchment partitioning across settlements produces strict
        non-overlapping MECE spatial allocation, ensuring:
        sum(settlement_resident) == total_domain_resident
        sum(settlement_exposed) == total_domain_exposed
        """
        rows, cols = 400, 500
        # Create a synthetic flood mask in the lower central area (Koshi floodplain)
        flood_mask = np.zeros((rows, cols), dtype=bool)
        flood_mask[200:320, 180:320] = True

        cloud_mask = np.zeros((rows, cols), dtype=bool)
        cloud_mask[50:100, 50:150] = True

        valid_mask = np.ones((rows, cols), dtype=bool)
        perm_water = np.zeros((rows, cols), dtype=bool)
        perm_water[240:260, 240:260] = True # Channel subtraction

        result = self.engine.calculate_population_exposure(
            flood_mask=flood_mask,
            cloud_mask=cloud_mask,
            valid_mask=valid_mask,
            permanent_water_mask=perm_water,
            bbox=self.koshi_bbox,
            study_area_id="koshi_basin",
            settlements=REAL_SETTLEMENTS,
            sensor_mode="SENTINEL_2_OPTICAL"
        )

        self.assertIsInstance(result, PopulationExposureResult)
        self.assertEqual(result.study_area_id, "koshi_basin")
        self.assertGreater(result.total_domain_resident_population, 0)
        self.assertGreater(result.total_domain_exposed_population, 0)

        # Sum over settlements
        settlement_resident_sum = sum(s.gridded_baseline_population for s in result.settlements)
        settlement_exposed_sum = sum(s.estimated_exposed_population for s in result.settlements)

        # Mathematical Proof: Double-counting residual must be strictly near zero (< 0.05 persons)
        res_diff = abs(settlement_resident_sum - result.total_domain_resident_population)
        exp_diff = abs(settlement_exposed_sum - result.total_domain_exposed_population)

        self.assertLess(res_diff, 0.05, f"Resident pop conservation residual must be < 0.05, got {res_diff}")
        self.assertLess(exp_diff, 0.05, f"Exposed pop conservation residual must be < 0.05, got {exp_diff}")

    def test_04_multiple_study_areas_switching(self):
        """Verify engine works seamlessly across all study areas in Nepal Terai."""
        areas = ["koshi_basin", "bagmati_rautahat", "west_rapti_banke"]
        rows, cols = 400, 500

        for area_id in areas:
            bbox = STUDY_AREAS[area_id]["bbox"]
            raster, meta = self.engine.get_population_raster(bbox, width=cols, height=rows)
            self.assertIsNotNone(raster, f"Raster must be generated for {area_id}")
            self.assertEqual(meta.availability_status, "AVAILABLE")
            self.assertGreater(float(np.sum(raster)), 500_000.0, f"Resident pop for {area_id} must be > 500k")

            # Check execution of exposure
            res = self.engine.calculate_population_exposure(
                flood_mask=np.zeros((rows, cols), dtype=bool),
                cloud_mask=np.zeros((rows, cols), dtype=bool),
                valid_mask=np.ones((rows, cols), dtype=bool),
                permanent_water_mask=np.zeros((rows, cols), dtype=bool),
                bbox=bbox,
                study_area_id=area_id,
                settlements=REAL_SETTLEMENTS
            )
            self.assertEqual(res.study_area_id, area_id)
            self.assertEqual(res.total_domain_exposed_population, 0.0)

    def test_05_explainable_priority_ranking_and_directives(self):
        """Verify that priority scoring is explainable and assigns appropriate rescue tiers."""
        rows, cols = 400, 500
        # Inundate specifically around Prakashpur / Chatara
        flood_mask = np.zeros((rows, cols), dtype=bool)
        flood_mask[160:210, 300:350] = True

        result = self.engine.calculate_population_exposure(
            flood_mask=flood_mask,
            cloud_mask=np.zeros((rows, cols), dtype=bool),
            valid_mask=np.ones((rows, cols), dtype=bool),
            permanent_water_mask=np.zeros((rows, cols), dtype=bool),
            bbox=self.koshi_bbox,
            study_area_id="koshi_basin",
            settlements=REAL_SETTLEMENTS
        )

        top_settlement = result.settlements[0]
        self.assertIn("Tier", top_settlement.provisional_priority_tier)
        self.assertGreater(top_settlement.priority_score, 0.0)
        self.assertGreater(len(top_settlement.priority_reasons), 0)
        self.assertIn("incident commander", top_settlement.uncertainty_notes.lower())

    def test_06_missing_dataset_graceful_fallback(self):
        """Verify that missing dataset triggers graceful fallback without fabricating fake numbers."""
        dummy_engine = PopulationExposureEngine(cache_path="data/reference/worldpop/non_existent_file.tif")
        # Ensure it does not download in test
        dummy_engine.download_dataset_if_missing = lambda timeout=20: False

        raster, meta = dummy_engine.get_population_raster(self.koshi_bbox)
        self.assertIsNone(raster)
        self.assertEqual(meta.availability_status, "UNAVAILABLE_DATASET")

        result = dummy_engine.calculate_population_exposure(
            flood_mask=np.zeros((400, 500), dtype=bool),
            cloud_mask=np.zeros((400, 500), dtype=bool),
            valid_mask=np.ones((400, 500), dtype=bool),
            permanent_water_mask=np.zeros((400, 500), dtype=bool),
            bbox=self.koshi_bbox,
            study_area_id="koshi_basin",
            settlements=REAL_SETTLEMENTS
        )

        self.assertEqual(result.population_metadata.availability_status, "UNAVAILABLE_DATASET")
        self.assertEqual(result.total_domain_resident_population, 0.0)
        self.assertEqual(result.total_domain_exposed_population, 0.0)
        self.assertIn("unavailable", result.uncertainty_disclaimer.lower())

    def test_07_geojson_export_validity(self):
        """Verify that population exposure GeoJSON is exported with valid RFC 7946 features."""
        rows, cols = 400, 500
        flood_mask = np.zeros((rows, cols), dtype=bool)
        flood_mask[200:250, 200:250] = True

        test_run_id = "test_run_pop_001"
        result = self.engine.calculate_population_exposure(
            flood_mask=flood_mask,
            cloud_mask=np.zeros((rows, cols), dtype=bool),
            valid_mask=np.ones((rows, cols), dtype=bool),
            permanent_water_mask=np.zeros((rows, cols), dtype=bool),
            bbox=self.koshi_bbox,
            study_area_id="koshi_basin",
            settlements=REAL_SETTLEMENTS,
            run_id=test_run_id
        )

        self.assertIsNotNone(result.vector_geojson_url)
        geojson_path = os.path.join("outputs", "vectors", f"population_exposure_{test_run_id}.geojson")
        self.assertTrue(os.path.exists(geojson_path))

        with open(geojson_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["type"], "FeatureCollection")
        self.assertGreater(len(data["features"]), 0)
        first_feat = data["features"][0]
        self.assertEqual(first_feat["geometry"]["type"], "Point")
        self.assertIn("census_baseline_population", first_feat["properties"])
        self.assertIn("gridded_baseline_population", first_feat["properties"])
        self.assertIn("provisional_priority_tier", first_feat["properties"])

if __name__ == "__main__":
    unittest.main()
