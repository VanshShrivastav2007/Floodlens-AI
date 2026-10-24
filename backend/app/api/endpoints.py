"""
FastAPI REST API Endpoints for Nepal Terai Flood Intelligence.
Provides genuine satellite scene discovery, remote COG analysis execution,
and honest validation reporting without synthetic data fallbacks.
"""

from fastapi import APIRouter, HTTPException, Query, Response, status
from fastapi.responses import HTMLResponse, FileResponse
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import uuid
import os

from ..schemas.models import (
    StudyArea,
    AnalysisRunRequest,
    FloodAnalysisResult,
    SatelliteSceneMetadata,
    SettlementImpactSummary,
    AnalysisJobProgress,
    JobStatusType,
    PopulationExposureResult,
    SensorMode,
    GeographyProvenanceResponse
)
from ..geospatial.nepal_data import STUDY_AREAS, REAL_SETTLEMENTS, geo_registry
from ..geospatial.raster_processor import get_utm_epsg_for_lon
from ..services.flood_analyzer import FloodAnalyzerService
from ..services.satellite_service import SatelliteService
from ..services.sar_service import SARService
from ..services.report_generator import ReportGeneratorService

router = APIRouter()
analyzer_service = FloodAnalyzerService()
satellite_service = SatelliteService()
sar_service = SARService()

# In-memory storage for analysis runs and job tracking
RUN_CACHE: Dict[str, FloodAnalysisResult] = {}
ANALYSIS_JOBS: Dict[str, AnalysisJobProgress] = {}
ACTIVE_JOB: Optional[AnalysisJobProgress] = None

@router.get("/status")
async def get_system_status():
    """
    Returns system status, active Earth Engine status, and public STAC readiness.
    Honest reporting: does not claim Earth Engine is connected if credentials are not configured.
    """
    return {
        "system": "Nepal Terai Flood Intelligence System",
        "version": "1.1.0",
        "status": "OPERATIONAL",
        "earth_engine_authenticated": satellite_service.gee_available,
        "earth_engine_status": "Connected" if satellite_service.gee_available else "Unauthenticated (Service account or 'earthengine authenticate' required)",
        "primary_optical_source": "Sentinel-2 L2A Cloud-Optimized GeoTIFFs (10m Resolution)",
        "stac_catalog": "Element84 AWS STAC (sentinel-2-l2a)",
        "geodesic_projections": "Dynamic UTM Zone 44N (EPSG:32644) / Zone 45N (EPSG:32645)",
        "default_basin": "koshi_basin"
    }

@router.get("/study-areas", response_model=List[StudyArea])
async def list_study_areas(area_type: Optional[str] = Query(None, description="Filter by area_type: 'basin', 'district', or 'region'")):
    """
    Returns real, data-driven study areas across Nepal's Terai region.
    Supports administrative districts, hydrological flood basins, and region-wide scope.
    """
    areas = geo_registry.list_study_areas(area_type=area_type)
    return [StudyArea(**val) for val in areas]

@router.get("/study-areas/{study_area_id}", response_model=StudyArea)
async def get_study_area(study_area_id: str):
    """
    Retrieves full metadata and polygon geometry for a specific study area or district.
    """
    area = geo_registry.get_study_area(study_area_id)
    if not area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study area or district '{study_area_id}' not found in registry."
        )
    return StudyArea(**area)

@router.get("/settlements")
async def get_settlements(
    study_area_id: Optional[str] = Query(None, description="Study area or district identifier"),
    limit: Optional[int] = Query(None, description="Maximum settlements to return"),
    query: Optional[str] = Query(None, description="Search filter by settlement or municipality name")
):
    """
    Returns verified settlements in Nepal Terai with genuine coordinates, administrative ward linkage,
    and flood vulnerability attributes. Preserves legacy curated reference fixtures.
    """
    return geo_registry.get_settlements(study_area_id=study_area_id, limit=limit, query=query)

@router.get("/geography/provenance", response_model=GeographyProvenanceResponse)
async def get_geography_provenance():
    """
    Returns data provenance, source attribution, and verification status for administrative boundaries
    and settlement inventories across Nepal Terai.
    """
    summary = geo_registry.get_provenance_summary()
    return GeographyProvenanceResponse(**summary)

@router.get("/geography/coverage")
async def get_geography_coverage():
    """
    Returns spatial coverage metrics, district counts, and data completeness breakdown.
    """
    return geo_registry.get_coverage_summary()

@router.get("/satellite-scenes")
async def search_satellite_scenes(
    study_area_id: str = "koshi_basin",
    date_start: str = "2024-09-01",
    date_end: str = "2024-10-15",
    max_cloud_cover: float = 50.0,
    sensor_mode: SensorMode = SensorMode.SENTINEL_2_OPTICAL
):
    """
    Queries public STAC catalogs for genuine satellite observations covering the study area.
    Supports Sentinel-2 optical (Element84 AWS) and Sentinel-1 SAR (Planetary Computer).
    Never returns fabricated scenes.
    """
    study_area = geo_registry.get_study_area(study_area_id)
    if not study_area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study area or district '{study_area_id}' not found in registry."
        )
    if not study_area.get("bbox") or len(study_area["bbox"]) != 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Study area '{study_area_id}' has invalid bounding box geometry."
        )
    bbox = study_area["bbox"]

    if date_start > date_end:
        raise HTTPException(status_code=400, detail="date_start cannot be later than date_end")

    scenes: List[Dict[str, Any]] = []
    source_name = "STAC Satellite Catalogs"

    if sensor_mode in [SensorMode.SENTINEL_2_OPTICAL, SensorMode.DUAL_SENSOR_SYNERGY]:
        try:
            stac_scenes = await satellite_service.search_stac_scenes(
                bbox=bbox,
                date_start=date_start,
                date_end=date_end,
                max_cloud_cover=max_cloud_cover
            )
            for s in stac_scenes:
                scenes.append({
                    "scene_id": s.scene_id,
                    "platform": s.platform,
                    "instrument": s.instrument,
                    "acquisition_date": s.acquisition_date,
                    "cloud_cover_percent": s.cloud_cover_percent,
                    "spatial_resolution_m": s.spatial_resolution_m,
                    "bounding_box": s.bounding_box,
                    "bands": s.bands,
                    "source": "Element84 AWS STAC (Sentinel-2 L2A)",
                    "sensor_type": "OPTICAL"
                })
            source_name = "Element84 AWS STAC (Sentinel-2 L2A)"
        except Exception as e:
            if sensor_mode == SensorMode.SENTINEL_2_OPTICAL:
                raise HTTPException(status_code=502, detail=f"Sentinel-2 STAC catalog query failed: {e}")

    if sensor_mode in [SensorMode.SENTINEL_1_SAR, SensorMode.DUAL_SENSOR_SYNERGY]:
        try:
            sar_scenes = await sar_service.search_best_scenes(
                bbox=bbox,
                date_start=date_start,
                date_end=date_end
            )
            for s in sar_scenes:
                scenes.append({
                    "scene_id": s.scene_id,
                    "platform": s.platform,
                    "instrument": "C-SAR (RTC Level-1)",
                    "acquisition_date": s.acquisition_date,
                    "cloud_cover_percent": 0.0,
                    "spatial_resolution_m": 10.0,
                    "bounding_box": s.bounding_box,
                    "orbit_direction": s.orbit_direction,
                    "relative_orbit": s.relative_orbit,
                    "bands": ["VV", "VH"] if "VH" in s.asset_urls else ["VV"],
                    "source": "Microsoft Planetary Computer (sentinel-1-rtc)",
                    "sensor_type": "SAR"
                })
            if sensor_mode == SensorMode.SENTINEL_1_SAR:
                source_name = "Microsoft Planetary Computer (sentinel-1-rtc)"
            else:
                source_name = "Dual STAC (Element84 AWS S2 + Planetary Computer S1)"
        except Exception as e:
            if sensor_mode == SensorMode.SENTINEL_1_SAR:
                raise HTTPException(status_code=502, detail=f"Sentinel-1 STAC catalog query failed: {e}")

    # Sort chronologically
    scenes.sort(key=lambda x: x["acquisition_date"])

    return {
        "source": source_name,
        "study_area": study_area["name"],
        "bounding_box": bbox,
        "count": len(scenes),
        "scenes": scenes
    }

@router.get("/jobs/active", response_model=Optional[AnalysisJobProgress])
async def get_active_job():
    """
    Returns the currently executing satellite analysis job and its progress, or null if idle.
    """
    global ACTIVE_JOB
    return ACTIVE_JOB

@router.post("/jobs/active/cancel")
async def cancel_active_job():
    """
    Cancels or clears the currently active analysis job.
    """
    global ACTIVE_JOB
    if ACTIVE_JOB is not None:
        ACTIVE_JOB.status = JobStatusType.FAILED
        ACTIVE_JOB.stage = "Cancelled by user"
        ACTIVE_JOB.error = "Analysis execution was cancelled by user."
        ACTIVE_JOB.completed_at = datetime.now(timezone.utc).isoformat()
        job = ACTIVE_JOB
        ACTIVE_JOB = None
        return {"status": "cancelled", "job_id": job.run_id}
    return {"status": "no_active_job"}

@router.get("/jobs/{run_id}", response_model=AnalysisJobProgress)
async def get_job_by_id(run_id: str):
    """
    Retrieves progress or completion state of a specific analysis run job.
    """
    if run_id in ANALYSIS_JOBS:
        return ANALYSIS_JOBS[run_id]
    raise HTTPException(status_code=404, detail="Job not found")

@router.post("/analyze", response_model=FloodAnalysisResult)
async def run_flood_analysis(request: AnalysisRunRequest):
    """
    Executes full flood detection pipeline on real Sentinel-2 / Sentinel-1 satellite data:
    1. Discovers genuine pre-flood and post-flood scenes from STAC catalog
    2. Reads actual surface reflectance bands (B03, B08, B11, SCL) / RTC radar backscatter
    3. Masks clouds and cloud shadows using genuine SCL
    4. Computes NDWI / MNDWI / SAR amplitude anomaly and isolates newly inundated pixels
    5. Calculates projected metric areas in appropriate UTM Zone (44N or 45N)
    6. Performs proximity exposure modeling for local settlements
    7. Evaluates genuine ground-truth reference data (or reports UNAVAILABLE_REFERENCE_DATA)
    8. Exports georeferenced GeoTIFF and GeoJSON
    """
    target_area = geo_registry.get_study_area(request.study_area_id)
    if not target_area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study area or district '{request.study_area_id}' not found in registry."
        )
    if not target_area.get("bbox") or len(target_area["bbox"]) != 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Study area '{request.study_area_id}' has invalid bounding box geometry."
        )

    global ACTIVE_JOB
    job_id = f"job_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    job = AnalysisJobProgress(
        run_id=job_id,
        status=JobStatusType.PROCESSING,
        stage="Initiating satellite query...",
        progress_percent=5,
        started_at=datetime.now(timezone.utc).isoformat()
    )
    ANALYSIS_JOBS[job_id] = job
    ACTIVE_JOB = job

    def on_progress(stage: str, percent: int):
        job.stage = stage
        job.progress_percent = percent

    try:
        result = await analyzer_service.execute_flood_analysis(request, progress_callback=on_progress)
        RUN_CACHE[result.run_id] = result
        ANALYSIS_JOBS[result.run_id] = job
        job.run_id = result.run_id
        job.status = JobStatusType.COMPLETED
        job.stage = "Analysis complete"
        job.progress_percent = 100
        job.completed_at = datetime.now(timezone.utc).isoformat()
        job.result = result
        ACTIVE_JOB = None
        return result
    except ValueError as ve:
        job.status = JobStatusType.FAILED
        job.stage = "Validation / scene unavailable"
        job.error = str(ve)
        job.completed_at = datetime.now(timezone.utc).isoformat()
        # Keep ACTIVE_JOB with failed status so active poller receives the failure state
        ACTIVE_JOB = job
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(ve)
        )
    except Exception as e:
        import traceback
        traceback.print_exc()
        job.status = JobStatusType.FAILED
        job.stage = "Pipeline error"
        job.error = str(e)
        job.completed_at = datetime.now(timezone.utc).isoformat()
        # Keep ACTIVE_JOB with failed status so active poller receives the failure state
        ACTIVE_JOB = job
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Flood analysis pipeline error: {str(e)}"
        )

@router.get("/results/{run_id}", response_model=FloodAnalysisResult)
async def get_analysis_result(run_id: str):
    """
    Retrieves previous analysis run.
    """
    if run_id in RUN_CACHE:
        return RUN_CACHE[run_id]
    raise HTTPException(status_code=404, detail="Analysis run not found")

@router.get("/reports/{run_id}", response_class=HTMLResponse)
async def get_report_html(run_id: str):
    """
    Generates downloadable HTML disaster briefing report.
    """
    if run_id not in RUN_CACHE:
        raise HTTPException(status_code=404, detail="Analysis run not found")
    result = RUN_CACHE[run_id]
    html_content = ReportGeneratorService.generate_html_report(result)
    return HTMLResponse(content=html_content, status_code=200)

@router.get("/vectors/{filename}")
async def get_vector_geojson(filename: str):
    """
    Serves generated GeoJSON vectors for interactive MapLibre GL rendering.
    """
    file_path = os.path.join(os.path.abspath("outputs/vectors"), filename)
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="application/geo+json")
    raise HTTPException(status_code=404, detail="Vector file not found")

@router.get("/population/exposure", response_model=Optional[PopulationExposureResult])
async def get_population_exposure(
    study_area_id: str = "koshi_basin",
    run_id: Optional[str] = None
):
    """
    Returns genuine WorldPop 2020 100m building-constrained gridded population exposure
    and explainable rescue priority decision support ranking for the study area or a previous run.
    """
    import numpy as np

    if run_id and run_id in RUN_CACHE:
        return RUN_CACHE[run_id].population_exposure

    study_area = geo_registry.get_study_area(study_area_id)
    if not study_area:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Study area or district '{study_area_id}' not found in registry."
        )
    if not study_area.get("bbox") or len(study_area["bbox"]) != 4:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Study area '{study_area_id}' has invalid bounding box geometry."
        )
    bbox = study_area["bbox"]
    rows, cols = 400, 500
    empty_flood = np.zeros((rows, cols), dtype=bool)
    empty_cloud = np.zeros((rows, cols), dtype=bool)
    valid_mask = np.ones((rows, cols), dtype=bool)
    empty_perm = np.zeros((rows, cols), dtype=bool)

    result = analyzer_service.population_engine.calculate_population_exposure(
        flood_mask=empty_flood,
        cloud_mask=empty_cloud,
        valid_mask=valid_mask,
        permanent_water_mask=empty_perm,
        bbox=bbox,
        study_area_id=study_area_id,
        settlements=REAL_SETTLEMENTS,
        sensor_mode="SENTINEL_2_OPTICAL"
    )
    return result
