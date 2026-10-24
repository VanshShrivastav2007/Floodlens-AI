import unittest
from starlette.testclient import TestClient
from backend.app.main import app

class TestGeographyFoundation(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_list_all_study_areas(self):
        res = self.client.get("/api/study-areas")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertGreaterEqual(len(data), 25)
        ids = [a["id"] for a in data]
        self.assertIn("koshi_basin", ids)
        self.assertIn("nepal_terai", ids)
        self.assertIn("sunsari", ids)
        self.assertIn("banke", ids)
        self.assertIn("kailali", ids)

    def test_filter_study_areas_by_type(self):
        # Basins
        res_basins = self.client.get("/api/study-areas?area_type=basin")
        self.assertEqual(res_basins.status_code, 200)
        basins = res_basins.json()
        self.assertEqual(len(basins), 3)

        # Districts
        res_districts = self.client.get("/api/study-areas?area_type=district")
        self.assertEqual(res_districts.status_code, 200)
        districts = res_districts.json()
        self.assertEqual(len(districts), 21)

        # Region
        res_region = self.client.get("/api/study-areas?area_type=region")
        self.assertEqual(res_region.status_code, 200)
        region = res_region.json()
        self.assertEqual(len(region), 1)
        self.assertEqual(region[0]["id"], "nepal_terai")

    def test_get_individual_study_area(self):
        res = self.client.get("/api/study-areas/sunsari")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["id"], "sunsari")
        self.assertEqual(data["district"], "Sunsari")
        self.assertEqual(data["area_type"], "district")
        self.assertIn("coordinates", data["polygon"])
        self.assertGreater(data["area_sqkm"], 1000.0)

    def test_get_study_area_not_found(self):
        res = self.client.get("/api/study-areas/non_existent_area")
        self.assertEqual(res.status_code, 404)

    def test_settlements_query_by_district(self):
        res = self.client.get("/api/settlements?study_area_id=sunsari&limit=20")
        self.assertEqual(res.status_code, 200)
        settlements = res.json()
        self.assertGreater(len(settlements), 0)
        self.assertLessEqual(len(settlements), 20)
        for s in settlements:
            self.assertEqual(s["district"], "Sunsari")

    def test_settlements_query_by_basin(self):
        res = self.client.get("/api/settlements?study_area_id=koshi_basin")
        self.assertEqual(res.status_code, 200)
        settlements = res.json()
        self.assertGreater(len(settlements), 10)
        names = [s["name"] for s in settlements]
        self.assertIn("Prakashpur", names)
        self.assertIn("Inaruwa", names)

    def test_geography_provenance(self):
        res = self.client.get("/api/geography/provenance")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "OPERATIONAL")
        self.assertEqual(data["total_districts"], 21)
        self.assertGreater(data["total_settlements"], 3000)
        self.assertIn("administrative_manifest", data)
        self.assertIn("settlements_manifest", data)

    def test_geography_coverage(self):
        res = self.client.get("/api/geography/coverage")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["registered_districts_count"], 21)
        self.assertEqual(data["outer_terai_districts_count"], 18)
        self.assertEqual(data["inner_terai_districts_count"], 3)
        self.assertGreater(data["total_district_area_sqkm"], 30000.0)
        self.assertEqual(data["legacy_fixtures_count"], 17)

if __name__ == '__main__':
    unittest.main()
