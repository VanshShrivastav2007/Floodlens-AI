"""
Test script to verify Nepal Terai Flood Intelligence backend pipeline.
Tests data models, water indices, change detection, UTM 45N area math,
settlement impacts, validation metrics, and GeoTIFF / GeoJSON exports.
"""

import asyncio
from backend.app.schemas.models import AnalysisRunRequest, WaterIndexType
from backend.app.services.flood_analyzer import FloodAnalyzerService
import os

async def main():
    print("Initializing FloodAnalyzerService...")
    service = FloodAnalyzerService()

    req = AnalysisRunRequest(
        study_area_id="koshi_basin",
        pre_flood_date_start="2024-09-15",
        post_flood_date_start="2024-09-29",
        water_index=WaterIndexType.MNDWI,
        water_threshold=0.05,
        filter_permanent_water=True,
        min_mapping_unit_pixels=5
    )

    print("Executing flood analysis...")
    result = await service.execute_flood_analysis(req)

    print("\n=== FLOOD ANALYSIS RESULT ===")
    print(f"Run ID: {result.run_id}")
    print(f"Study Area: {result.study_area.name}")
    print(f"Total Area: {result.total_study_area_sqkm} sq km")
    print(f"Permanent River Water: {result.permanent_water_sqkm} sq km")
    print(f"Newly Inundated Floodwater: {result.newly_inundated_sqkm} sq km ({result.newly_inundated_hectares} hectares)")
    print(f"Cloud Masked Area: {result.cloud_masked_sqkm} sq km ({result.cloud_mask_percentage}%)")
    print(f"Valid Observation Percent: {result.valid_observation_percent}%")

    print("\n=== SETTLEMENT IMPACT ASSESSMENT ===")
    summary = result.impact_summary
    print(f"Total Settlements Evaluated: {summary.total_settlements_analyzed}")
    print(f"Critical Settlements: {summary.critical_count}")
    print(f"High Risk Settlements: {summary.high_count}")
    print(f"Moderate Risk Settlements: {summary.moderate_count}")
    print(f"Total Population Exposed: {summary.total_exposed_population:,}")
    print(f"Critical Facilities at Risk: {summary.critical_infrastructure_count}")

    print("\nTop 3 Impacted Settlements:")
    for s in summary.settlements[:3]:
        print(f" - [{s.impact_level}] {s.name} ({s.municipality}): {s.distance_to_flood_m}m from flood | Pop: {s.population:,} | Exposure: {s.exposure_percentage}%")
        print(f"   Action: {s.recommended_action}")

    print("\n=== ACCURACY VALIDATION ===")
    val = result.validation
    print(f"Reference: {val.reference_dataset}")
    if val.precision is not None:
        print(f"Precision: {val.precision * 100:.1f}%")
        print(f"Recall: {val.recall * 100:.1f}%")
        print(f"F1-Score: {val.f1_score * 100:.1f}%")
        print(f"IoU (Jaccard Index): {val.iou_jaccard * 100:.1f}%")
        print(f"Overall Accuracy: {val.overall_accuracy * 100:.1f}%")
    else:
        print(f"Validation Metrics: {val.validation_status} ({val.notes})")
    print(f"Status: {val.validation_status}")

    print("\n=== EXPORT ARTIFACTS ===")
    for k, v in result.raster_outputs.items():
        print(f"Raster: {k} -> {v}")
    for k, v in result.vector_outputs.items():
        print(f"Vector: {k} -> {v}")

    # Verify files on disk
    for f in os.listdir("outputs/rasters"):
        print(f"Saved raster: outputs/rasters/{f}")
    for f in os.listdir("outputs/vectors"):
        print(f"Saved vector: outputs/vectors/{f}")

if __name__ == "__main__":
    asyncio.run(main())
