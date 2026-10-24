import unittest
from starlette.testclient import TestClient
from backend.app.main import app

class TestAPIEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_root_endpoint(self):
        res = self.client.get("/")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("Nepal Terai Flood Intelligence", data["title"])

    def test_status_endpoint(self):
        res = self.client.get("/api/status")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "OPERATIONAL")
        self.assertIn("Dynamic UTM", data["geodesic_projections"])

    def test_study_areas_endpoint(self):
        res = self.client.get("/api/study-areas")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(len(data), 0)
        area_ids = [a["id"] for a in data]
        self.assertIn("koshi_basin", area_ids)

    def test_settlements_endpoint(self):
        res = self.client.get("/api/settlements?study_area_id=koshi_basin")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreater(len(data), 0)
        names = [s["name"] for s in data]
        self.assertIn("Inaruwa", names)
        self.assertIn("Prakashpur", names)

    def test_satellite_scenes_endpoint(self):
        res = self.client.get("/api/satellite-scenes?study_area_id=koshi_basin")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("scenes", data)
        self.assertGreater(data["count"], 0)

    def test_full_analysis_workflow(self):
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
            "data_source": "Sentinel-2 L2A (Harmonized)"
        }
        res = self.client.post("/api/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        result = res.json()
        self.assertIn("run_id", result)
        self.assertGreater(result["newly_inundated_sqkm"], 0.0)
        self.assertGreater(result["impact_summary"]["total_exposed_population"], 0)
        self.assertEqual(result["validation"]["validation_status"], "UNAVAILABLE_REFERENCE_DATA")
        self.assertIn("low_coverage_warning", result)
        self.assertGreater(result["valid_observation_percent"], 0.0)
        self.assertTrue(result["is_mosaic"])
        self.assertIn("45RVK", result["tiles_mosaicked"])
        self.assertIn("45RWK", result["tiles_mosaicked"])
        self.assertAlmostEqual(result["nodata_mask_percentage"], 0.0, places=1)
        self.assertGreater(result["valid_observation_percent"], 40.0)

        # Test retrieving result
        run_id = result["run_id"]
        res_get = self.client.get(f"/api/results/{run_id}")
        self.assertEqual(res_get.status_code, 200)

        # Test report HTML generation
        res_report = self.client.get(f"/api/reports/{run_id}")
        self.assertEqual(res_report.status_code, 200)
        self.assertIn("RAPID FLOOD EXTENT", res_report.text)
        self.assertIn("MULTI-GRANULE MOSAIC", res_report.text)
        if result["low_coverage_warning"]:
            self.assertIn("LOW OBSERVATION COVERAGE WARNING", res_report.text)

        # Test georeferencing of exported GeoTIFF
        import rasterio
        geotiff_rel = result["raster_outputs"]["geotiff"].lstrip("/")
        with rasterio.open(geotiff_rel) as src:
            self.assertEqual(src.crs.to_string(), "EPSG:4326")
            self.assertAlmostEqual(src.bounds.left, 86.75, places=3)
            self.assertAlmostEqual(src.bounds.right, 87.35, places=3)

    def test_single_tile_fallback_workflow(self):
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
            "data_source": "Sentinel-2 L2A (Harmonized)",
            "enable_mosaicing": False
        }
        res = self.client.post("/api/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        result = res.json()
        self.assertFalse(result["is_mosaic"])
        self.assertEqual(len(result["tiles_mosaicked"]), 1)
        self.assertGreater(result["newly_inundated_sqkm"], 0.0)

    def test_unmet_criteria_returns_422(self):
        # Extremely narrow date range with impossible cloud cover (0%)
        payload = {
            "study_area_id": "koshi_basin",
            "pre_flood_date_start": "2024-09-01",
            "pre_flood_date_end": "2024-09-02",
            "post_flood_date_start": "2024-09-26",
            "post_flood_date_end": "2024-09-27",
            "max_cloud_cover_percent": 0.0,
            "water_index": "MNDWI",
            "water_threshold": 0.05,
            "filter_permanent_water": True,
            "min_mapping_unit_pixels": 5,
            "data_source": "Sentinel-2 L2A (Harmonized)"
        }
        res = self.client.post("/api/analyze", json=payload)
        self.assertEqual(res.status_code, 422)
        self.assertIn("No suitable real Sentinel-2 scene found", res.json()["detail"])

    def test_sar_analysis_workflow(self):
        payload = {
            "study_area_id": "koshi_basin",
            "pre_flood_date_start": "2024-09-01",
            "pre_flood_date_end": "2024-09-25",
            "post_flood_date_start": "2024-09-26",
            "post_flood_date_end": "2024-10-15",
            "sensor_mode": "SENTINEL_1_SAR",
            "sar_polarization": "VV",
            "sar_threshold_db": -15.5,
            "sar_change_threshold_db": -2.5,
            "filter_permanent_water": True,
            "min_mapping_unit_pixels": 5
        }
        res = self.client.post("/api/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        result = res.json()
        self.assertEqual(result["sensor_mode"], "SENTINEL_1_SAR")
        self.assertIsNotNone(result.get("sar_result"))
        sar = result["sar_result"]
        self.assertEqual(sar["polarization"], "VV")
        self.assertGreater(sar["sar_newly_inundated_sqkm"], 0.0)
        self.assertGreater(sar["valid_sar_coverage_percent"], 50.0)
        self.assertIn("S1A", sar["pre_scene"]["scene_id"])
        self.assertIn("S1A", sar["post_scene"]["scene_id"])
        self.assertEqual(sar["pre_scene"]["relative_orbit"], 85)

        # Test report generation contains SAR block
        run_id = result["run_id"]
        res_report = self.client.get(f"/api/reports/{run_id}")
        self.assertEqual(res_report.status_code, 200)
        self.assertIn("Sentinel-1 C-SAR Radar Inundation Intelligence", res_report.text)
        self.assertIn("ALL-WEATHER / CLOUD-INDEPENDENT", res_report.text)

    def test_dual_sensor_synergy_workflow(self):
        payload = {
            "study_area_id": "koshi_basin",
            "pre_flood_date_start": "2024-09-01",
            "pre_flood_date_end": "2024-09-25",
            "post_flood_date_start": "2024-09-26",
            "post_flood_date_end": "2024-10-15",
            "sensor_mode": "DUAL_SENSOR_SYNERGY",
            "water_index": "MNDWI",
            "sar_polarization": "VV",
            "filter_permanent_water": True,
            "enable_mosaicing": True
        }
        res = self.client.post("/api/analyze", json=payload)
        self.assertEqual(res.status_code, 200)
        result = res.json()
        self.assertEqual(result["sensor_mode"], "DUAL_SENSOR_SYNERGY")
        self.assertIsNotNone(result.get("sar_result"))
        self.assertIsNotNone(result.get("synergy_result"))
        syn = result["synergy_result"]
        self.assertGreater(syn["total_multi_sensor_flood_sqkm"], 0.0)
        self.assertGreater(syn["cloud_pierced_flood_sqkm"], 0.0)
        self.assertGreater(syn["consensus_confirmed_flood_sqkm"], 0.0)
        
        # Scientific Invariant 1: MECE Inundation Partition Conservation
        self.assertTrue(syn["flood_union_conservation_verified"])
        self.assertAlmostEqual(syn["flood_conservation_residual_sqkm"], 0.0, places=4)
        self.assertAlmostEqual(syn["sum_flood_partitions_sqkm"], syn["total_multi_sensor_flood_sqkm"], places=2)

        # Scientific Invariant 2: Full Domain Spatial Conservation
        self.assertTrue(syn["full_grid_conservation_verified"])
        self.assertAlmostEqual(syn["full_grid_residual_sqkm"], 0.0, places=4)

        # Scientific Invariant 3: Permanent Water Inclusion-Exclusion Conservation
        self.assertTrue(syn["permanent_water_conservation_verified"])
        self.assertAlmostEqual(syn["permanent_water_inclusion_exclusion_residual_sqkm"], 0.0, places=4)
        self.assertEqual(result["permanent_water_sqkm"], syn["domain_permanent_water_sqkm"])
        self.assertEqual(result["combined_permanent_water_sqkm"], syn["combined_permanent_water_union_sqkm"])
        self.assertEqual(result["optical_permanent_water_sqkm"], syn["optical_permanent_water_sqkm"])
        self.assertEqual(result["sar_permanent_water_sqkm"], syn["sar_permanent_water_sqkm"])

        # Scientific Invariant 4: Spatial Resolution Distinction
        self.assertEqual(result["native_spatial_resolution_m"], 10.0)
        self.assertIn("400 x 500 canonical grid", result["effective_grid_resolution_desc"])

        # Test report generation contains Synergy and Inclusion-Exclusion blocks
        run_id = result["run_id"]
        res_report = self.client.get(f"/api/reports/{run_id}")
        self.assertEqual(res_report.status_code, 200)
        self.assertIn("Dual-Sensor Synergy", res_report.text)
        self.assertIn("Consensus Confirmed", res_report.text)
        self.assertIn("Permanent Water Inclusion-Exclusion Conservation", res_report.text)
        self.assertIn("THEOREM VERIFIED", res_report.text)

        # Test job tracking by run_id
        res_job = self.client.get(f"/api/jobs/{run_id}")
        self.assertEqual(res_job.status_code, 200)
        job_data = res_job.json()
        self.assertEqual(job_data["status"], "completed")
        self.assertEqual(job_data["progress_percent"], 100)

    def test_job_tracking_endpoints(self):
        res_active = self.client.get("/api/jobs/active")
        self.assertEqual(res_active.status_code, 200)

        res_404 = self.client.get("/api/jobs/non_existent_job_12345")
        self.assertEqual(res_404.status_code, 404)

if __name__ == '__main__':
    unittest.main()
