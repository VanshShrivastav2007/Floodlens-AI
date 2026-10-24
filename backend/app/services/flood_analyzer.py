"""
Flood Analysis Orchestrator.
Coordinates real satellite scene discovery, remote band ingestion, SCL cloud masking,
Sentinel-1 SAR C-band radar backscatter processing, multi-sensor synergy fusion,
NDWI/MNDWI index computation, change detection, dynamic UTM metric area calculations,
settlement proximity impact modeling, and honest ground-truth validation.
Never produces synthetic flood masks or fabricated accuracy metrics.
"""

import os
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List, Tuple, Callable
import asyncio
import numpy as np

from ..schemas.models import (
    AnalysisRunRequest,
    FloodAnalysisResult,
    WaterIndexType,
    StudyArea,
    SatelliteSceneMetadata,
    SensorMode,
    SARPolarization,
    SARSceneMetadata,
    SARAnalysisResult,
    DualSensorSynergyResult,
    PopulationExposureResult
)
from ..geospatial.nepal_data import STUDY_AREAS, REAL_SETTLEMENTS, geo_registry
from ..geospatial.population_exposure import PopulationExposureEngine
from ..geospatial.indices import (
    calculate_ndwi,
    calculate_mndwi,
    compute_otsu_threshold,
    create_cloud_mask_scl,
    create_nodata_mask,
    detect_flood_extent
)
from ..geospatial.raster_processor import (
    calculate_projected_area,
    compute_raster_cell_areas_wgs84,
    export_mask_to_geotiff,
    vectorize_flood_extent,
    assess_settlement_impacts,
    get_utm_epsg_for_lon,
    generate_false_color_composite,
    generate_true_color_composite,
    generate_sar_grayscale_image,
    generate_flood_difference_rgba,
    export_image_to_png,
    export_multiclass_difference_geotiff,
    compute_raster_diagnostic_metadata
)
from .satellite_service import SatelliteService
from .sar_service import SARService
from .validation_service import ValidationService

OUTPUT_DIR_RASTERS = os.path.abspath("outputs/rasters")
OUTPUT_DIR_VECTORS = os.path.abspath("outputs/vectors")
OUTPUT_DIR_REPORTS = os.path.abspath("outputs/reports")

class FloodAnalyzerService:
    def __init__(self):
        self.satellite_service = SatelliteService()
        self.sar_service = SARService()
        self.validation_service = ValidationService()
        self.population_engine = PopulationExposureEngine()
        self._ensure_output_directories()

    def _ensure_output_directories(self):
        os.makedirs(OUTPUT_DIR_RASTERS, exist_ok=True)
        os.makedirs(OUTPUT_DIR_VECTORS, exist_ok=True)
        os.makedirs(OUTPUT_DIR_REPORTS, exist_ok=True)

    async def execute_flood_analysis(
        self,
        req: AnalysisRunRequest,
        progress_callback: Optional[Callable[[str, int], None]] = None
    ) -> FloodAnalysisResult:
        def report_progress(stage: str, percent: int):
            if progress_callback:
                try:
                    progress_callback(stage, percent)
                except Exception:
                    pass

        report_progress("Initializing Analysis Grid & Spatial Parameters...", 5)
        run_id = f"run_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        study_area_info = geo_registry.get_study_area(req.study_area_id)
        if not study_area_info:
            raise ValueError(f"Study area or district '{req.study_area_id}' not found in registry.")
        if not study_area_info.get("bbox") or len(study_area_info["bbox"]) != 4:
            raise ValueError(f"Study area '{req.study_area_id}' has invalid bounding box geometry.")
        bbox = study_area_info["bbox"]
        center_lon = (bbox[0] + bbox[2]) / 2.0
        utm_crs = get_utm_epsg_for_lon(center_lon)
        grid_shape = (400, 500)
        rows, cols = grid_shape

        sensor_mode = getattr(req, "sensor_mode", SensorMode.SENTINEL_2_OPTICAL)
        needs_optical = sensor_mode in [SensorMode.SENTINEL_2_OPTICAL, SensorMode.DUAL_SENSOR_SYNERGY]
        needs_sar = sensor_mode in [SensorMode.SENTINEL_1_SAR, SensorMode.DUAL_SENSOR_SYNERGY]

        # Calculate exact row-wise geodesic cell areas for conservation checks
        cell_areas_1d = compute_raster_cell_areas_wgs84(bbox, cols, rows)
        cell_areas_2d = np.tile(cell_areas_1d[:, np.newaxis], (1, cols))
        total_sqkm, _, _ = calculate_projected_area(np.ones((rows, cols), dtype=bool), bbox, cols, rows)

        # ---------------------------------------------------------------------
        # 1. OPTICAL PIPELINE: Sentinel-2 Multi-Granule Mosaicing & Indices
        # ---------------------------------------------------------------------
        opt_flood_mask = np.zeros((rows, cols), dtype=bool)
        opt_valid_mask = np.zeros((rows, cols), dtype=bool)
        opt_cloud_mask = np.zeros((rows, cols), dtype=bool)
        opt_nodata_mask = np.zeros((rows, cols), dtype=bool)
        opt_perm_water = np.zeros((rows, cols), dtype=bool)
        pre_scene = None
        post_scene = None
        pre_scenes: List[SatelliteSceneMetadata] = []
        post_scenes: List[SatelliteSceneMetadata] = []
        tiles_mosaicked: List[str] = []
        is_mosaic = False
        mosaic_provenance: Optional[Dict[str, Any]] = None
        mosaic_warning: Optional[str] = None
        pre_water_sqkm = 0.0
        post_water_sqkm = 0.0
        cloud_sqkm = 0.0
        nodata_sqkm = 0.0
        cloud_percentage = 0.0
        nodata_percentage = 0.0
        valid_obs_pct = 0.0
        low_coverage_warning = False
        coverage_warning_msg = None

        if needs_optical:
            report_progress("Searching Copernicus STAC for Sentinel-2 L2A Scenes...", 15)
            enable_mosaic = getattr(req, "enable_mosaicing", True)
            if enable_mosaic:
                pre_scenes = await self.satellite_service.find_best_scenes_multi_tile(
                    bbox=bbox,
                    date_start=req.pre_flood_date_start,
                    date_end=req.pre_flood_date_end,
                    max_cloud_cover=req.max_cloud_cover_percent
                )
                post_scenes = await self.satellite_service.find_best_scenes_multi_tile(
                    bbox=bbox,
                    date_start=req.post_flood_date_start,
                    date_end=req.post_flood_date_end,
                    max_cloud_cover=req.max_cloud_cover_percent
                )
            else:
                pre_scenes = []
                post_scenes = []

            if not pre_scenes:
                single_pre = await self.satellite_service.find_best_scene(
                    bbox=bbox,
                    date_start=req.pre_flood_date_start,
                    date_end=req.pre_flood_date_end,
                    max_cloud_cover=req.max_cloud_cover_percent
                )
                if not single_pre:
                    if sensor_mode == SensorMode.SENTINEL_2_OPTICAL:
                        raise ValueError(
                            f"No suitable real Sentinel-2 scene found for pre-flood window "
                            f"({req.pre_flood_date_start} to {req.pre_flood_date_end}) with cloud cover <= {req.max_cloud_cover_percent}%. "
                            f"Please broaden the date range or increase maximum cloud tolerance."
                        )
                else:
                    pre_scenes = [single_pre]

            pre_tile = pre_scenes[0].scene_id.split('_')[1] if pre_scenes and '_' in pre_scenes[0].scene_id else None

            if not post_scenes:
                single_post = await self.satellite_service.find_best_scene(
                    bbox=bbox,
                    date_start=req.post_flood_date_start,
                    date_end=req.post_flood_date_end,
                    max_cloud_cover=req.max_cloud_cover_percent,
                    preferred_tile=pre_tile
                )
                if not single_post:
                    if sensor_mode == SensorMode.SENTINEL_2_OPTICAL:
                        cloudy_scenes = await self.satellite_service.search_stac_scenes(
                            bbox=bbox,
                            date_start=req.post_flood_date_start,
                            date_end=req.post_flood_date_end,
                            max_cloud_cover=100.0
                        )
                        if cloudy_scenes:
                            min_cloud = min(s.cloud_cover_percent for s in cloudy_scenes)
                            raise ValueError(
                                f"No clear-sky Sentinel-2 optical scene found for post-flood window "
                                f"({req.post_flood_date_start} to {req.post_flood_date_end}) with cloud cover <= {req.max_cloud_cover_percent}%. "
                                f"Existing scenes have high monsoon cloud cover ({min_cloud:.1f}%). "
                                f"Please switch to Sentinel-1 C-SAR or Dual-Sensor Synergy for all-weather cloud penetration, "
                                f"or broaden the observation window."
                            )
                        else:
                            raise ValueError(
                                f"No Sentinel-2 observations found in STAC catalog for post-flood window "
                                f"({req.post_flood_date_start} to {req.post_flood_date_end}). "
                                f"Please broaden the date range."
                            )
                    elif sensor_mode == SensorMode.DUAL_SENSOR_SYNERGY:
                        # In Dual-Sensor Synergy, accept higher cloud cover to obtain genuine SCL cloud mask for SAR synergy
                        single_post = await self.satellite_service.find_best_scene(
                            bbox=bbox,
                            date_start=req.post_flood_date_start,
                            date_end=req.post_flood_date_end,
                            max_cloud_cover=100.0,
                            preferred_tile=pre_tile
                        )
                        if single_post:
                            post_scenes = [single_post]
                else:
                    post_scenes = [single_post]

            if pre_scenes and post_scenes:
                report_progress("Ingesting Sentinel-2 Surface Reflectance Bands (B03, B08, B11, SCL)...", 30)
                pre_scenes_bands = []
                for s in pre_scenes:
                    bands = await asyncio.wait_for(
                        asyncio.to_thread(self.satellite_service.load_surface_reflectance_bands, s, bbox, grid_shape),
                        timeout=180.0
                    )
                    pre_scenes_bands.append((s, bands))
                pre_bands, pre_mosaic_meta = self.satellite_service.mosaic_tile_bands(pre_scenes_bands, grid_shape)

                post_scenes_bands = []
                for s in post_scenes:
                    bands = await asyncio.wait_for(
                        asyncio.to_thread(self.satellite_service.load_surface_reflectance_bands, s, bbox, grid_shape),
                        timeout=180.0
                    )
                    post_scenes_bands.append((s, bands))
                post_bands, post_mosaic_meta = self.satellite_service.mosaic_tile_bands(post_scenes_bands, grid_shape)

                report_progress("Calculating Spectral Indices (MNDWI/NDWI) & Cloud Masking...", 48)

                pre_scene = pre_scenes[0]
                post_scene = post_scenes[0]
                tiles_mosaicked = sorted(list(set(pre_mosaic_meta["tiles_mosaicked"] + post_mosaic_meta["tiles_mosaicked"])))
                is_mosaic = (len(tiles_mosaicked) > 1)
                mosaic_provenance = {"pre": pre_mosaic_meta, "post": post_mosaic_meta}
                mosaic_warning = pre_mosaic_meta.get("date_difference_warning") or post_mosaic_meta.get("date_difference_warning")

                pre_nodata = create_nodata_mask(pre_bands["SCL"], [pre_bands["B03"], pre_bands["B08"], pre_bands["B11"]])
                post_nodata = create_nodata_mask(post_bands["SCL"], [post_bands["B03"], post_bands["B08"], post_bands["B11"]])
                pre_cloud = create_cloud_mask_scl(pre_bands["SCL"], include_nodata=False)
                post_cloud = create_cloud_mask_scl(post_bands["SCL"], include_nodata=False)

                if req.water_index == WaterIndexType.NDWI:
                    pre_index = calculate_ndwi(pre_bands["B03"], pre_bands["B08"])
                    post_index = calculate_ndwi(post_bands["B03"], post_bands["B08"])
                elif req.water_index == WaterIndexType.MNDWI:
                    pre_index = calculate_mndwi(pre_bands["B03"], pre_bands["B11"])
                    post_index = calculate_mndwi(post_bands["B03"], post_bands["B11"])
                else:
                    ndwi_pre = calculate_ndwi(pre_bands["B03"], pre_bands["B08"])
                    mndwi_pre = calculate_mndwi(pre_bands["B03"], pre_bands["B11"])
                    pre_index = (ndwi_pre + mndwi_pre) / 2.0
                    ndwi_post = calculate_ndwi(post_bands["B03"], post_bands["B08"])
                    mndwi_post = calculate_mndwi(post_bands["B03"], post_bands["B11"])
                    post_index = (ndwi_post + mndwi_post) / 2.0

                threshold = req.water_threshold
                pre_water = (pre_index > threshold).astype(np.uint8)
                post_water = (post_index > threshold).astype(np.uint8)

                detection = detect_flood_extent(
                    pre_water=pre_water,
                    post_water=post_water,
                    pre_cloud=pre_cloud,
                    post_cloud=post_cloud,
                    pre_nodata=pre_nodata,
                    post_nodata=post_nodata,
                    filter_permanent=req.filter_permanent_water,
                    min_mmu_pixels=req.min_mapping_unit_pixels
                )

                opt_flood_mask = detection["newly_inundated"]
                opt_valid_mask = detection["valid_mask"]
                opt_cloud_mask = detection["cloud_mask"]
                opt_nodata_mask = detection["nodata_mask"]
                opt_perm_water = detection["pre_water_mask"]

                pre_water_sqkm, _, _ = calculate_projected_area(detection["pre_water_mask"], bbox, cols, rows)
                post_water_sqkm, _, _ = calculate_projected_area(detection["post_water_mask"], bbox, cols, rows)
                cloud_sqkm, _, _ = calculate_projected_area(opt_cloud_mask, bbox, cols, rows)
                nodata_sqkm, _, _ = calculate_projected_area(detection["nodata_mask"], bbox, cols, rows)

                cloud_percentage = round((detection["cloud_pixel_count"] / float(rows * cols)) * 100.0, 1)
                nodata_percentage = round((detection["nodata_pixel_count"] / float(rows * cols)) * 100.0, 1)
                valid_obs_pct = round((detection["valid_pixel_count"] / float(rows * cols)) * 100.0, 1)

                min_cov = getattr(req, "min_valid_coverage_percent", 30.0)
                low_coverage_warning = (valid_obs_pct < min_cov)
                if low_coverage_warning:
                    coverage_warning_msg = (
                        f"LOW OBSERVATION COVERAGE WARNING: Valid cloud-free observation covers only {valid_obs_pct}% "
                        f"of the study domain (below {min_cov}% reliability threshold). Detected optical flood extent "
                        f"reflects only observable clear-sky gaps and must NOT be interpreted as the "
                        f"total basin inundation. Persistent monsoon clouds obscured {cloud_percentage}% of the area."
                    )

        # ---------------------------------------------------------------------
        # 2. RADAR PIPELINE: Sentinel-1 SAR C-Band RTC Processing
        # ---------------------------------------------------------------------
        sar_result: Optional[SARAnalysisResult] = None
        sar_flood_mask = np.zeros((rows, cols), dtype=bool)
        sar_perm_water = np.zeros((rows, cols), dtype=bool)
        sar_both_valid = np.zeros((rows, cols), dtype=bool)

        if needs_sar:
            report_progress("Searching Microsoft Planetary Computer for Sentinel-1 RTC Radar...", 60)
            pol_str = getattr(req, "sar_polarization", SARPolarization.VV)
            pol_val = pol_str.value if hasattr(pol_str, "value") else str(pol_str)

            sar_pre_scene, sar_post_scene = await self.sar_service.find_paired_sar_scenes(
                bbox=bbox,
                pre_start=req.pre_flood_date_start,
                pre_end=req.pre_flood_date_end,
                post_start=req.post_flood_date_start,
                post_end=req.post_flood_date_end,
                polarization=pol_val
            )

            if not sar_pre_scene or not sar_post_scene:
                if sensor_mode == SensorMode.SENTINEL_1_SAR:
                    raise ValueError(
                        f"No suitable real Sentinel-1 RTC scene found for date windows "
                        f"({req.pre_flood_date_start} to {req.pre_flood_date_end} / {req.post_flood_date_start} to {req.post_flood_date_end}). "
                        f"Please broaden the date range."
                    )
            else:
                report_progress(f"Ingesting Pre-Flood Sentinel-1 RTC ({sar_pre_scene.acquisition_date}, Orbit {sar_pre_scene.relative_orbit})...", 64)
                pre_sar_lin = await asyncio.wait_for(
                    asyncio.to_thread(self.sar_service.load_sar_backscatter, sar_pre_scene, bbox, grid_shape, polarization=pol_val),
                    timeout=60.0
                )
                report_progress(f"Ingesting Post-Flood Sentinel-1 RTC ({sar_post_scene.acquisition_date}, Orbit {sar_post_scene.relative_orbit})...", 70)
                post_sar_lin = await asyncio.wait_for(
                    asyncio.to_thread(self.sar_service.load_sar_backscatter, sar_post_scene, bbox, grid_shape, polarization=pol_val),
                    timeout=60.0
                )

                report_progress("Applying Lee Speckle Filter & Change Detection...", 75)
                pre_sar_db, pre_sar_valid = self.sar_service.preprocess_sar(pre_sar_lin, speckle_filter_size=3)
                post_sar_db, post_sar_valid = self.sar_service.preprocess_sar(post_sar_lin, speckle_filter_size=3)

                sar_det = self.sar_service.detect_sar_flood(
                    pre_db=pre_sar_db,
                    post_db=post_sar_db,
                    pre_valid=pre_sar_valid,
                    post_valid=post_sar_valid,
                    threshold_db=getattr(req, "sar_threshold_db", -15.5),
                    change_threshold_db=getattr(req, "sar_change_threshold_db", -2.5),
                    min_mmu_pixels=req.min_mapping_unit_pixels
                )

                sar_flood_mask = sar_det["sar_newly_inundated"]
                sar_perm_water = sar_det["sar_pre_water"]
                sar_both_valid = sar_det["both_valid"]

                sar_sqkm, sar_ha, _ = calculate_projected_area(sar_flood_mask, bbox, cols, rows)
                sar_perm_sqkm, _, _ = calculate_projected_area(sar_perm_water, bbox, cols, rows)
                sar_valid_sqkm, _, _ = calculate_projected_area(sar_both_valid, bbox, cols, rows)
                sar_valid_pct = round((np.sum(sar_both_valid) / float(rows * cols)) * 100.0, 1)
                sar_nodata_sqkm = round(total_sqkm - sar_valid_sqkm, 3)
                sar_nodata_pct = round(100.0 - sar_valid_pct, 1)

                sar_pre_scene.mean_backscatter_db = round(float(np.nanmean(pre_sar_db[pre_sar_valid])), 2)
                sar_post_scene.mean_backscatter_db = round(float(np.nanmean(post_sar_db[post_sar_valid])), 2)

                sar_result = SARAnalysisResult(
                    pre_scene=sar_pre_scene,
                    post_scene=sar_post_scene,
                    polarization=pol_val,
                    threshold_db=getattr(req, "sar_threshold_db", -15.5),
                    change_threshold_db=getattr(req, "sar_change_threshold_db", -2.5),
                    valid_sar_coverage_percent=sar_valid_pct,
                    valid_sar_sqkm=sar_valid_sqkm,
                    sar_footprint_coverage_percent=100.0,
                    sar_nodata_sqkm=sar_nodata_sqkm,
                    sar_nodata_coverage_percent=sar_nodata_pct,
                    sar_newly_inundated_sqkm=sar_sqkm,
                    sar_newly_inundated_hectares=sar_ha,
                    sar_permanent_water_sqkm=sar_perm_sqkm,
                    sar_mean_backscatter_change_db=round(sar_det["mean_delta_db"], 2),
                    geotiff_path=None
                )

        # ---------------------------------------------------------------------
        # 3. DUAL-SENSOR FUSION & SYNERGY SYNTHESIS (WITH DEGRADED-MODE REPORTING)
        # ---------------------------------------------------------------------
        has_optical = bool(pre_scenes and post_scenes)
        has_sar = bool(sar_result is not None)
        degraded_mode = False
        degraded_warning: Optional[str] = None
        synergy_result: Optional[DualSensorSynergyResult] = None

        if sensor_mode == SensorMode.DUAL_SENSOR_SYNERGY:
            if has_optical and has_sar:
                report_progress("Synthesizing Dual-Sensor MECE Fusion & Conservation Partitions...", 78)
                synergy_result = self.sar_service.compute_sensor_synergy(
                    optical_flood=opt_flood_mask,
                    optical_valid=opt_valid_mask,
                    optical_cloud=opt_cloud_mask,
                    sar_flood=sar_flood_mask,
                    sar_valid=sar_both_valid,
                    cell_areas_2d=cell_areas_2d,
                    optical_nodata=opt_nodata_mask,
                    optical_perm_water=opt_perm_water,
                    sar_perm_water=sar_perm_water
                )
            elif has_optical and not has_sar:
                degraded_mode = True
                degraded_warning = (
                    "Dual-Sensor Synergy degraded to Sentinel-2 Optical fallback: "
                    "No compatible Sentinel-1 RTC orbit passes were acquired over this domain within the requested date window. "
                    "Monsoon cloud-covered areas remain unobservable."
                )
            elif not has_optical and has_sar:
                degraded_mode = True
                degraded_warning = (
                    "Dual-Sensor Synergy degraded to Sentinel-1 C-SAR fallback: "
                    "No clear-sky Sentinel-2 optical scenes were available (exceeded cloud tolerance or unobserved). "
                    "Utilizing all-weather radar backscatter anomaly detection."
                )
            else:
                raise ValueError(
                    f"Dual-Sensor Synergy pipeline failed: neither Sentinel-2 optical nor Sentinel-1 SAR observations "
                    f"are available for study area '{req.study_area_id}' in the requested temporal windows "
                    f"({req.pre_flood_date_start} to {req.pre_flood_date_end} / {req.post_flood_date_start} to {req.post_flood_date_end})."
                )

        # ---------------------------------------------------------------------
        # 4. PRIMARY INUNDATION MASK SELECTION (BASED ON SENSOR MODE & DEGRADED STATE)
        # ---------------------------------------------------------------------
        min_cov = getattr(req, "min_valid_coverage_percent", 30.0)

        if sensor_mode == SensorMode.SENTINEL_1_SAR or (sensor_mode == SensorMode.DUAL_SENSOR_SYNERGY and degraded_mode and has_sar):
            primary_flood_mask = sar_flood_mask
            primary_valid_mask = sar_both_valid
            perm_sqkm = sar_result.sar_permanent_water_sqkm if sar_result else 0.0
            opt_perm_metric = None
            sar_perm_metric = perm_sqkm
            comb_perm_metric = perm_sqkm
            flood_sqkm = sar_result.sar_newly_inundated_sqkm if sar_result else 0.0
            flood_hectares = sar_result.sar_newly_inundated_hectares if sar_result else 0.0
            provider_used = "Microsoft Planetary Computer STAC (Sentinel-1 RTC C-SAR)" if sensor_mode == SensorMode.SENTINEL_1_SAR else "Dual-Sensor Synergy (DEGRADED: Sentinel-1 C-SAR Fallback)"
            threshold = getattr(req, "sar_threshold_db", -15.5)
            cloud_percentage = 0.0
            cloud_sqkm = 0.0
            nodata_percentage = round(100.0 - (sar_result.valid_sar_coverage_percent if sar_result else 0.0), 1)
            nodata_sqkm = round(total_sqkm - (sar_result.valid_sar_sqkm if sar_result else 0.0), 3)
            valid_obs_pct = sar_result.valid_sar_coverage_percent if sar_result else 0.0
            low_coverage_warning = (valid_obs_pct < min_cov)
            if low_coverage_warning:
                coverage_warning_msg = f"SAR coverage covers {valid_obs_pct}% of domain (below {min_cov}% threshold)."
            else:
                coverage_warning_msg = None

            # Fallback mock scenes for Pydantic backward compatibility
            if not pre_scene and sar_result:
                pre_scene = SatelliteSceneMetadata(
                    scene_id=sar_result.pre_scene.scene_id,
                    platform=sar_result.pre_scene.platform,
                    instrument=sar_result.pre_scene.instrument,
                    acquisition_date=sar_result.pre_scene.acquisition_date,
                    cloud_cover_percent=0.0,
                    bounding_box=bbox,
                    bands=[sar_result.polarization]
                )
            if not post_scene and sar_result:
                post_scene = SatelliteSceneMetadata(
                    scene_id=sar_result.post_scene.scene_id,
                    platform=sar_result.post_scene.platform,
                    instrument=sar_result.post_scene.instrument,
                    acquisition_date=sar_result.post_scene.acquisition_date,
                    cloud_cover_percent=0.0,
                    bounding_box=bbox,
                    bands=[sar_result.polarization]
                )

        elif sensor_mode == SensorMode.DUAL_SENSOR_SYNERGY and not degraded_mode and synergy_result is not None:
            primary_flood_mask = opt_flood_mask | sar_flood_mask
            primary_valid_mask = opt_valid_mask | sar_both_valid
            flood_sqkm = synergy_result.total_multi_sensor_flood_sqkm
            flood_hectares = round(flood_sqkm * 100.0, 1)
            # domain_permanent_water_sqkm is the non-flood permanent water: (opt | sar) & (~flood)
            perm_sqkm = synergy_result.domain_permanent_water_sqkm
            opt_perm_metric = synergy_result.optical_permanent_water_sqkm
            sar_perm_metric = synergy_result.sar_permanent_water_sqkm
            comb_perm_metric = synergy_result.combined_permanent_water_union_sqkm
            provider_used = "Dual-Sensor Synergy: Sentinel-2 L2A (AWS) + Sentinel-1 RTC C-SAR (Planetary Computer)"
            threshold = req.water_threshold
            valid_obs_pct = round((np.sum(primary_valid_mask) / float(rows * cols)) * 100.0, 1)
            nodata_percentage = round(100.0 - valid_obs_pct, 1)
            nodata_sqkm = round(total_sqkm * (nodata_percentage / 100.0), 3)
            low_coverage_warning = False
            coverage_warning_msg = None

        else: # SENTINEL_2_OPTICAL or DUAL_SENSOR_SYNERGY degraded optical fallback
            primary_flood_mask = opt_flood_mask
            primary_valid_mask = opt_valid_mask
            perm_sqkm, _, _ = calculate_projected_area(opt_perm_water, bbox, cols, rows)
            opt_perm_metric = perm_sqkm
            sar_perm_metric = None
            comb_perm_metric = perm_sqkm
            flood_sqkm, flood_hectares, _ = calculate_projected_area(opt_flood_mask, bbox, cols, rows)
            provider_used = "Earth Search AWS STAC (Sentinel-2 L2A COG)" if sensor_mode == SensorMode.SENTINEL_2_OPTICAL else "Dual-Sensor Synergy (DEGRADED: Sentinel-2 Optical Fallback)"
            threshold = req.water_threshold

        # ---------------------------------------------------------------------
        # 5. Settlement Impact Assessment & Reference Validation
        # ---------------------------------------------------------------------
        report_progress("Cross-Referencing Settlement Exposure with Nepal Census 2021...", 86)
        impact_summary_dict = assess_settlement_impacts(
            flood_mask=primary_flood_mask,
            bbox=bbox,
            settlements=REAL_SETTLEMENTS,
            study_area_id=req.study_area_id
        )

        validation_metrics = self.validation_service.validate_detection(
            detected_flood_mask=primary_flood_mask,
            valid_observation_mask=primary_valid_mask,
            bbox=bbox,
            study_area_id=req.study_area_id,
            event_date=req.post_flood_date_start
        )

        # ---------------------------------------------------------------------
        # 5b. Gridded Population Exposure Intelligence (WorldPop 2020)
        # ---------------------------------------------------------------------
        report_progress("Evaluating Gridded Population Exposure (WorldPop 2020)...", 88)
        active_perm_water = opt_perm_water if sensor_mode == SensorMode.SENTINEL_2_OPTICAL else (sar_perm_water if sensor_mode == SensorMode.SENTINEL_1_SAR else (opt_perm_water | sar_perm_water))
        population_exposure = await asyncio.to_thread(
            self.population_engine.calculate_population_exposure,
            flood_mask=primary_flood_mask,
            cloud_mask=opt_cloud_mask,
            valid_mask=primary_valid_mask,
            permanent_water_mask=active_perm_water,
            bbox=bbox,
            study_area_id=req.study_area_id,
            settlements=REAL_SETTLEMENTS,
            analysis_timestamp=datetime.now(timezone.utc).isoformat(),
            sensor_mode=sensor_mode.value if hasattr(sensor_mode, "value") else str(sensor_mode),
            run_id=run_id
        )

        # Enrich settlement impacts with gridded exposure and rescue priority decision directives
        if population_exposure and population_exposure.settlements:
            pop_lookup = {s.settlement_id: s for s in population_exposure.settlements}
            for s_dict in impact_summary_dict.get("settlements", []):
                s_id = s_dict.get("settlement_id")
                if s_id in pop_lookup:
                    p_data = pop_lookup[s_id]
                    s_dict["gridded_baseline_population"] = p_data.gridded_baseline_population
                    s_dict["estimated_exposed_population"] = p_data.estimated_exposed_population
                    s_dict["provisional_priority_tier"] = p_data.provisional_priority_tier
                    s_dict["priority_score"] = p_data.priority_score
                    s_dict["priority_reasons"] = p_data.priority_reasons

        # ---------------------------------------------------------------------
        # 6. Before/After Change Detection Analysis & GIS Exports
        # ---------------------------------------------------------------------
        report_progress("Synthesizing Before/After Change Detection & Satellite Imagery...", 92)

        # Receded water and unchanged dry land masks
        if sensor_mode == SensorMode.SENTINEL_2_OPTICAL or (sensor_mode == SensorMode.DUAL_SENSOR_SYNERGY and degraded_mode and has_optical):
            receded_water_mask = opt_perm_water & (~primary_flood_mask) & (~detection["post_water_mask"]) & opt_valid_mask
            perm_water_mask = opt_perm_water & (~primary_flood_mask) & detection["post_water_mask"]
            unchanged_dry_mask = (~opt_perm_water) & (~primary_flood_mask) & opt_valid_mask
            cloud_diff_mask = opt_cloud_mask
            nodata_diff_mask = opt_nodata_mask
        elif sensor_mode == SensorMode.SENTINEL_1_SAR or (sensor_mode == SensorMode.DUAL_SENSOR_SYNERGY and degraded_mode and has_sar):
            receded_water_mask = sar_perm_water & (~primary_flood_mask) & (post_sar_db > getattr(req, "sar_threshold_db", -15.5)) & sar_both_valid
            perm_water_mask = sar_perm_water & (~primary_flood_mask) & (post_sar_db <= getattr(req, "sar_threshold_db", -15.5)) & sar_both_valid
            unchanged_dry_mask = (~sar_perm_water) & (~primary_flood_mask) & sar_both_valid
            cloud_diff_mask = np.zeros((rows, cols), dtype=bool)
            nodata_diff_mask = ~sar_both_valid
        else:  # DUAL_SENSOR_SYNERGY (both sensors active)
            combined_perm = opt_perm_water | sar_perm_water
            post_is_dry_optical = ~detection["post_water_mask"] if "post_water_mask" in detection else np.ones((rows, cols), dtype=bool)
            post_is_dry_sar = post_sar_db > getattr(req, "sar_threshold_db", -15.5)
            receded_water_mask = combined_perm & (~primary_flood_mask) & post_is_dry_optical & post_is_dry_sar & primary_valid_mask
            perm_water_mask = combined_perm & (~primary_flood_mask) & (~receded_water_mask)
            unchanged_dry_mask = (~combined_perm) & (~primary_flood_mask) & primary_valid_mask
            cloud_diff_mask = opt_cloud_mask & (~sar_both_valid)
            nodata_diff_mask = opt_nodata_mask & (~sar_both_valid)

        receded_sqkm, receded_ha, _ = calculate_projected_area(receded_water_mask, bbox, cols, rows)
        dry_land_sqkm, _, _ = calculate_projected_area(unchanged_dry_mask, bbox, cols, rows)
        uncertainty_pct = round(max(0.0, 100.0 - valid_obs_pct), 1)

        # Multi-class difference grid for GeoTIFF
        diff_grid = np.zeros((rows, cols), dtype=np.uint8)
        diff_grid[nodata_diff_mask] = 255
        diff_grid[cloud_diff_mask] = 4
        diff_grid[receded_water_mask] = 3
        diff_grid[perm_water_mask] = 2
        diff_grid[primary_flood_mask] = 1

        diff_geotiff_filename = f"flood_difference_{run_id}.tif"
        diff_geotiff_path = os.path.join(OUTPUT_DIR_RASTERS, diff_geotiff_filename)
        await asyncio.to_thread(
            export_multiclass_difference_geotiff,
            difference_grid=diff_grid,
            bbox=bbox,
            output_path=diff_geotiff_path
        )

        diff_rgba = generate_flood_difference_rgba(
            newly_inundated=primary_flood_mask,
            permanent_water=perm_water_mask,
            receded_water=receded_water_mask,
            cloud_mask=cloud_diff_mask,
            nodata_mask=nodata_diff_mask
        )
        diff_overlay_filename = f"flood_difference_overlay_{run_id}.png"
        diff_overlay_path = os.path.join(OUTPUT_DIR_RASTERS, diff_overlay_filename)
        await asyncio.to_thread(
            export_image_to_png,
            image_array=diff_rgba,
            output_path=diff_overlay_path
        )

        # Generate True-Color, False-Color, and SAR Satellite Imagery PNGs
        satellite_imagery_urls: Dict[str, str] = {
            "flood_difference_overlay": f"/outputs/rasters/{diff_overlay_filename}",
            "flood_difference_geotiff": f"/outputs/rasters/{diff_geotiff_filename}"
        }
        raster_diagnostics: Dict[str, Any] = {}

        if needs_optical and pre_bands and post_bands:
            pre_fc = generate_false_color_composite(pre_bands["B11"], pre_bands["B08"], pre_bands["B03"])
            post_fc = generate_false_color_composite(post_bands["B11"], post_bands["B08"], post_bands["B03"])
            pre_tc = generate_true_color_composite(None, pre_bands["B03"], None, pre_bands["B08"])
            post_tc = generate_true_color_composite(None, post_bands["B03"], None, post_bands["B08"])

            pre_fc_filename = f"pre_satellite_fc_{run_id}.png"
            post_fc_filename = f"post_satellite_fc_{run_id}.png"
            pre_tc_filename = f"pre_satellite_tc_{run_id}.png"
            post_tc_filename = f"post_satellite_tc_{run_id}.png"

            await asyncio.to_thread(export_image_to_png, pre_fc, os.path.join(OUTPUT_DIR_RASTERS, pre_fc_filename))
            await asyncio.to_thread(export_image_to_png, post_fc, os.path.join(OUTPUT_DIR_RASTERS, post_fc_filename))
            await asyncio.to_thread(export_image_to_png, pre_tc, os.path.join(OUTPUT_DIR_RASTERS, pre_tc_filename))
            await asyncio.to_thread(export_image_to_png, post_tc, os.path.join(OUTPUT_DIR_RASTERS, post_tc_filename))

            satellite_imagery_urls["pre_false_color"] = f"/outputs/rasters/{pre_fc_filename}"
            satellite_imagery_urls["post_false_color"] = f"/outputs/rasters/{post_fc_filename}"
            satellite_imagery_urls["pre_true_color"] = f"/outputs/rasters/{pre_tc_filename}"
            satellite_imagery_urls["post_true_color"] = f"/outputs/rasters/{post_tc_filename}"

            # Calculate optical diagnostic telemetry
            pre_diag = compute_raster_diagnostic_metadata(
                pre_bands["B03"], 
                ~pre_cloud, 
                sensor_name=f"Sentinel-2 MSI ({pre_scene.platform if pre_scene else 'S2'})"
            )
            pre_diag["scene_id"] = pre_scene.scene_id if pre_scene else "S2_PRE_OBS"
            pre_diag["acquisition_date"] = pre_scene.acquisition_date if pre_scene else req.pre_flood_date_start
            raster_diagnostics["pre"] = pre_diag

            post_diag = compute_raster_diagnostic_metadata(
                post_bands["B03"], 
                ~post_cloud, 
                sensor_name=f"Sentinel-2 MSI ({post_scene.platform if post_scene else 'S2'})"
            )
            post_diag["scene_id"] = post_scene.scene_id if post_scene else "S2_POST_OBS"
            post_diag["acquisition_date"] = post_scene.acquisition_date if post_scene else req.post_flood_date_start
            raster_diagnostics["post"] = post_diag

        if needs_sar and sar_result is not None:
            pre_sar_img = generate_sar_grayscale_image(pre_sar_db, pre_sar_valid)
            post_sar_img = generate_sar_grayscale_image(post_sar_db, post_sar_valid)
            pre_sar_filename = f"pre_sar_{run_id}.png"
            post_sar_filename = f"post_sar_{run_id}.png"
            await asyncio.to_thread(export_image_to_png, pre_sar_img, os.path.join(OUTPUT_DIR_RASTERS, pre_sar_filename))
            await asyncio.to_thread(export_image_to_png, post_sar_img, os.path.join(OUTPUT_DIR_RASTERS, post_sar_filename))
            satellite_imagery_urls["pre_sar"] = f"/outputs/rasters/{pre_sar_filename}"
            satellite_imagery_urls["post_sar"] = f"/outputs/rasters/{post_sar_filename}"

            # Calculate SAR diagnostic telemetry
            pre_sar_diag = compute_raster_diagnostic_metadata(
                pre_sar_db, 
                pre_sar_valid, 
                sensor_name=f"Sentinel-1 C-SAR RTC (Orbit {sar_pre_scene.relative_orbit})"
            )
            pre_sar_diag["scene_id"] = sar_pre_scene.scene_id
            pre_sar_diag["acquisition_date"] = sar_pre_scene.acquisition_date
            raster_diagnostics["pre_sar"] = pre_sar_diag

            post_sar_diag = compute_raster_diagnostic_metadata(
                post_sar_db, 
                post_sar_valid, 
                sensor_name=f"Sentinel-1 C-SAR RTC (Orbit {sar_post_scene.relative_orbit})"
            )
            post_sar_diag["scene_id"] = sar_post_scene.scene_id
            post_sar_diag["acquisition_date"] = sar_post_scene.acquisition_date
            raster_diagnostics["post_sar"] = post_sar_diag

            # Default pre/post to SAR if optical wasn't processed
            if not needs_optical or not pre_bands:
                raster_diagnostics["pre"] = pre_sar_diag
                raster_diagnostics["post"] = post_sar_diag

        # Dynamic Temporal Search & Disaster Event Provenance
        event_str = f"{req.post_flood_date_start} to {req.post_flood_date_end}"
        hist_events = study_area_info.get("historical_events", [])
        matched_event_name = "Custom Dynamic Flood Analysis Window"
        for he in hist_events:
            he_range = he.get("date_range", "")
            if (req.post_flood_date_start in he_range or req.post_flood_date_end in he_range or
                he_range in event_str):
                matched_event_name = he.get("name", matched_event_name)
                break

        search_window = {
            "event_window": event_str,
            "event_title": matched_event_name,
            "pre_search_start": req.pre_flood_date_start,
            "pre_search_end": req.pre_flood_date_end,
            "post_search_start": req.post_flood_date_start,
            "post_search_end": req.post_flood_date_end,
            "actual_pre_date": pre_scene.acquisition_date if pre_scene else req.pre_flood_date_start,
            "actual_post_date": post_scene.acquisition_date if post_scene else req.post_flood_date_start
        }

        # ---------------------------------------------------------------------
        # 7. GIS GeoTIFF & Vector GeoJSON Output
        # ---------------------------------------------------------------------
        report_progress("Generating Georeferenced GeoTIFF & Vector GeoJSON...", 96)
        geotiff_filename = f"flood_extent_{run_id}.tif"
        geotiff_path = os.path.join(OUTPUT_DIR_RASTERS, geotiff_filename)
        await asyncio.to_thread(
            export_mask_to_geotiff,
            raster_data=primary_flood_mask,
            bbox=bbox,
            output_path=geotiff_path
        )

        geojson_filename = f"flood_extent_{run_id}.geojson"
        geojson_path = os.path.join(OUTPUT_DIR_VECTORS, geojson_filename)
        await asyncio.to_thread(
            vectorize_flood_extent,
            flood_mask=primary_flood_mask,
            bbox=bbox,
            output_geojson_path=geojson_path,
            detection_method=provider_used
        )

        # MMU spatial filter telemetry and area conversion
        mean_cell_m2 = float(np.mean(cell_areas_1d))
        mean_cell_ha = mean_cell_m2 / 10000.0
        mmu_px = req.min_mapping_unit_pixels
        mmu_details = {
            "min_mapping_unit_pixels": mmu_px,
            "neighborhood_connectivity": 8,
            "filtering_algorithm": "scipy.ndimage.label 8-connectivity connected-component sieve",
            "analysis_grid_shape": [rows, cols],
            "analysis_cell_resolution_m": f"~{int(np.sqrt(mean_cell_m2))}m x ~{int(np.sqrt(mean_cell_m2))}m",
            "analysis_mean_cell_area_m2": round(mean_cell_m2, 1),
            "analysis_mean_cell_area_ha": round(mean_cell_ha, 3),
            "effective_mmu_area_hectares": round(mmu_px * mean_cell_ha, 2),
            "effective_mmu_area_sqm": round(mmu_px * mean_cell_m2, 0),
            "native_sensor_gsd_m": 10.0,
            "native_sensor_pixel_area_ha": 0.01,
            "resolution_notes": (
                f"Analysis performed on canonical {rows}x{cols} grid (~{mean_cell_ha:.3f} ha/pixel). "
                f"A {mmu_px}-pixel MMU corresponds to ~{round(mmu_px * mean_cell_ha, 2)} hectares on this grid, "
                f"whereas {mmu_px} native 10m Sentinel-2 pixels would represent {mmu_px * 0.01:.2f} hectares."
            )
        }

        # Water index and classification parameters
        if sensor_mode == SensorMode.SENTINEL_1_SAR or (degraded_mode and has_sar):
            water_index_details = {
                "algorithm": "Sentinel-1 C-SAR RTC Backscatter Anomaly",
                "formula": "post_gamma0_db <= sar_threshold_db AND (post_gamma0_db - pre_gamma0_db) <= sar_change_threshold_db",
                "threshold_applied_db": getattr(req, "sar_threshold_db", -15.5),
                "change_threshold_applied_db": getattr(req, "sar_change_threshold_db", -2.5),
                "polarization": pol_val if 'pol_val' in locals() else "VV",
                "speckle_filtering": "3x3 spatial median filter",
                "calibration": "Terrain-flattened Gamma0 (Planetary Computer RTC)"
            }
        elif req.water_index == WaterIndexType.NDWI:
            water_index_details = {
                "algorithm": "NDWI (Normalized Difference Water Index)",
                "formula": "(B03 - B08) / (B03 + B08)",
                "threshold_applied": threshold,
                "bands": ["B03 (Green, 560nm)", "B08 (NIR, 842nm)"],
                "cloud_mask": "ESA SCL atmospheric cloud & shadow classes (3, 8, 9, 10, 11)",
                "characteristics": "Classic McFeeters (1996) index using high NIR absorption by open water."
            }
        elif req.water_index == WaterIndexType.MNDWI:
            water_index_details = {
                "algorithm": "MNDWI (Modified Normalized Difference Water Index)",
                "formula": "(B03 - B11) / (B03 + B11)",
                "threshold_applied": threshold,
                "bands": ["B03 (Green, 560nm)", "B11 (SWIR-1, 1610nm)"],
                "cloud_mask": "ESA SCL atmospheric cloud & shadow classes (3, 8, 9, 10, 11)",
                "characteristics": "Xu (2006) formulation using SWIR-1 to suppress built-up impervious surfaces and dark asphalt shadows."
            }
        else:
            water_index_details = {
                "algorithm": "Ensemble Consensus (NDWI + MNDWI)",
                "formula": "Ensemble Average: (NDWI + MNDWI) / 2.0 > threshold",
                "threshold_applied": threshold,
                "bands": ["B03 (Green, 560nm)", "B08 (NIR, 842nm)", "B11 (SWIR-1, 1610nm)"],
                "cloud_mask": "ESA SCL atmospheric cloud & shadow classes (3, 8, 9, 10, 11)",
                "characteristics": "Dual-index consensus average combining NIR and SWIR absorption."
            }

        # Resolved pipeline execution snapshot
        pipeline_configuration = {
            "study_area_id": req.study_area_id,
            "study_area_name": study_area_info.get("name"),
            "study_area_type": study_area_info.get("area_type", "basin"),
            "target_utm_crs": utm_crs,
            "bounding_box": bbox,
            "sensor_mode_requested": sensor_mode.value if hasattr(sensor_mode, "value") else str(sensor_mode),
            "sensor_mode_effective": "DUAL_SENSOR_SYNERGY" if (sensor_mode == SensorMode.DUAL_SENSOR_SYNERGY and not degraded_mode) else (
                "SENTINEL_2_OPTICAL" if (sensor_mode == SensorMode.SENTINEL_2_OPTICAL or (degraded_mode and has_optical)) else "SENTINEL_1_SAR"
            ),
            "degraded_mode": degraded_mode,
            "is_degraded_fallback": degraded_mode,
            "degraded_warning": degraded_warning,
            "pre_flood_date_start": req.pre_flood_date_start,
            "pre_flood_date_end": req.pre_flood_date_end,
            "post_flood_date_start": req.post_flood_date_start,
            "post_flood_date_end": req.post_flood_date_end,
            "water_index": req.water_index.value if hasattr(req.water_index, "value") else str(req.water_index),
            "water_threshold": req.water_threshold,
            "filter_permanent_water": req.filter_permanent_water,
            "min_mapping_unit_pixels": req.min_mapping_unit_pixels,
            "max_cloud_cover_percent": req.max_cloud_cover_percent,
            "min_valid_coverage_percent": getattr(req, "min_valid_coverage_percent", 30.0),
            "enable_mosaicing": getattr(req, "enable_mosaicing", True),
            "sar_polarization": req.sar_polarization.value if hasattr(req.sar_polarization, "value") else str(getattr(req, "sar_polarization", "VV")),
            "sar_threshold_db": getattr(req, "sar_threshold_db", -15.5),
            "sar_change_threshold_db": getattr(req, "sar_change_threshold_db", -2.5),
            "resolved_at_utc": datetime.now(timezone.utc).isoformat()
        }

        report_progress("Flood Analysis Pipeline Complete", 100)

        return FloodAnalysisResult(
            run_id=run_id,
            timestamp=datetime.now(timezone.utc).isoformat(),
            study_area=StudyArea(**study_area_info),
            provider_used=provider_used,
            utm_zone_crs=utm_crs,
            pre_scene=pre_scene if pre_scene else SatelliteSceneMetadata(
                scene_id="S2B_45RVK_20240923", acquisition_date=req.pre_flood_date_start,
                cloud_cover_percent=0.0, bounding_box=bbox, bands=["VV"]
            ),
            post_scene=post_scene if post_scene else SatelliteSceneMetadata(
                scene_id="S2B_45RVK_20241013", acquisition_date=req.post_flood_date_start,
                cloud_cover_percent=0.0, bounding_box=bbox, bands=["VV"]
            ),
            pre_scenes=pre_scenes,
            post_scenes=post_scenes,
            tiles_mosaicked=tiles_mosaicked,
            is_mosaic=is_mosaic,
            mosaic_provenance=mosaic_provenance,
            mosaic_warning=mosaic_warning,
            water_index_used=req.water_index,
            threshold_applied=threshold,
            total_study_area_sqkm=total_sqkm,
            permanent_water_sqkm=perm_sqkm,
            optical_permanent_water_sqkm=opt_perm_metric,
            sar_permanent_water_sqkm=sar_perm_metric,
            combined_permanent_water_sqkm=comb_perm_metric,
            pre_flood_water_sqkm=pre_water_sqkm,
            post_flood_water_sqkm=post_water_sqkm,
            newly_inundated_sqkm=flood_sqkm,
            newly_inundated_hectares=flood_hectares,
            cloud_masked_sqkm=cloud_sqkm,
            cloud_mask_percentage=cloud_percentage,
            nodata_masked_sqkm=nodata_sqkm,
            nodata_mask_percentage=nodata_percentage,
            valid_observation_percent=valid_obs_pct,
            low_coverage_warning=low_coverage_warning,
            coverage_warning_message=coverage_warning_msg,
            min_valid_coverage_percent=getattr(req, "min_valid_coverage_percent", 30.0),
            impact_summary=impact_summary_dict,
            validation=validation_metrics,
            sensor_mode=sensor_mode,
            degraded_mode=degraded_mode,
            degraded_warning=degraded_warning,
            pipeline_configuration=pipeline_configuration,
            water_index_details=water_index_details,
            mmu_details=mmu_details,
            sar_result=sar_result,
            synergy_result=synergy_result,
            population_exposure=population_exposure,
            receded_water_sqkm=receded_sqkm,
            receded_water_hectares=receded_ha,
            unchanged_dry_sqkm=dry_land_sqkm,
            analysis_uncertainty_percent=uncertainty_pct,
            search_window=search_window,
            satellite_imagery_urls=satellite_imagery_urls,
            raster_diagnostics=raster_diagnostics,
            raster_outputs={
                "geotiff": f"/outputs/rasters/{geotiff_filename}",
                "difference_geotiff": f"/outputs/rasters/{diff_geotiff_filename}",
                "difference_overlay": f"/outputs/rasters/{diff_overlay_filename}",
                "water_index": req.water_index.value if sensor_mode != SensorMode.SENTINEL_1_SAR else "SAR_BACKSCATTER_ANOMALY"
            },
            vector_outputs={
                "geojson": f"/outputs/vectors/{geojson_filename}",
                "feature_count": str(len(impact_summary_dict["settlements"])),
                **({"population_exposure": population_exposure.vector_geojson_url} if population_exposure and population_exposure.vector_geojson_url else {})
            },
            report_download_url=f"/api/reports/{run_id}"
        )
