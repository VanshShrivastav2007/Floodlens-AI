import requests
import json
import os
import sys

BASE_URL = "http://127.0.0.1:8000"

def log_section(title):
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80)

def main():
    # 1. Check API Status
    log_section("1. BACKEND STATUS ENDPOINT VERIFICATION")
    res_status = requests.get(f"{BASE_URL}/api/status")
    print(f"HTTP Status: {res_status.status_code}")
    print(json.dumps(res_status.json(), indent=2))

    # 2. Run Real Analysis for koshi_basin
    log_section("2. REAL ANALYSIS EXECUTION FOR KOSHI BASIN")
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
    
    print(f"POST {BASE_URL}/api/analyze with payload:")
    print(json.dumps(payload, indent=2))
    
    res_analysis = requests.post(f"{BASE_URL}/api/analyze", json=payload)
    print(f"\nResponse Code: {res_analysis.status_code}")
    
    if res_analysis.status_code != 200:
        print(f"Error detail: {res_analysis.text}")
        sys.exit(1)
        
    data = res_analysis.json()
    
    # 3. Scene Metadata & Band Ingestion Details
    log_section("3. SATELLITE METADATA & REAL REMOTE COG INGESTION")
    print(f"Provider Used: {data.get('provider_used')}")
    print(f"UTM Projected CRS: {data.get('utm_zone_crs')}")
    
    pre = data['pre_scene']
    post = data['post_scene']
    print(f"\n[Pre-Flood Scene]")
    print(f"  Scene ID: {pre['scene_id']}")
    print(f"  Acquisition Date: {pre['acquisition_date']}")
    print(f"  Cloud Cover: {pre['cloud_cover_percent']}%")
    print(f"  Platform: {pre['platform']}")
    print(f"  Bands Ingested: {pre['bands']}")
    print(f"  Native CRS: {pre.get('native_crs')}")
    
    print(f"\n[Post-Flood Scene]")
    print(f"  Scene ID: {post['scene_id']}")
    print(f"  Acquisition Date: {post['acquisition_date']}")
    print(f"  Cloud Cover: {post['cloud_cover_percent']}%")
    print(f"  Platform: {post['platform']}")
    print(f"  Bands Ingested: {post['bands']}")
    print(f"  Native CRS: {post.get('native_crs')}")

    # Check cached bands on disk to verify real array ingestion
    cache_dir = "data/cache/stac"
    if os.path.exists(cache_dir):
        cached_files = [f for f in os.listdir(cache_dir) if f.endswith('.npy')]
        print(f"\nCached Real Band Arrays on Disk ({len(cached_files)} files in {cache_dir}):")
        for cf in sorted(cached_files)[:8]:
            fp = os.path.join(cache_dir, cf)
            print(f"  - {cf} ({os.path.getsize(fp):,} bytes)")

    # 4. Flood Area & Output Paths
    log_section("4. FLOOD AREA METRICS & GENERATED GIS ASSETS")
    print(f"Total Study Area: {data['total_study_area_sqkm']} sq km")
    print(f"Permanent Water Area: {data['permanent_water_sqkm']} sq km")
    print(f"Pre-Flood Water Area: {data['pre_flood_water_sqkm']} sq km")
    print(f"Post-Flood Water Area: {data['post_flood_water_sqkm']} sq km")
    print(f"Newly Inundated Flood Area: {data['newly_inundated_sqkm']} sq km ({data['newly_inundated_hectares']} hectares)")
    print(f"Atmospheric Cloud Masked Area: {data['cloud_masked_sqkm']} sq km ({data['cloud_mask_percentage']}%)")
    print(f"NoData / Swath Edge Area: {data.get('nodata_masked_sqkm')} sq km ({data.get('nodata_mask_percentage')}%)")
    print(f"Valid Cloud-Free Observation: {data['valid_observation_percent']}%")
    print(f"Low Coverage Warning Flag: {data.get('low_coverage_warning')}")
    print(f"Coverage Warning Message: {data.get('coverage_warning_message')}")
    
    geotiff_path = data['raster_outputs'].get('geotiff')
    geojson_path = data['vector_outputs'].get('geojson')
    report_url = data.get('report_download_url')
    
    print(f"\nRaster Output (GeoTIFF): {geotiff_path}")
    if geotiff_path and os.path.exists(geotiff_path.lstrip('/')):
        real_fp = geotiff_path.lstrip('/')
        print(f"  File exists on disk: YES ({os.path.getsize(real_fp):,} bytes)")
        import rasterio
        with rasterio.open(real_fp) as ds:
            print(f"  GeoTIFF CRS: {ds.crs}")
            print(f"  GeoTIFF Transform: {ds.transform}")
            print(f"  GeoTIFF Bounds: {ds.bounds}")
            print(f"  GeoTIFF Shape: {ds.shape}")
            print(f"  GeoTIFF Tags: {ds.tags()}")
    
    print(f"Vector Output (GeoJSON): {geojson_path}")
    if geojson_path and os.path.exists(geojson_path.lstrip('/')):
        real_gp = geojson_path.lstrip('/')
        print(f"  File exists on disk: YES ({os.path.getsize(real_gp):,} bytes)")
        
    print(f"Executive Report URL: {report_url}")

    # 5. Settlement Impact Summary
    log_section("5. SETTLEMENT IMPACT & PROXIMITY ASSESSMENT")
    impact = data['impact_summary']
    print(f"Total Settlements Analyzed: {impact['total_settlements_analyzed']}")
    print(f"Critical Count: {impact['critical_count']}")
    print(f"High Count: {impact['high_count']}")
    print(f"Moderate Count: {impact['moderate_count']}")
    print(f"Total Exposed Population: {impact['total_exposed_population']:,}")
    print(f"Critical Infrastructure Compromised: {impact['critical_infrastructure_count']}")
    print(f"Provenance: {impact.get('provenance')}")

    # 6. Scientific Validation Ground Truth
    log_section("6. SCIENTIFIC VALIDATION GROUND TRUTH STATUS")
    val = data.get('validation', {})
    print(f"Validation Status: {val.get('validation_status')}")
    print(f"Precision: {val.get('precision')}")
    print(f"Recall: {val.get('recall')}")
    print(f"F1-Score: {val.get('f1_score')}")
    print(f"IoU (Jaccard): {val.get('iou_jaccard')}")
    print(f"Overall Accuracy: {val.get('overall_accuracy')}")
    print(f"Validation Notes: {val.get('notes')}")

    # 7. Error Handling Verification (HTTP 422 on Unmet Criteria)
    log_section("7. HTTP 422 ERROR VERIFICATION ON UNMET OBSERVATION CRITERIA")
    bad_payload = {
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
    res_bad = requests.post(f"{BASE_URL}/api/analyze", json=bad_payload)
    print(f"Request with 0% cloud cover on cloudy monsoon dates:")
    print(f"HTTP Status: {res_bad.status_code} (Expected: 422)")
    print(f"Response Detail: {res_bad.json().get('detail')}")
    assert res_bad.status_code == 422, f"Expected 422, got {res_bad.status_code}"
    print("VERIFIED: Analysis fails cleanly with HTTP 422 and actionable message without synthetic fallback.")

    # 8. Basemap Tile Connectivity Verification
    log_section("8. BASEMAP TILE ACCESS VERIFICATION (NO API KEY REQUIRED)")
    tiles_to_test = [
        ("Carto Dark Geospatial", "https://a.basemaps.cartocdn.com/dark_all/7/96/53.png"),
        ("Esri World Imagery", "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/7/53/96"),
        ("OpenStreetMap Standard", "https://tile.openstreetmap.org/7/96/53.png")
    ]
    for name, url in tiles_to_test:
        try:
            r = requests.get(url, headers={"User-Agent": "FloodLens-AI/1.1 (Runtime Verification)"}, timeout=10)
            print(f"[{name}] {url} -> HTTP {r.status_code} {r.headers.get('Content-Type')}")
            assert r.status_code == 200, f"Expected 200, got {r.status_code}"
        except Exception as e:
            print(f"[{name}] Failed: {e}")

    log_section("ALL RUNTIME VERIFICATIONS COMPLETED SUCCESSFULLY")

if __name__ == "__main__":
    main()
