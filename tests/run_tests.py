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

class TestGeospatialEngine(unittest.TestCase):
    def test_water_indices_math(self):
        green = np.array([[0.15, 0.10], [0.12, 0.08]], dtype=np.float32)
        nir = np.array([[0.02, 0.40], [0.03, 0.35]], dtype=np.float32)

        ndwi = calculate_ndwi(green, nir)
        self.assertGreater(ndwi[0, 0], 0.7)
        self.assertLess(ndwi[0, 1], -0.5)

    def test_zero_division_protection(self):
        green = np.zeros((3, 3), dtype=np.float32)
        nir = np.zeros((3, 3), dtype=np.float32)
        ndwi = calculate_ndwi(green, nir)
        self.assertFalse(np.isnan(ndwi).any())
        self.assertFalse(np.isinf(ndwi).any())

    def test_cloud_masking_scl(self):
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
        self.assertAlmostEqual(ha_k, sqkm_k * 100.0, delta=0.5)
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
        self.assertIn("no verified ground-truth reference flood extent", metrics.notes.lower())

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

    def test_nodata_masking_scl_zero(self):
        from backend.app.geospatial.indices import create_nodata_mask
        scl = np.array([[0, 4], [6, 0]], dtype=np.uint8) # 0 is ESA NO_DATA
        bands = [np.array([[0.0, 0.15], [0.12, 0.0]], dtype=np.float32)]
        nodata = create_nodata_mask(scl, bands)
        self.assertTrue(nodata[0, 0])
        self.assertFalse(nodata[0, 1])
        self.assertFalse(nodata[1, 0])
        self.assertTrue(nodata[1, 1])

    def test_cloud_vs_nodata_separation(self):
        from backend.app.geospatial.indices import create_cloud_mask_scl
        # SCL: 0=NoData, 3=Shadow, 4=Veg, 8=CloudMed, 9=CloudHigh
        scl = np.array([[0, 3], [8, 4]], dtype=np.uint8)
        cloud_pure = create_cloud_mask_scl(scl, include_nodata=False)
        self.assertFalse(cloud_pure[0, 0]) # 0 is NoData, not atmospheric cloud
        self.assertTrue(cloud_pure[0, 1])  # 3 is shadow
        self.assertTrue(cloud_pure[1, 0])  # 8 is cloud
        self.assertFalse(cloud_pure[1, 1]) # 4 is clear veg

    def test_unobserved_pixels_never_treated_as_dry_land(self):
        pre_water = np.array([[0, 0], [0, 0]], dtype=np.uint8)
        post_water = np.array([[0, 1], [0, 0]], dtype=np.uint8)
        pre_cloud = np.array([[False, False], [False, False]], dtype=bool)
        post_cloud = np.array([[True, False], [False, False]], dtype=bool) # (0,0) is cloudy in post
        pre_nodata = np.array([[False, False], [True, False]], dtype=bool) # (1,0) is out of swath

        det = detect_flood_extent(
            pre_water=pre_water,
            post_water=post_water,
            pre_cloud=pre_cloud,
            post_cloud=post_cloud,
            pre_nodata=pre_nodata,
            filter_permanent=True,
            min_mmu_pixels=1
        )

        self.assertFalse(det["valid_mask"][0, 0]) # Unobserved due to cloud
        self.assertFalse(det["valid_mask"][1, 0]) # Unobserved due to nodata
        self.assertTrue(det["valid_mask"][0, 1])  # Clear valid observation
        self.assertTrue(det["newly_inundated"][0, 1])

    def test_geotiff_georeferencing_alignment(self):
        import os, rasterio
        from backend.app.geospatial.raster_processor import export_mask_to_geotiff
        test_path = "outputs/rasters/test_alignment_check.tif"
        data = np.ones((50, 60), dtype=np.uint8)
        bbox = [86.75, 26.35, 87.35, 26.85]
        export_mask_to_geotiff(data, bbox, test_path)

        with rasterio.open(test_path) as src:
            self.assertEqual(src.crs.to_string(), "EPSG:4326")
            self.assertEqual(src.width, 60)
            self.assertEqual(src.height, 50)
            self.assertAlmostEqual(src.bounds.left, 86.75, places=4)
            self.assertAlmostEqual(src.bounds.bottom, 26.35, places=4)
            self.assertAlmostEqual(src.bounds.right, 87.35, places=4)
            self.assertAlmostEqual(src.bounds.top, 26.85, places=4)
        if os.path.exists(test_path):
            os.remove(test_path)

    def test_geodesic_pixel_area_spatial_accounting(self):
        from backend.app.geospatial.raster_processor import (
            calculate_projected_area,
            compute_raster_cell_areas_wgs84
        )
        from pyproj import Geod

        bbox = [86.75, 26.35, 87.35, 26.85]
        rows, cols = 400, 500

        # 1. Independent geodesic bbox area via pyproj.Geod
        geod = Geod(ellps="WGS84")
        lons = [86.75, 87.35, 87.35, 86.75, 86.75]
        lats = [26.35, 26.35, 26.85, 26.85, 26.35]
        expected_geod_sqkm = abs(geod.polygon_area_perimeter(lons, lats)[0]) / 1e6

        # 2. Raster cell geodesic area sum for the full grid
        full_mask = np.ones((rows, cols), dtype=bool)
        calc_sqkm, _, _ = calculate_projected_area(full_mask, bbox, cols, rows)
        self.assertAlmostEqual(calc_sqkm, expected_geod_sqkm, delta=0.5)

        # 3. Spatial partition conservation: cloud + nodata + valid == total
        # Create non-overlapping partition
        nodata = np.zeros((rows, cols), dtype=bool)
        nodata[:, :200] = True # Western 40% is nodata
        cloud = np.zeros((rows, cols), dtype=bool)
        cloud[:150, 200:] = True # Upper-right is cloud
        valid = (~nodata) & (~cloud)

        nodata_sqkm, _, _ = calculate_projected_area(nodata, bbox, cols, rows)
        cloud_sqkm, _, _ = calculate_projected_area(cloud, bbox, cols, rows)
        valid_sqkm, _, _ = calculate_projected_area(valid, bbox, cols, rows)

        sum_parts = nodata_sqkm + cloud_sqkm + valid_sqkm
        self.assertAlmostEqual(sum_parts, calc_sqkm, places=2)

    def test_raster_area_vs_projected_utm(self):
        from backend.app.geospatial.raster_processor import calculate_projected_area
        from shapely.geometry import Polygon
        from shapely.ops import transform as shapely_transform
        from pyproj import Transformer

        bbox = [86.75, 26.35, 87.35, 26.85]
        rows, cols = 400, 500

        # Geodesic raster area
        full_mask = np.ones((rows, cols), dtype=bool)
        geod_sqkm, _, crs = calculate_projected_area(full_mask, bbox, cols, rows)

        # Independent projected UTM polygon area
        poly_wgs = Polygon([(86.75, 26.35), (87.35, 26.35), (87.35, 26.85), (86.75, 26.85)])
        to_utm = Transformer.from_crs("EPSG:4326", crs, always_xy=True)
        poly_utm = shapely_transform(to_utm.transform, poly_wgs)
        utm_poly_sqkm = poly_utm.area / 1e6

        # Agreement between geodesic raster integration and UTM projected area is within 0.1%
        diff_pct = abs(geod_sqkm - utm_poly_sqkm) / utm_poly_sqkm * 100.0
        self.assertLess(diff_pct, 0.15)

    def test_flood_area_reproducibility(self):
        # Verify 100% deterministic reproducibility of detection on repeated runs
        np.random.seed(42)
        pre_water = (np.random.rand(100, 100) > 0.85).astype(np.uint8)
        post_water = (np.random.rand(100, 100) > 0.80).astype(np.uint8)
        pre_cloud = np.random.rand(100, 100) > 0.90
        post_cloud = np.random.rand(100, 100) > 0.85
        pre_nodata = np.random.rand(100, 100) > 0.95
        post_nodata = np.random.rand(100, 100) > 0.95

        runs = []
        for _ in range(3):
            det = detect_flood_extent(
                pre_water, post_water,
                pre_cloud, post_cloud,
                pre_nodata, post_nodata,
                filter_permanent=True, min_mmu_pixels=3
            )
            runs.append((det["filtered_inundated_pixel_count"], det["valid_pixel_count"]))

        # All runs must produce identical pixel counts
        self.assertEqual(runs[0], runs[1])
        self.assertEqual(runs[1], runs[2])

    def test_known_binary_mask_flood_area(self):
        from backend.app.geospatial.raster_processor import (
            calculate_projected_area,
            compute_raster_cell_areas_wgs84
        )
        bbox = [86.75, 26.35, 87.35, 26.85]
        rows, cols = 400, 500

        # Create known 50x40 block mask (2,000 pixels) between rows 100 to 140
        mask = np.zeros((rows, cols), dtype=np.uint8)
        mask[100:140, 200:250] = 1 # 40 rows x 50 cols = 2000 pixels

        # Calculate via calculate_projected_area
        sqkm, ha, crs = calculate_projected_area(mask, bbox, cols, rows)

        # Independently calculate via direct row-wise summation
        row_areas = compute_raster_cell_areas_wgs84(bbox, cols, rows)
        expected_sqkm = np.sum(row_areas[100:140] * 50) / 1e6

        self.assertAlmostEqual(sqkm, round(expected_sqkm, 3), places=3)
        self.assertAlmostEqual(ha, round(expected_sqkm * 100.0, 1), places=1)

    def test_raster_to_vector_geojson_consistency(self):
        from backend.app.geospatial.raster_processor import vectorize_flood_extent
        import os

        bbox = [86.75, 26.35, 87.35, 26.85]
        rows, cols = 400, 500
        mask = np.zeros((rows, cols), dtype=np.uint8)
        mask[50:100, 50:100] = 1 # 50x50 block

        out_geojson = "outputs/vectors/test_vector_consistency.geojson"
        geojson = vectorize_flood_extent(mask, bbox, output_geojson_path=out_geojson, simplify_tolerance=0.0)

        self.assertEqual(geojson["type"], "FeatureCollection")
        self.assertGreater(len(geojson["features"]), 0)
        feat = geojson["features"][0]
        self.assertEqual(feat["geometry"]["type"], "Polygon")
        coords = np.array(feat["geometry"]["coordinates"][0])

        # Polygon coordinates must lie strictly within the bounding box
        self.assertGreaterEqual(np.min(coords[:, 0]), bbox[0])
        self.assertLessEqual(np.max(coords[:, 0]), bbox[2])
        self.assertGreaterEqual(np.min(coords[:, 1]), bbox[1])
        self.assertLessEqual(np.max(coords[:, 1]), bbox[3])

        if os.path.exists(out_geojson):
            os.remove(out_geojson)

    def test_scl_class_1_defective_is_nodata_not_cloud(self):
        from backend.app.geospatial.indices import (
            create_nodata_mask,
            create_cloud_mask_scl,
            detect_flood_extent
        )
        # SCL: 0=NoData, 1=Saturated/Defective, 3=Shadow, 8=CloudMed, 4=Veg
        scl = np.array([[1, 3], [8, 4]], dtype=np.uint8)

        # 1. Defective/saturated (class 1) must be flagged as nodata
        nodata = create_nodata_mask(scl)
        self.assertTrue(nodata[0, 0])
        self.assertFalse(nodata[0, 1])
        self.assertFalse(nodata[1, 0])
        self.assertFalse(nodata[1, 1])

        # 2. Atmospheric cloud mask must NOT count class 1 as cloud
        cloud = create_cloud_mask_scl(scl, include_nodata=False)
        self.assertFalse(cloud[0, 0]) # Defective pixel is NOT atmospheric cloud
        self.assertTrue(cloud[0, 1])  # Class 3 (shadow) IS atmospheric
        self.assertTrue(cloud[1, 0])  # Class 8 (cloud) IS atmospheric
        self.assertFalse(cloud[1, 1]) # Class 4 (veg) is clear

        # 3. Detect flood extent: class 1 pixel must be invalid and never classified as dry land or flood
        pre_water = np.array([[0, 0], [0, 0]], dtype=np.uint8)
        post_water = np.array([[1, 0], [0, 0]], dtype=np.uint8) # Water detected on defective pixel
        det = detect_flood_extent(
            pre_water, post_water,
            pre_cloud=cloud, post_cloud=cloud,
            pre_nodata=nodata, post_nodata=nodata,
            filter_permanent=True, min_mmu_pixels=1
        )
        self.assertFalse(det["valid_mask"][0, 0])
        self.assertFalse(det["newly_inundated"][0, 0]) # Suppressed because pixel is invalid/defective

    def test_mosaic_adjacent_tiles_zero_nodata(self):
        from backend.app.services.satellite_service import SatelliteService
        from backend.app.schemas.models import SatelliteSceneMetadata
        from backend.app.geospatial.indices import create_nodata_mask

        service = SatelliteService()
        rows, cols = 400, 500

        # Create tile 1 (West - 45RVK): valid on left half (cols 0..250), NoData on right half
        b_tile1 = {
            "B03": np.zeros((rows, cols), dtype=np.float32),
            "B08": np.zeros((rows, cols), dtype=np.float32),
            "B11": np.zeros((rows, cols), dtype=np.float32),
            "SCL": np.zeros((rows, cols), dtype=np.uint8) # Default 0 = NoData
        }
        b_tile1["B03"][:, :250] = 0.15
        b_tile1["B08"][:, :250] = 0.05
        b_tile1["B11"][:, :250] = 0.02
        b_tile1["SCL"][:, :250] = 4 # Class 4 = Vegetation (Valid)

        s1 = SatelliteSceneMetadata(
            scene_id="S2B_45RVK_20240923_0_L2A",
            acquisition_date="2024-09-23",
            cloud_cover_percent=5.0,
            platform="Sentinel-2B",
            instrument="MSI",
            spatial_resolution_m=10.0,
            bounding_box=[86.75, 26.35, 87.35, 26.85],
            bands=["B03", "B08", "B11", "SCL"],
            asset_urls={"B03": "mock", "B08": "mock", "B11": "mock", "SCL": "mock"}
        )

        # Create tile 2 (East - 45RWK): NoData on left half, valid on right half (cols 250..500)
        b_tile2 = {
            "B03": np.zeros((rows, cols), dtype=np.float32),
            "B08": np.zeros((rows, cols), dtype=np.float32),
            "B11": np.zeros((rows, cols), dtype=np.float32),
            "SCL": np.zeros((rows, cols), dtype=np.uint8) # Default 0 = NoData
        }
        b_tile2["B03"][:, 250:] = 0.12
        b_tile2["B08"][:, 250:] = 0.04
        b_tile2["B11"][:, 250:] = 0.03
        b_tile2["SCL"][:, 250:] = 4 # Class 4 = Vegetation (Valid)

        s2 = SatelliteSceneMetadata(
            scene_id="S2B_45RWK_20240923_0_L2A",
            acquisition_date="2024-09-23",
            cloud_cover_percent=6.0,
            platform="Sentinel-2B",
            instrument="MSI",
            spatial_resolution_m=10.0,
            bounding_box=[86.75, 26.35, 87.35, 26.85],
            bands=["B03", "B08", "B11", "SCL"],
            asset_urls={"B03": "mock", "B08": "mock", "B11": "mock", "SCL": "mock"}
        )

        mosaic_bands, meta = service.mosaic_tile_bands([(s1, b_tile1), (s2, b_tile2)], grid_shape=(rows, cols))

        # Check provenance metadata
        self.assertTrue(meta["is_mosaic"])
        self.assertTrue(meta["is_single_pass"])
        self.assertIn("45RVK", meta["tiles_mosaicked"])
        self.assertIn("45RWK", meta["tiles_mosaicked"])
        self.assertIsNone(meta["date_difference_warning"])

        # Check that mosaicing eliminates NoData: entire 400x500 domain has valid data!
        nodata_mask = create_nodata_mask(mosaic_bands["SCL"], [mosaic_bands["B03"], mosaic_bands["B08"], mosaic_bands["B11"]])
        self.assertEqual(np.sum(nodata_mask), 0)
        self.assertEqual(mosaic_bands["SCL"][100, 100], 4)
        self.assertEqual(mosaic_bands["SCL"][100, 350], 4)

    def test_mosaic_precedence_valid_over_cloud_and_nodata(self):
        from backend.app.services.satellite_service import SatelliteService
        from backend.app.schemas.models import SatelliteSceneMetadata

        service = SatelliteService()
        rows, cols = 10, 10

        # Pixel (0, 0): Tile 1 has cloud (SCL=8), Tile 2 has clear vegetation (SCL=4) -> Mosaic must choose clear (SCL=4)
        # Pixel (0, 1): Tile 1 has cloud (SCL=8), Tile 2 has NoData (SCL=0) -> Mosaic must choose cloud (SCL=8)
        # Pixel (0, 2): Tile 1 has NoData (SCL=0), Tile 2 has NoData (SCL=0) -> Mosaic remains NoData (SCL=0)
        b1 = {
            "B03": np.ones((rows, cols), dtype=np.float32) * 0.1,
            "B08": np.ones((rows, cols), dtype=np.float32) * 0.1,
            "B11": np.ones((rows, cols), dtype=np.float32) * 0.1,
            "SCL": np.zeros((rows, cols), dtype=np.uint8)
        }
        b1["SCL"][0, 0] = 8 # Cloud
        b1["SCL"][0, 1] = 8 # Cloud
        b1["SCL"][0, 2] = 0 # NoData

        b2 = {
            "B03": np.ones((rows, cols), dtype=np.float32) * 0.1,
            "B08": np.ones((rows, cols), dtype=np.float32) * 0.1,
            "B11": np.ones((rows, cols), dtype=np.float32) * 0.1,
            "SCL": np.zeros((rows, cols), dtype=np.uint8)
        }
        b2["SCL"][0, 0] = 4 # Clear vegetation
        b2["SCL"][0, 1] = 0 # NoData
        b2["SCL"][0, 2] = 0 # NoData

        s1 = SatelliteSceneMetadata(
            scene_id="S2B_45RVK_20240923_0_L2A",
            acquisition_date="2024-09-23",
            cloud_cover_percent=20.0,
            platform="Sentinel-2B",
            instrument="MSI",
            spatial_resolution_m=10.0,
            bounding_box=[86.75, 26.35, 87.35, 26.85],
            bands=["B03", "B08", "B11", "SCL"]
        )
        s2 = SatelliteSceneMetadata(
            scene_id="S2B_45RWK_20240923_0_L2A",
            acquisition_date="2024-09-23",
            cloud_cover_percent=10.0,
            platform="Sentinel-2B",
            instrument="MSI",
            spatial_resolution_m=10.0,
            bounding_box=[86.75, 26.35, 87.35, 26.85],
            bands=["B03", "B08", "B11", "SCL"]
        )

        mosaic_bands, meta = service.mosaic_tile_bands([(s1, b1), (s2, b2)], grid_shape=(rows, cols))

        # Clear vegetation is selected over cloud
        self.assertEqual(mosaic_bands["SCL"][0, 0], 4)
        # Cloud is selected over NoData (preserving atmospheric accounting)
        self.assertEqual(mosaic_bands["SCL"][0, 1], 8)
        # Unobserved pixel across both tiles remains NoData
        self.assertEqual(mosaic_bands["SCL"][0, 2], 0)

    def test_mosaic_multi_date_warning(self):
        from backend.app.services.satellite_service import SatelliteService
        from backend.app.schemas.models import SatelliteSceneMetadata

        service = SatelliteService()
        rows, cols = 10, 10
        b1 = {b: np.ones((rows, cols), dtype=np.uint8 if b == "SCL" else np.float32) for b in ["B03", "B08", "B11", "SCL"]}
        b2 = {b: np.ones((rows, cols), dtype=np.uint8 if b == "SCL" else np.float32) for b in ["B03", "B08", "B11", "SCL"]}

        s1 = SatelliteSceneMetadata(
            scene_id="S2B_45RVK_20240920_0_L2A",
            acquisition_date="2024-09-20", # 3 days earlier
            cloud_cover_percent=15.0,
            platform="Sentinel-2B",
            instrument="MSI",
            spatial_resolution_m=10.0,
            bounding_box=[86.75, 26.35, 87.35, 26.85],
            bands=["B03", "B08", "B11", "SCL"]
        )
        s2 = SatelliteSceneMetadata(
            scene_id="S2B_45RWK_20240923_0_L2A",
            acquisition_date="2024-09-23",
            cloud_cover_percent=5.0,
            platform="Sentinel-2B",
            instrument="MSI",
            spatial_resolution_m=10.0,
            bounding_box=[86.75, 26.35, 87.35, 26.85],
            bands=["B03", "B08", "B11", "SCL"]
        )

        mosaic_bands, meta = service.mosaic_tile_bands([(s1, b1), (s2, b2)], grid_shape=(rows, cols))
        self.assertFalse(meta["is_single_pass"])
        self.assertIsNotNone(meta["date_difference_warning"])
        self.assertIn("2024-09-20", meta["date_difference_warning"])
    def test_sar_db_conversion_and_speckle_suppression(self):
        from backend.app.services.sar_service import SARService
        sar = SARService()
        rows, cols = 20, 20

        # Linear power array with known values and an isolated high-value speckle spike
        linear = np.ones((rows, cols), dtype=np.float32) * 0.1 # -10.0 dB
        linear[10, 10] = 5.0 # Isolated speckle spike
        linear[0, 0] = np.nan # NoData pixel

        db, valid = sar.preprocess_sar(linear, speckle_filter_size=3)

        # NaN handling
        self.assertFalse(valid[0, 0])
        self.assertTrue(np.isnan(db[0, 0]))

        # Median filter suppresses single-pixel speckle spike
        self.assertAlmostEqual(float(db[10, 10]), -10.0, places=1)

        # Standard linear power 0.1 corresponds to -10.0 dB
        self.assertAlmostEqual(float(db[5, 5]), -10.0, places=2)

    def test_sar_flood_change_detection_logic(self):
        from backend.app.services.sar_service import SARService
        sar = SARService()
        rows, cols = 10, 10

        # Pre-event: normal dry agricultural land (-10.0 dB)
        pre_db = np.ones((rows, cols), dtype=np.float32) * -10.0
        # Post-event: dry land (-10.0 dB)
        post_db = np.ones((rows, cols), dtype=np.float32) * -10.0
        pre_valid = np.ones((rows, cols), dtype=bool)
        post_valid = np.ones((rows, cols), dtype=bool)

        # Pixel (1, 1): Permanent baseline water (-18.0 dB in both pre and post)
        pre_db[1, 1] = -18.0
        post_db[1, 1] = -18.0

        # Region (4:7, 4:7): Newly inundated flood (pre -10 dB -> post -19 dB, drop = -9 dB, 9 pixels >= MMU 5)
        pre_db[4:7, 4:7] = -10.0
        post_db[4:7, 4:7] = -19.0

        # Pixel (8, 8): Isolated flooded pixel (1 pixel < MMU 5, should be filtered)
        pre_db[8, 8] = -10.0
        post_db[8, 8] = -19.0

        res = sar.detect_sar_flood(
            pre_db=pre_db,
            post_db=post_db,
            pre_valid=pre_valid,
            post_valid=post_valid,
            threshold_db=-15.5,
            change_threshold_db=-2.5,
            min_mmu_pixels=5
        )

        inundated = res["sar_newly_inundated"]
        pre_water = res["sar_pre_water"]

        # Permanent water identified and excluded from newly inundated
        self.assertTrue(pre_water[1, 1])
        self.assertFalse(inundated[1, 1])

        # Newly inundated 3x3 block detected
        self.assertTrue(np.all(inundated[4:7, 4:7]))

        # Isolated 1-pixel flood filtered out by MMU (threshold >= 5)
        self.assertFalse(inundated[8, 8])

    def test_dual_sensor_synergy_accounting(self):
        from backend.app.services.sar_service import SARService
        sar = SARService()
        rows, cols = 20, 20
        cell_areas = np.ones((rows, cols), dtype=np.float64) * 10000.0 # 0.01 sq km per pixel

        optical_flood = np.zeros((rows, cols), dtype=bool)
        optical_valid = np.ones((rows, cols), dtype=bool)
        optical_cloud = np.zeros((rows, cols), dtype=bool)
        optical_nodata = np.zeros((rows, cols), dtype=bool)

        sar_flood = np.zeros((rows, cols), dtype=bool)
        sar_valid = np.ones((rows, cols), dtype=bool)

        # Region P1: Consensus confirmed flood (both detect)
        optical_flood[2:5, 2:5] = True # 9 pixels
        sar_flood[2:5, 2:5] = True

        # Region P2: Cloud-pierced SAR flood (optical obscured by clouds, SAR detects flood)
        optical_cloud[10:14, 10:14] = True # 16 pixels cloud
        optical_valid[10:14, 10:14] = False
        sar_flood[10:14, 10:14] = True

        # Region P5: Optical flood outside SAR swath (SAR outside swath, optical detects clear sky flood)
        optical_flood[16:18, 16:18] = True # 4 pixels
        sar_valid[16:18, 16:18] = False

        # Region P6: Optical flood where SAR observed valid dry land (discordant optical)
        optical_flood[0:2, 0:2] = True # 4 pixels
        sar_flood[0:2, 0:2] = False
        sar_valid[0:2, 0:2] = True

        # Region P4: SAR flood where Optical observed valid dry land (discordant SAR)
        sar_flood[6:8, 6:8] = True # 4 pixels
        optical_flood[6:8, 6:8] = False
        optical_valid[6:8, 6:8] = True

        syn = sar.compute_sensor_synergy(
            optical_flood=optical_flood,
            optical_valid=optical_valid,
            optical_cloud=optical_cloud,
            sar_flood=sar_flood,
            sar_valid=sar_valid,
            cell_areas_2d=cell_areas,
            optical_nodata=optical_nodata
        )

        # Consensus (P1): 9 pixels * 0.01 = 0.09 sq km
        self.assertAlmostEqual(syn.consensus_confirmed_flood_sqkm, 0.09, places=2)
        # Cloud-pierced SAR (P2): 16 pixels * 0.01 = 0.16 sq km
        self.assertAlmostEqual(syn.cloud_pierced_sar_flood_sqkm, 0.16, places=2)
        # Optical outside SAR swath (P5): 4 pixels * 0.01 = 0.04 sq km
        self.assertAlmostEqual(syn.optical_outside_sar_swath_sqkm, 0.04, places=2)
        # Optical discordant (P6): 4 pixels * 0.01 = 0.04 sq km
        self.assertAlmostEqual(syn.optical_discordant_flood_sqkm, 0.04, places=2)
        # SAR discordant (P4): 4 pixels * 0.01 = 0.04 sq km
        self.assertAlmostEqual(syn.sar_discordant_flood_sqkm, 0.04, places=2)

        # Total union: (9 + 16 + 4 + 4 + 4) * 0.01 = 0.37 sq km
        self.assertAlmostEqual(syn.total_multi_sensor_flood_sqkm, 0.37, places=2)
        # MECE Partition Conservation Law 1: Sum of partitions must strictly equal Total Union
        self.assertTrue(syn.flood_union_conservation_verified)
        self.assertAlmostEqual(syn.flood_conservation_residual_sqkm, 0.0, places=5)
        self.assertAlmostEqual(syn.sum_flood_partitions_sqkm, syn.total_multi_sensor_flood_sqkm, places=5)

        # MECE Domain Spatial Conservation Law 2: Full Grid Conservation
        self.assertTrue(syn.full_grid_conservation_verified)
        self.assertAlmostEqual(syn.full_grid_residual_sqkm, 0.0, places=5)

    def test_real_koshi_mece_decomposition_conservation(self):
        """
        Tests the actual cached Koshi Basin Sentinel-1 RTC and Sentinel-2 mosaic arrays
        and mathematically verifies the 6 MECE partitions sum identically to the total union.
        """
        import os
        from backend.app.services.sar_service import SARService
        from backend.app.geospatial.raster_processor import compute_raster_cell_areas_wgs84
        from backend.app.geospatial.indices import detect_flood_extent, calculate_mndwi, create_cloud_mask_scl, create_nodata_mask
        from backend.app.services.satellite_service import SatelliteService
        from backend.app.schemas.models import SatelliteSceneMetadata

        pre_s2_path = 'data/cache/stac/S2B_45RVK_20240923_0_L2A_B03_400x500.npy'
        if not os.path.exists(pre_s2_path):
            self.skipTest("Cached satellite assets not found for offline integration test.")

        bbox = [86.75, 26.35, 87.35, 26.85]
        rows, cols = 400, 500
        row_areas = compute_raster_cell_areas_wgs84(bbox, cols, rows)
        cell_areas_2d = np.tile(row_areas[:, np.newaxis], (1, cols))

        pre_rvk_b03 = np.load('data/cache/stac/S2B_45RVK_20240923_0_L2A_B03_400x500.npy')
        pre_rvk_b08 = np.load('data/cache/stac/S2B_45RVK_20240923_0_L2A_B08_400x500.npy')
        pre_rvk_b11 = np.load('data/cache/stac/S2B_45RVK_20240923_0_L2A_B11_400x500.npy')
        pre_rvk_scl = np.load('data/cache/stac/S2B_45RVK_20240923_0_L2A_SCL_400x500.npy')
        pre_rwk_b03 = np.load('data/cache/stac/S2B_45RWK_20240923_0_L2A_B03_400x500.npy')
        pre_rwk_b08 = np.load('data/cache/stac/S2B_45RWK_20240923_0_L2A_B08_400x500.npy')
        pre_rwk_b11 = np.load('data/cache/stac/S2B_45RWK_20240923_0_L2A_B11_400x500.npy')
        pre_rwk_scl = np.load('data/cache/stac/S2B_45RWK_20240923_0_L2A_SCL_400x500.npy')

        post_rvk_b03 = np.load('data/cache/stac/S2B_45RVK_20241013_0_L2A_B03_400x500.npy')
        post_rvk_b08 = np.load('data/cache/stac/S2B_45RVK_20241013_0_L2A_B08_400x500.npy')
        post_rvk_b11 = np.load('data/cache/stac/S2B_45RVK_20241013_0_L2A_B11_400x500.npy')
        post_rvk_scl = np.load('data/cache/stac/S2B_45RVK_20241013_0_L2A_SCL_400x500.npy')
        post_rwk_b03 = np.load('data/cache/stac/S2B_45RWK_20241013_1_L2A_B03_400x500.npy')
        post_rwk_b08 = np.load('data/cache/stac/S2B_45RWK_20241013_1_L2A_B08_400x500.npy')
        post_rwk_b11 = np.load('data/cache/stac/S2B_45RWK_20241013_1_L2A_B11_400x500.npy')
        post_rwk_scl = np.load('data/cache/stac/S2B_45RWK_20241013_1_L2A_SCL_400x500.npy')

        sat = SatelliteService()
        s_rvk = SatelliteSceneMetadata(scene_id="RVK", acquisition_date="2024-09-23", cloud_cover_percent=0.0, bounding_box=bbox, bands=[])
        s_rwk = SatelliteSceneMetadata(scene_id="RWK", acquisition_date="2024-09-23", cloud_cover_percent=0.0, bounding_box=bbox, bands=[])

        pre_mosaic, _ = sat.mosaic_tile_bands([(s_rvk, {"B03": pre_rvk_b03, "B08": pre_rvk_b08, "B11": pre_rvk_b11, "SCL": pre_rvk_scl}), (s_rwk, {"B03": pre_rwk_b03, "B08": pre_rwk_b08, "B11": pre_rwk_b11, "SCL": pre_rwk_scl})], (rows, cols))
        post_mosaic, _ = sat.mosaic_tile_bands([(s_rvk, {"B03": post_rvk_b03, "B08": post_rvk_b08, "B11": post_rvk_b11, "SCL": post_rvk_scl}), (s_rwk, {"B03": post_rwk_b03, "B08": post_rwk_b08, "B11": post_rwk_b11, "SCL": post_rwk_scl})], (rows, cols))

        pre_water = calculate_mndwi(pre_mosaic["B03"], pre_mosaic["B11"]) > 0.05
        post_water = calculate_mndwi(post_mosaic["B03"], post_mosaic["B11"]) > 0.05
        pre_cloud = create_cloud_mask_scl(pre_mosaic["SCL"], include_nodata=False)
        post_cloud = create_cloud_mask_scl(post_mosaic["SCL"], include_nodata=False)
        pre_nodata = create_nodata_mask(pre_mosaic["SCL"], [pre_mosaic["B03"], pre_mosaic["B08"], pre_mosaic["B11"]])
        post_nodata = create_nodata_mask(post_mosaic["SCL"], [post_mosaic["B03"], post_mosaic["B08"], post_mosaic["B11"]])

        opt_det = detect_flood_extent(pre_water, post_water, pre_cloud, post_cloud, pre_nodata, post_nodata, filter_permanent=True, min_mmu_pixels=5)

        sar = SARService()
        pre24 = np.load('data/cache/stac/S1A_IW_GRDH_1SDV_20240924T122211_20240924T122236_055807_06D1A1_rtc_VV_400x500.npy')
        post06 = np.load('data/cache/stac/S1A_IW_GRDH_1SDV_20241006T122212_20241006T122237_055982_06D887_rtc_VV_400x500.npy')
        pre_db, pre_v = sar.preprocess_sar(pre24)
        post_db, post_v = sar.preprocess_sar(post06)
        sar_det = sar.detect_sar_flood(pre_db, post_db, pre_v, post_v, threshold_db=-15.5, change_threshold_db=-2.5, min_mmu_pixels=5)

        syn = sar.compute_sensor_synergy(
            optical_flood=opt_det["newly_inundated"],
            optical_valid=opt_det["valid_mask"],
            optical_cloud=opt_det["cloud_mask"],
            sar_flood=sar_det["sar_newly_inundated"],
            sar_valid=sar_det["both_valid"],
            cell_areas_2d=cell_areas_2d,
            optical_nodata=opt_det["nodata_mask"],
            optical_perm_water=opt_det["pre_water_mask"],
            sar_perm_water=sar_det["sar_pre_water"]
        )

        self.assertTrue(syn.flood_union_conservation_verified)
        self.assertAlmostEqual(syn.flood_conservation_residual_sqkm, 0.0, places=5)
        self.assertAlmostEqual(syn.sum_flood_partitions_sqkm, syn.total_multi_sensor_flood_sqkm, places=2)
        self.assertTrue(syn.full_grid_conservation_verified)
        self.assertAlmostEqual(syn.full_grid_residual_sqkm, 0.0, places=4)
        self.assertTrue(syn.permanent_water_conservation_verified)
        self.assertAlmostEqual(syn.permanent_water_inclusion_exclusion_residual_sqkm, 0.0, places=5)
        self.assertLessEqual(syn.combined_permanent_water_union_sqkm, syn.optical_permanent_water_sqkm + syn.sar_permanent_water_sqkm)
        self.assertGreater(syn.optical_permanent_water_sqkm, 0.0)
        self.assertGreater(syn.sar_permanent_water_sqkm, 0.0)
        self.assertLessEqual(syn.domain_permanent_water_sqkm, syn.combined_permanent_water_union_sqkm)

    def test_permanent_water_inclusion_exclusion_rigorous(self):
        from backend.app.services.sar_service import SARService
        from backend.app.geospatial.raster_processor import compute_raster_cell_areas_wgs84
        bbox = [86.75, 26.35, 87.35, 26.85]
        rows, cols = 400, 500
        row_areas = compute_raster_cell_areas_wgs84(bbox, cols, rows)
        cell_areas_2d = np.tile(row_areas[:, np.newaxis], (1, cols))

        # Synthetic masks:
        # Optical water: rows 0..100, cols 0..200
        opt_perm = np.zeros((rows, cols), dtype=bool)
        opt_perm[0:100, 0:200] = True # 20,000 cells

        # SAR water: rows 50..150, cols 100..300
        sar_perm = np.zeros((rows, cols), dtype=bool)
        sar_perm[50:150, 100:300] = True # 20,000 cells

        # Flood: rows 200..250, cols 0..100 plus small overlap with optical water: rows 80..90, cols 0..50
        opt_flood = np.zeros((rows, cols), dtype=bool)
        opt_flood[80:90, 0:50] = True
        sar_flood = np.zeros((rows, cols), dtype=bool)
        sar_flood[200:250, 0:100] = True

        sar = SARService()
        syn = sar.compute_sensor_synergy(
            optical_flood=opt_flood,
            optical_valid=np.ones((rows, cols), dtype=bool),
            optical_cloud=np.zeros((rows, cols), dtype=bool),
            sar_flood=sar_flood,
            sar_valid=np.ones((rows, cols), dtype=bool),
            cell_areas_2d=cell_areas_2d,
            optical_nodata=np.zeros((rows, cols), dtype=bool),
            optical_perm_water=opt_perm,
            sar_perm_water=sar_perm
        )

        self.assertTrue(syn.permanent_water_conservation_verified)
        self.assertAlmostEqual(syn.permanent_water_inclusion_exclusion_residual_sqkm, 0.0, places=5)
        self.assertLess(syn.combined_permanent_water_union_sqkm, syn.optical_permanent_water_sqkm + syn.sar_permanent_water_sqkm)
        perm_union = opt_perm | sar_perm
        total_flood = opt_flood | sar_flood
        perm_non_flood = perm_union & (~total_flood)
        self.assertEqual(np.sum(perm_non_flood & total_flood), 0)
        self.assertTrue(syn.full_grid_conservation_verified)

if __name__ == '__main__':
    unittest.main()
