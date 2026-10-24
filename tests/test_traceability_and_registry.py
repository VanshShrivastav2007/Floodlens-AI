import unittest
from unittest.mock import patch, AsyncMock
from starlette.testclient import TestClient
from datetime import datetime, timezone

from backend.app.main import app
from backend.app.schemas.models import (
    AnalysisRunRequest,
    FloodAnalysisResult,
    SensorMode,
    WaterIndexType,
    StudyArea,
    SatelliteSceneMetadata,
    SettlementImpactSummary,
    ValidationMetrics
)
from backend.app.geospatial.nepal_data import geo_registry
from backend.app.services.flood_analyzer import FloodAnalyzerService

class TestTraceabilityAndRegistry(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.analyzer = FloodAnalyzerService()

    def test_new_result_fields_and_defaults(self):
        """Verifies that FloodAnalysisResult includes traceability fields with backward-compatible defaults."""
        study_area = StudyArea(**geo_registry.get_study_area("koshi_basin"))
        dummy_scene = SatelliteSceneMetadata(
            scene_id="S2B_TEST",
            acquisition_date="2024-09-20",
            cloud_cover_percent=12.0,
            bounding_box=study_area.bbox,
            bands=["B03", "B08", "B11"]
        )
        dummy_impact = SettlementImpactSummary(
            total_settlements_analyzed=1,
            critical_count=0,
            high_count=0,
            moderate_count=0,
            monitoring_count=0,
            safe_count=1,
            total_exposed_population=0,
            critical_infrastructure_count=0,
            settlements=[]
        )
        dummy_val = ValidationMetrics(
            validation_status="UNAVAILABLE_REFERENCE_DATA",
            notes="No reference data"
        )

        res = FloodAnalysisResult(
            run_id="run_test_001",
            timestamp=datetime.now(timezone.utc).isoformat(),
            study_area=study_area,
            provider_used="Test Provider",
            utm_zone_crs="EPSG:32645",
            pre_scene=dummy_scene,
            post_scene=dummy_scene,
            water_index_used=WaterIndexType.MNDWI,
            threshold_applied=0.05,
            total_study_area_sqkm=3310.0,
            permanent_water_sqkm=50.0,
            pre_flood_water_sqkm=50.0,
            post_flood_water_sqkm=60.0,
            newly_inundated_sqkm=10.0,
            newly_inundated_hectares=1000.0,
            cloud_masked_sqkm=20.0,
            cloud_mask_percentage=2.0,
            valid_observation_percent=98.0,
            impact_summary=dummy_impact,
            validation=dummy_val,
            raster_outputs={},
            vector_outputs={}
        )

        # Assert default traceability fields
        self.assertFalse(res.degraded_mode)
        self.assertIsNone(res.degraded_warning)
        self.assertIsInstance(res.pipeline_configuration, dict)
        self.assertIsNone(res.water_index_details)
        self.assertIsNone(res.mmu_details)

    def test_registered_basin_and_district_lookup(self):
        """Verifies geo_registry correctly resolves basins and registered Terai districts with valid geometry."""
        # Test Basin lookup
        koshi = geo_registry.get_study_area("koshi_basin")
        self.assertIsNotNone(koshi)
        self.assertEqual(koshi["area_type"], "basin")
        self.assertEqual(len(koshi["bbox"]), 4)
        self.assertIn("coordinates", koshi["polygon"])

        # Test District lookup
        sunsari = geo_registry.get_study_area("sunsari")
        self.assertIsNotNone(sunsari)
        self.assertEqual(sunsari["area_type"], "district")
        self.assertEqual(len(sunsari["bbox"]), 4)
        self.assertIn("coordinates", sunsari["polygon"])

        # Test Region lookup
        region = geo_registry.get_study_area("nepal_terai")
        self.assertIsNotNone(region)
        self.assertEqual(region["area_type"], "region")

        # Test API endpoint resolution for district
        res_district = self.client.get("/api/study-areas/sunsari")
        self.assertEqual(res_district.status_code, 200)
        self.assertEqual(res_district.json()["id"], "sunsari")

        # Test scenes query for district
        res_scenes = self.client.get("/api/satellite-scenes?study_area_id=sunsari")
        self.assertEqual(res_scenes.status_code, 200)
        self.assertIn("scenes", res_scenes.json())

    def test_unknown_study_area_returns_404(self):
        """Verifies unknown study area identifiers return HTTP 404 rather than silently using Koshi Basin."""
        res_get = self.client.get("/api/study-areas/non_existent_id_xyz")
        self.assertEqual(res_get.status_code, 404)
        self.assertIn("not found in registry", res_get.json()["detail"])

        res_scenes = self.client.get("/api/satellite-scenes?study_area_id=non_existent_id_xyz")
        self.assertEqual(res_scenes.status_code, 404)
        self.assertIn("not found in registry", res_scenes.json()["detail"])

        res_analyze = self.client.post("/api/analyze", json={
            "study_area_id": "non_existent_id_xyz",
            "pre_flood_date_start": "2024-09-01",
            "pre_flood_date_end": "2024-09-25",
            "post_flood_date_start": "2024-09-26",
            "post_flood_date_end": "2024-10-15"
        })
        self.assertEqual(res_analyze.status_code, 404)
        self.assertIn("not found in registry", res_analyze.json()["detail"])

    def test_full_analysis_traceability_contents(self):
        """Executes full analysis and verifies pipeline_configuration, water_index_details, and mmu_details."""
        payload = {
            "study_area_id": "koshi_basin",
            "pre_flood_date_start": "2024-09-01",
            "pre_flood_date_end": "2024-09-25",
            "post_flood_date_start": "2024-09-26",
            "post_flood_date_end": "2024-10-15",
            "max_cloud_cover_percent": 50.0,
            "water_index": "MNDWI",
            "water_threshold": 0.05,
            "filter_permanent_water": True,
            "min_mapping_unit_pixels": 5,
            "sensor_mode": "SENTINEL_2_OPTICAL"
        }
        res = self.client.post("/api/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # 1. Pipeline configuration snapshot
        self.assertIn("pipeline_configuration", data)
        cfg = data["pipeline_configuration"]
        self.assertEqual(cfg["study_area_id"], "koshi_basin")
        self.assertEqual(cfg["sensor_mode_requested"], "SENTINEL_2_OPTICAL")
        self.assertEqual(cfg["sensor_mode_effective"], "SENTINEL_2_OPTICAL")
        self.assertFalse(cfg["degraded_mode"])
        self.assertEqual(cfg["water_index"], "MNDWI")
        self.assertEqual(cfg["water_threshold"], 0.05)
        self.assertEqual(cfg["min_mapping_unit_pixels"], 5)
        self.assertTrue(cfg["filter_permanent_water"])
        self.assertIn("resolved_at_utc", cfg)

        # 2. Water index details
        self.assertIn("water_index_details", data)
        wid = data["water_index_details"]
        self.assertIn("MNDWI", wid["algorithm"])
        self.assertIn("(B03 - B11)", wid["formula"])
        self.assertEqual(wid["threshold_applied"], 0.05)
        self.assertIn("B03", str(wid["bands"]))

        # 3. MMU details
        self.assertIn("mmu_details", data)
        mmu = data["mmu_details"]
        self.assertEqual(mmu["min_mapping_unit_pixels"], 5)
        self.assertEqual(mmu["neighborhood_connectivity"], 8)
        self.assertGreater(mmu["effective_mmu_area_hectares"], 0.0)
        self.assertEqual(mmu["native_sensor_gsd_m"], 10.0)
        self.assertIn("resolution_notes", mmu)

        # 4. Degraded mode false for nominal optical
        self.assertFalse(data["degraded_mode"])
        self.assertIsNone(data["degraded_warning"])

    def test_dual_sensor_mode_both_available(self):
        """Verifies nominal Dual-Sensor synergy reports degraded_mode=False and produces both SAR and Synergy blocks."""
        payload = {
            "study_area_id": "koshi_basin",
            "pre_flood_date_start": "2024-09-01",
            "pre_flood_date_end": "2024-09-25",
            "post_flood_date_start": "2024-09-26",
            "post_flood_date_end": "2024-10-15",
            "sensor_mode": "DUAL_SENSOR_SYNERGY",
            "water_index": "MNDWI",
            "sar_polarization": "VV"
        }
        res = self.client.post("/api/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["sensor_mode"], "DUAL_SENSOR_SYNERGY")
        self.assertFalse(data["degraded_mode"])
        self.assertIsNone(data["degraded_warning"])
        self.assertIsNotNone(data["sar_result"])
        self.assertIsNotNone(data["synergy_result"])
        self.assertEqual(data["pipeline_configuration"]["sensor_mode_effective"], "DUAL_SENSOR_SYNERGY")

    def test_dual_sensor_mode_sar_unavailable_fallback(self):
        """Verifies that if SAR is unavailable during Dual-Sensor synergy, the pipeline gracefully falls back to Optical and explicitly reports degraded_mode=True."""
        req = AnalysisRunRequest(
            study_area_id="koshi_basin",
            pre_flood_date_start="2024-09-01",
            pre_flood_date_end="2024-09-25",
            post_flood_date_start="2024-09-26",
            post_flood_date_end="2024-10-15",
            sensor_mode=SensorMode.DUAL_SENSOR_SYNERGY
        )

        # Mock find_paired_sar_scenes to simulate SAR unavailability
        with patch.object(self.analyzer.sar_service, "find_paired_sar_scenes", new=AsyncMock(return_value=(None, None))):
            import asyncio
            result = asyncio.run(self.analyzer.execute_flood_analysis(req))

            self.assertTrue(result.degraded_mode)
            self.assertIsNotNone(result.degraded_warning)
            self.assertIn("degraded to Sentinel-2 Optical fallback", result.degraded_warning)
            self.assertIn("DEGRADED: Sentinel-2 Optical Fallback", result.provider_used)
            self.assertIsNone(result.synergy_result)
            self.assertGreater(result.newly_inundated_sqkm, 0.0)
            self.assertEqual(result.pipeline_configuration["sensor_mode_effective"], "SENTINEL_2_OPTICAL")
            self.assertTrue(result.pipeline_configuration["is_degraded_fallback"])

    def test_dual_sensor_mode_both_unavailable_raises_error(self):
        """Verifies that if both sensors are unavailable, the pipeline raises ValueError instead of fabricating data."""
        req = AnalysisRunRequest(
            study_area_id="koshi_basin",
            pre_flood_date_start="2024-09-01",
            pre_flood_date_end="2024-09-25",
            post_flood_date_start="2024-09-26",
            post_flood_date_end="2024-10-15",
            sensor_mode=SensorMode.DUAL_SENSOR_SYNERGY
        )

        with patch.object(self.analyzer.satellite_service, "find_best_scenes_multi_tile", new=AsyncMock(return_value=[])), \
             patch.object(self.analyzer.satellite_service, "find_best_scene", new=AsyncMock(return_value=None)), \
             patch.object(self.analyzer.sar_service, "find_paired_sar_scenes", new=AsyncMock(return_value=(None, None))):
            import asyncio
            with self.assertRaises(ValueError) as ctx:
                asyncio.run(self.analyzer.execute_flood_analysis(req))
            self.assertIn("Dual-Sensor Synergy pipeline failed", str(ctx.exception))

if __name__ == '__main__':
    unittest.main()
