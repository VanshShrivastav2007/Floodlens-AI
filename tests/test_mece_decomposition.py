import numpy as np
from backend.app.services.sar_service import SARService
from backend.app.geospatial.raster_processor import compute_raster_cell_areas_wgs84
from backend.app.geospatial.indices import detect_flood_extent, calculate_mndwi, create_cloud_mask_scl, create_nodata_mask
from backend.app.services.satellite_service import SatelliteService
from backend.app.schemas.models import SatelliteSceneMetadata

bbox = [86.75, 26.35, 87.35, 26.85]
rows, cols = 400, 500
row_areas = compute_raster_cell_areas_wgs84(bbox, cols, rows)
cell_areas_2d = np.tile(row_areas[:, np.newaxis], (1, cols))
total_domain_sqkm = np.sum(cell_areas_2d) / 1e6

# Load optical mosaic bands
# Pre-flood mosaic: 45RVK (West) + 45RWK (East) for 2024-09-23
pre_rvk_b03 = np.load('data/cache/stac/S2B_45RVK_20240923_0_L2A_B03_400x500.npy')
pre_rvk_b08 = np.load('data/cache/stac/S2B_45RVK_20240923_0_L2A_B08_400x500.npy')
pre_rvk_b11 = np.load('data/cache/stac/S2B_45RVK_20240923_0_L2A_B11_400x500.npy')
pre_rvk_scl = np.load('data/cache/stac/S2B_45RVK_20240923_0_L2A_SCL_400x500.npy')

pre_rwk_b03 = np.load('data/cache/stac/S2B_45RWK_20240923_0_L2A_B03_400x500.npy')
pre_rwk_b08 = np.load('data/cache/stac/S2B_45RWK_20240923_0_L2A_B08_400x500.npy')
pre_rwk_b11 = np.load('data/cache/stac/S2B_45RWK_20240923_0_L2A_B11_400x500.npy')
pre_rwk_scl = np.load('data/cache/stac/S2B_45RWK_20240923_0_L2A_SCL_400x500.npy')

# Post-flood mosaic: 45RVK + 45RWK for 2024-10-13
post_rvk_b03 = np.load('data/cache/stac/S2B_45RVK_20241013_0_L2A_B03_400x500.npy')
post_rvk_b08 = np.load('data/cache/stac/S2B_45RVK_20241013_0_L2A_B08_400x500.npy')
post_rvk_b11 = np.load('data/cache/stac/S2B_45RVK_20241013_0_L2A_B11_400x500.npy')
post_rvk_scl = np.load('data/cache/stac/S2B_45RVK_20241013_0_L2A_SCL_400x500.npy')

post_rwk_b03 = np.load('data/cache/stac/S2B_45RWK_20241013_1_L2A_B03_400x500.npy')
post_rwk_b08 = np.load('data/cache/stac/S2B_45RWK_20241013_1_L2A_B08_400x500.npy')
post_rwk_b11 = np.load('data/cache/stac/S2B_45RWK_20241013_1_L2A_B11_400x500.npy')
post_rwk_scl = np.load('data/cache/stac/S2B_45RWK_20241013_1_L2A_SCL_400x500.npy')

sat_service = SatelliteService()
s_rvk_pre = SatelliteSceneMetadata(scene_id="S2B_45RVK_20240923_0_L2A", acquisition_date="2024-09-23", cloud_cover_percent=0.0, bounding_box=bbox, bands=[])
s_rwk_pre = SatelliteSceneMetadata(scene_id="S2B_45RWK_20240923_0_L2A", acquisition_date="2024-09-23", cloud_cover_percent=0.0, bounding_box=bbox, bands=[])
pre_mosaic, _ = sat_service.mosaic_tile_bands([
    (s_rvk_pre, {"B03": pre_rvk_b03, "B08": pre_rvk_b08, "B11": pre_rvk_b11, "SCL": pre_rvk_scl}),
    (s_rwk_pre, {"B03": pre_rwk_b03, "B08": pre_rwk_b08, "B11": pre_rwk_b11, "SCL": pre_rwk_scl})
], grid_shape=(rows, cols))

s_rvk_post = SatelliteSceneMetadata(scene_id="S2B_45RVK_20241013_0_L2A", acquisition_date="2024-10-13", cloud_cover_percent=0.0, bounding_box=bbox, bands=[])
s_rwk_post = SatelliteSceneMetadata(scene_id="S2B_45RWK_20241013_1_L2A", acquisition_date="2024-10-13", cloud_cover_percent=0.0, bounding_box=bbox, bands=[])
post_mosaic, _ = sat_service.mosaic_tile_bands([
    (s_rvk_post, {"B03": post_rvk_b03, "B08": post_rvk_b08, "B11": post_rvk_b11, "SCL": post_rvk_scl}),
    (s_rwk_post, {"B03": post_rwk_b03, "B08": post_rwk_b08, "B11": post_rwk_b11, "SCL": post_rwk_scl})
], grid_shape=(rows, cols))

# Compute optical flood
pre_mndwi = calculate_mndwi(pre_mosaic["B03"], pre_mosaic["B11"])
post_mndwi = calculate_mndwi(post_mosaic["B03"], post_mosaic["B11"])
pre_water = pre_mndwi > 0.05
post_water = post_mndwi > 0.05
pre_cloud = create_cloud_mask_scl(pre_mosaic["SCL"], include_nodata=False)
post_cloud = create_cloud_mask_scl(post_mosaic["SCL"], include_nodata=False)
pre_nodata = create_nodata_mask(pre_mosaic["SCL"], [pre_mosaic["B03"], pre_mosaic["B08"], pre_mosaic["B11"]])
post_nodata = create_nodata_mask(post_mosaic["SCL"], [post_mosaic["B03"], post_mosaic["B08"], post_mosaic["B11"]])

opt_det = detect_flood_extent(
    pre_water=pre_water,
    post_water=post_water,
    pre_cloud=pre_cloud,
    post_cloud=post_cloud,
    pre_nodata=pre_nodata,
    post_nodata=post_nodata,
    filter_permanent=True,
    min_mmu_pixels=5
)

opt_flood = opt_det["newly_inundated"]
opt_valid = opt_det["valid_mask"]
opt_cloud = opt_det["cloud_mask"]
opt_nodata = opt_det["nodata_mask"]
opt_perm = opt_det["pre_water_mask"]

# Load SAR (using 2024-09-24 baseline and 2024-10-06 response)
sar = SARService()
pre24 = np.load('data/cache/stac/S1A_IW_GRDH_1SDV_20240924T122211_20240924T122236_055807_06D1A1_rtc_VV_400x500.npy')
post = np.load('data/cache/stac/S1A_IW_GRDH_1SDV_20241006T122212_20241006T122237_055982_06D887_rtc_VV_400x500.npy')
pre_db, pre_v = sar.preprocess_sar(pre24)
post_db, post_v = sar.preprocess_sar(post)
sar_det = sar.detect_sar_flood(pre_db, post_db, pre_v, post_v, threshold_db=-15.5, change_threshold_db=-2.5, min_mmu_pixels=5)

sar_flood = sar_det["sar_newly_inundated"]
sar_valid = sar_det["both_valid"]
sar_perm = sar_det["sar_pre_water"]
sar_nodata = ~sar_valid

# Calculate areas helper
def area_sqkm(mask):
    return float(np.sum(cell_areas_2d[mask]) / 1e6)

# Test MECE Flood Union Decomposition
p_consensus = opt_flood & sar_flood
p_sar_cloud = sar_flood & opt_cloud
p_sar_nodata = sar_flood & opt_nodata
p_sar_clear_dry = sar_flood & opt_valid & (~opt_flood)

p_opt_nosar = opt_flood & sar_nodata
p_opt_dry_sar = opt_flood & sar_valid & (~sar_flood)

total_union = opt_flood | sar_flood

print("=== DECOMPOSITION TEST FOR 2024-09-24 BASELINE ===")
print("Total Grid Area (km²):", round(total_domain_sqkm, 3))
print("Optical Flood (km²):", round(area_sqkm(opt_flood), 3))
print("SAR Flood (km²):", round(area_sqkm(sar_flood), 3))
print("--- Flood Union Partitions ---")
print("1. Consensus Confirmed (both flood):", round(area_sqkm(p_consensus), 3))
print("2. SAR Flood under Optical Clouds:", round(area_sqkm(p_sar_cloud), 3))
print("3. SAR Flood under Optical NoData:", round(area_sqkm(p_sar_nodata), 3))
print("4. SAR Flood where Optical saw Dry Land:", round(area_sqkm(p_sar_clear_dry), 3))
print("5. Optical Flood Outside SAR Swath:", round(area_sqkm(p_opt_nosar), 3))
print("6. Optical Flood where SAR saw Dry Land:", round(area_sqkm(p_opt_dry_sar), 3))

sum_partitions = area_sqkm(p_consensus) + area_sqkm(p_sar_cloud) + area_sqkm(p_sar_nodata) + area_sqkm(p_sar_clear_dry) + area_sqkm(p_opt_nosar) + area_sqkm(p_opt_dry_sar)
union_area = area_sqkm(total_union)

print("Sum of 6 Flood Partitions (km²):", round(sum_partitions, 4))
print("Total Multi-Sensor Flood Union (km²):", round(union_area, 4))
print("Conservation Error (Union - Sum):", abs(union_area - sum_partitions))
assert np.isclose(union_area, sum_partitions, atol=1e-6), "Conservation check failed!"
print("-> CONSERVATION CHECK 1 PASSED!")
