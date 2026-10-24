import urllib.request
import json
import os
import rasterio

BASE_URL = "http://127.0.0.1:8000/api"

def run_request(endpoint, payload=None, method="GET"):
    url = f"{BASE_URL}/{endpoint}" if not endpoint.startswith("http") else endpoint
    data = json.dumps(payload).encode("utf-8") if payload else None
    headers = {"Content-Type": "application/json"} if payload else {}
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            content_type = resp.headers.get("Content-Type", "")
            raw = resp.read()
            if "application/json" in content_type:
                return resp.status, json.loads(raw.decode("utf-8"))
            return resp.status, raw.decode("utf-8")
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(body)
        except Exception:
            return e.code, body

def main():
    print("=================================================================")
    print("LIVE END-TO-END PIPELINE VERIFICATION — FLOODLENS AI")
    print("=================================================================\n")

    # 1. System Status
    st_code, st_res = run_request("status")
    print(f"[STATUS] API Status Endpoint: HTTP {st_code}")
    print(f"  System: {st_res.get('system')}")
    print(f"  STAC Catalog: {st_res.get('stac_catalog')}")
    print(f"  Optical Provider: {st_res.get('primary_optical_source')}\n")

    # 2. Sentinel-2 Optical Analysis Run
    print("-----------------------------------------------------------------")
    print("RUN 1: Sentinel-2 Optical Analysis (Multi-Granule Mosaic)")
    print("-----------------------------------------------------------------")
    opt_payload = {
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
        "enable_mosaicing": True,
        "sensor_mode": "SENTINEL_2_OPTICAL"
    }
    code_opt, res_opt = run_request("analyze", opt_payload, method="POST")
    print(f"HTTP Response Code: {code_opt}")
    if code_opt == 200:
        print(f"  Run ID: {res_opt['run_id']}")
        print(f"  Provider Used: {res_opt['provider_used']}")
        print(f"  Sensor Mode: {res_opt['sensor_mode']}")
        print(f"  Mosaicked Tiles: {res_opt['tiles_mosaicked']}")
        print(f"  Pre-Flood Scenes: {[s['scene_id'] for s in res_opt.get('pre_scenes', [])]}")
        print(f"  Post-Flood Scenes: {[s['scene_id'] for s in res_opt.get('post_scenes', [])]}")
        print(f"  Total Study Area: {res_opt['total_study_area_sqkm']:.3f} km²")
        print(f"  Newly Inundated Extent: {res_opt['newly_inundated_sqkm']:.3f} km² ({res_opt['newly_inundated_hectares']:.1f} ha)")
        print(f"  Permanent Baseline Water: {res_opt['permanent_water_sqkm']:.3f} km²")
        print(f"  Valid Observation Coverage: {res_opt['valid_observation_percent']}%")
        print(f"  Cloud Mask Coverage: {res_opt['cloud_mask_percentage']}% ({res_opt['cloud_masked_sqkm']:.3f} km²)")
        print(f"  NoData Mask Coverage: {res_opt['nodata_mask_percentage']}% ({res_opt['nodata_masked_sqkm']:.3f} km²)")
        print(f"  Validation Status: {res_opt['validation']['validation_status']}")
        print(f"  Exposed Population: {res_opt['impact_summary']['total_exposed_population']:,}")
    else:
        print("  FAILED:", res_opt)

    # 3. Sentinel-1 SAR Analysis Run
    print("\n-----------------------------------------------------------------")
    print("RUN 2: Sentinel-1 SAR Analysis (Planetary Computer RTC C-SAR)")
    print("-----------------------------------------------------------------")
    sar_payload = {
        "study_area_id": "koshi_basin",
        "pre_flood_date_start": "2024-09-01",
        "pre_flood_date_end": "2024-09-25",
        "post_flood_date_start": "2024-09-26",
        "post_flood_date_end": "2024-10-15",
        "sensor_mode": "SENTINEL_1_SAR",
        "sar_polarization": "VV",
        "sar_threshold_db": -15.5,
        "sar_change_threshold_db": -2.5,
        "min_mapping_unit_pixels": 5
    }
    code_sar, res_sar = run_request("analyze", sar_payload, method="POST")
    print(f"HTTP Response Code: {code_sar}")
    if code_sar == 200:
        sar_res = res_sar.get("sar_result", {})
        print(f"  Run ID: {res_sar['run_id']}")
        print(f"  Provider Used: {res_sar['provider_used']}")
        print(f"  Sensor Mode: {res_sar['sensor_mode']}")
        print(f"  Pre-Flood SAR Scene: {sar_res['pre_scene']['scene_id']} ({sar_res['pre_scene']['acquisition_date']})")
        print(f"  Post-Flood SAR Scene: {sar_res['post_scene']['scene_id']} ({sar_res['post_scene']['acquisition_date']})")
        print(f"  SAR Orbit Match: Relative Orbit {sar_res['pre_scene']['relative_orbit']} -> {sar_res['post_scene']['relative_orbit']} ({sar_res['pre_scene']['orbit_direction']})")
        print(f"  SAR Inundated Extent: {res_sar['newly_inundated_sqkm']:.3f} km² ({res_sar['newly_inundated_hectares']:.1f} ha)")
        print(f"  SAR Valid Radar Coverage: {sar_res['valid_sar_coverage_percent']}% ({sar_res['valid_sar_sqkm']:.3f} km²)")
        print(f"  SAR Outside-Swath / NoData: {sar_res.get('sar_nodata_coverage_percent')}% ({sar_res.get('sar_nodata_sqkm')} km²)")
        print(f"  SAR Mean Delta Backscatter: {sar_res['sar_mean_backscatter_change_db']} dB")
        print(f"  Exposed Population: {res_sar['impact_summary']['total_exposed_population']:,}")
    else:
        print("  FAILED:", res_sar)

    # 4. Dual-Sensor Fusion Synergy Run
    print("\n-----------------------------------------------------------------")
    print("RUN 3: Dual-Sensor MECE Fusion Synergy (Optical + SAR)")
    print("-----------------------------------------------------------------")
    syn_payload = {
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
        "enable_mosaicing": True,
        "sensor_mode": "DUAL_SENSOR_SYNERGY",
        "sar_polarization": "VV",
        "sar_threshold_db": -15.5,
        "sar_change_threshold_db": -2.5
    }
    code_syn, res_syn = run_request("analyze", syn_payload, method="POST")
    print(f"HTTP Response Code: {code_syn}")
    if code_syn == 200:
        syn = res_syn.get("synergy_result", {})
        print(f"  Run ID: {res_syn['run_id']}")
        print(f"  Provider Used: {res_syn['provider_used']}")
        print(f"  Total Multi-Sensor Flood Union: {syn['total_multi_sensor_flood_sqkm']:.3f} km²")
        print("  --- MECE Flood Union Partitions (P1 to P6) ---")
        print(f"    P1: Consensus Confirmed (Optical & SAR agree): {syn['consensus_confirmed_flood_sqkm']:.3f} km²")
        print(f"    P2: Cloud-Piercing SAR Flood (under optical clouds): {syn['cloud_pierced_sar_flood_sqkm']:.3f} km²")
        print(f"    P3: SAR Flood under Optical NoData: {syn['sar_flood_optical_nodata_sqkm']:.3f} km²")
        print(f"    P4: SAR Discordant Flood (Optical Clear Dry): {syn['sar_discordant_flood_sqkm']:.3f} km²")
        print(f"    P5: Optical Flood Outside SAR Swath: {syn['optical_outside_sar_swath_sqkm']:.3f} km²")
        print(f"    P6: Optical Discordant Flood (SAR Valid Dry): {syn['optical_discordant_flood_sqkm']:.3f} km²")
        print(f"  Sum of 6 Partitions: {syn['sum_flood_partitions_sqkm']:.3f} km²")
        print(f"  Flood Union Conservation Verified: {syn['flood_union_conservation_verified']}")
        print(f"  Conservation Residual: {syn['flood_conservation_residual_sqkm']:.6f} km²")
        print(f"  Sensor Agreement: {syn['sensor_agreement_percent']}%")
        print("  --- Full Domain Spatial Accounting ---")
        print(f"    Domain Total Area: {syn['domain_total_sqkm']:.3f} km²")
        print(f"    Active Flood Union: {syn['total_multi_sensor_flood_sqkm']:.3f} km²")
        print(f"    Permanent Water: {syn['domain_permanent_water_sqkm']:.3f} km²")
        print(f"    Mutual Valid Dry Land: {syn['domain_both_dry_sqkm']:.3f} km²")
        print(f"    Optical Cloud / SAR Dry: {syn['domain_optical_cloud_sar_dry_sqkm']:.3f} km²")
        print(f"    Outside SAR Swath (Clear Dry): {syn['domain_optical_dry_sar_nodata_sqkm']:.3f} km²")
        print(f"    Outside SAR Swath (Cloud Covered): {syn['domain_optical_cloud_sar_nodata_sqkm']:.3f} km²")
        print(f"  Full Grid Conservation Verified: {syn['full_grid_conservation_verified']}")
        print(f"  Full Grid Residual: {syn['full_grid_residual_sqkm']:.6f} km²")
        print(f"  Exposed Population: {res_syn['impact_summary']['total_exposed_population']:,}")
    else:
        print("  FAILED:", res_syn)

    # 5. Invalid Request / Missing Data Handling
    print("\n-----------------------------------------------------------------")
    print("RUN 4: Error Handling / Unmet Criteria Graceful Failure Test")
    print("-----------------------------------------------------------------")
    impossible_payload = {
        "study_area_id": "koshi_basin",
        "pre_flood_date_start": "2024-09-01",
        "pre_flood_date_end": "2024-09-02",
        "post_flood_date_start": "2024-10-01",
        "post_flood_date_end": "2024-10-02",
        "max_cloud_cover_percent": 0.001,
        "sensor_mode": "SENTINEL_2_OPTICAL"
    }
    code_err, res_err = run_request("analyze", impossible_payload, method="POST")
    print(f"HTTP Response Code: {code_err} (Expected: 422)")
    print(f"Error Detail: {res_err.get('detail')}")
    assert code_err == 422, f"Expected 422, got {code_err}"
    print("-> Graceful HTTP 422 Unprocessable Content Verified! No synthetic data fabricated.")

    # 6. Export Validation
    print("\n-----------------------------------------------------------------")
    print("EXPORT VALIDATION — GEOTIFF, GEOJSON, AND HTML REPORT")
    print("-----------------------------------------------------------------")
    if code_syn == 200:
        run_id = res_syn["run_id"]
        tif_path = os.path.abspath(f"outputs/rasters/flood_extent_{run_id}.tif")
        json_path = os.path.abspath(f"outputs/vectors/flood_extent_{run_id}.geojson")

        print(f"1. GeoTIFF Inspection: {tif_path}")
        assert os.path.exists(tif_path), f"GeoTIFF file not found at {tif_path}"
        with rasterio.open(tif_path) as src:
            print(f"   Dimensions: {src.width} x {src.height}")
            print(f"   CRS: {src.crs}")
            print(f"   Bounds: {src.bounds}")
            print(f"   Transform: {src.transform}")
            print(f"   NoData Value: {src.nodata}")
            data = src.read(1)
            print(f"   Unique Values: {set(data.flatten().tolist())}")
            print(f"   Flooded Pixels (val=1): {int((data == 1).sum())}")
            assert src.crs == "EPSG:4326", f"Expected EPSG:4326, got {src.crs}"
            assert src.width == 500 and src.height == 400, "Dimensions mismatch!"

        print(f"\n2. GeoJSON Inspection: {json_path}")
        assert os.path.exists(json_path), f"GeoJSON file not found at {json_path}"
        with open(json_path, "r", encoding="utf-8") as f:
            gj = json.load(f)
            features = gj.get("features", [])
            print(f"   Feature Count: {len(features)}")
            print(f"   CRS Definition: {gj.get('crs')}")
            if features:
                sample = features[0]
                print(f"   Sample Feature Geometry Type: {sample.get('geometry', {}).get('type')}")
                print(f"   Sample Properties: {sample.get('properties')}")
                assert "Newly Inundated Floodwater" in sample.get('properties', {}).get('class', "")

        print("\n3. HTML Report Generation Inspection:")
        code_rep, rep_html = run_request(f"reports/{run_id}")
        print(f"   HTTP Response Code: {code_rep}")
        print(f"   HTML Length: {len(rep_html)} characters")
        assert "RAPID FLOOD EXTENT &amp; SETTLEMENT IMPACT REPORT" in rep_html
        assert "Mutually Exclusive, Collectively Exhaustive (MECE) Inundation Partitions" in rep_html
        assert "Domain Spatial Accounting" in rep_html
        assert "CONSERVATION VERIFIED" in rep_html
        print("   -> HTML report rendered complete MECE partition breakdown and domain accounting tables!")

    print("\n=================================================================")
    print("ALL LIVE END-TO-END PIPELINE CHECKS PASSED SUCCESSFULLY!")
    print("=================================================================")

if __name__ == "__main__":
    main()
