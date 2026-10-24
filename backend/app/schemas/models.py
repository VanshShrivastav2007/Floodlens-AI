from pydantic import BaseModel, Field, model_validator
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from datetime import datetime

class WaterIndexType(str, Enum):
    NDWI = "NDWI"          # (Green - NIR) / (Green + NIR)
    MNDWI = "MNDWI"        # (Green - SWIR) / (Green + SWIR)
    COMBINED = "COMBINED"   # Ensemble consensus of NDWI and MNDWI

class DataSourceType(str, Enum):
    SENTINEL_2_L2A = "Sentinel-2 L2A (Harmonized)"
    STAC_ELEMENT84 = "Earth Search AWS STAC (Sentinel-2)"
    PLANETARY_COMPUTER = "Microsoft Planetary Computer STAC"
    EARTH_ENGINE = "Google Earth Engine (COPERNICUS/S2_SR_HARMONIZED)"

class SatelliteProvider(str, Enum):
    AUTO = "auto"
    STAC = "stac"
    EARTH_ENGINE = "earth_engine"

class SensorMode(str, Enum):
    SENTINEL_2_OPTICAL = "SENTINEL_2_OPTICAL"
    SENTINEL_1_SAR = "SENTINEL_1_SAR"
    DUAL_SENSOR_SYNERGY = "DUAL_SENSOR_SYNERGY"

class SARPolarization(str, Enum):
    VV = "VV"
    VH = "VH"
    DUAL = "VV+VH"

class SARSceneMetadata(BaseModel):
    scene_id: str
    platform: str = "Sentinel-1A"
    instrument: str = "C-SAR"
    product_type: str = "RTC"  # Radiometric Terrain Corrected
    polarization: str = "VV"
    acquisition_date: str
    orbit_direction: str = "ascending"
    relative_orbit: int = 85
    spatial_resolution_m: float = 10.0
    bounding_box: List[float]
    backscatter_quantity: str = "gamma0_linear_power"
    mean_backscatter_db: Optional[float] = None
    asset_urls: Dict[str, str] = {}
    provider: str = "Microsoft Planetary Computer STAC (sentinel-1-rtc)"

class SARAnalysisResult(BaseModel):
    pre_scene: SARSceneMetadata
    post_scene: SARSceneMetadata
    polarization: str = "VV"
    threshold_db: float = -15.5
    change_threshold_db: float = -2.5
    valid_sar_coverage_percent: float
    valid_sar_sqkm: float
    sar_footprint_coverage_percent: float = 100.0
    sar_nodata_sqkm: float = 0.0
    sar_nodata_coverage_percent: float = 0.0
    sar_newly_inundated_sqkm: float
    sar_newly_inundated_hectares: float
    sar_permanent_water_sqkm: float
    sar_mean_backscatter_change_db: float
    geotiff_path: Optional[str] = None
    processing_steps: List[str] = [
        "Planetary Computer RTC SAS token authorization",
        "Radiometric calibration to gamma0 terrain-flattened backscatter",
        "Speckle suppression via 3x3 spatial median filter",
        "Linear power to decibel (dB) transformation",
        "Temporal backscatter anomaly detection (delta_dB <= -2.5 dB)",
        "Specular reflection thresholding (post_dB <= -15.5 dB)",
        "Pre-event permanent water channel subtraction",
        "Minimum mapping unit connected-component filtering"
    ]
    uncertainty_notice: str = "SAR radar penetration is all-weather / cloud-independent, but may experience specular reflection over flat dry sand bars or radar shadow on steep hill slopes."

class DualSensorSynergyResult(BaseModel):
    optical_flood_sqkm: float
    sar_flood_sqkm: float
    # 6 MECE Flood Union Partitions (Strict Sum == total_multi_sensor_flood_sqkm)
    consensus_confirmed_flood_sqkm: float       # P1: F_opt ∩ F_sar
    cloud_pierced_sar_flood_sqkm: float         # P2: F_sar ∩ C_opt
    sar_flood_optical_nodata_sqkm: float = 0.0  # P3: F_sar ∩ ND_opt
    sar_discordant_flood_sqkm: float = 0.0      # P4: F_sar ∩ D_opt (SAR wet, Optical dry)
    optical_outside_sar_swath_sqkm: float = 0.0 # P5: F_opt ∩ ND_sar (Optical wet, SAR outside swath)
    optical_discordant_flood_sqkm: float = 0.0  # P6: F_opt ∩ D_sar (Optical wet, SAR dry)
    # Backward compatibility aliases
    cloud_pierced_flood_sqkm: float             # Identical to cloud_pierced_sar_flood_sqkm
    optical_only_flood_sqkm: float              # Identical to optical_outside_sar_swath_sqkm
    # Conservation verification
    total_multi_sensor_flood_sqkm: float
    sum_flood_partitions_sqkm: float = 0.0
    flood_union_conservation_verified: bool = True
    flood_conservation_residual_sqkm: float = 0.0
    sensor_agreement_percent: float
    # Full Domain Spatial Conservation (Strict Sum == domain_total_sqkm)
    domain_total_sqkm: float = 0.0
    domain_permanent_water_sqkm: float = 0.0
    optical_permanent_water_sqkm: float = 0.0
    sar_permanent_water_sqkm: float = 0.0
    combined_permanent_water_union_sqkm: float = 0.0
    permanent_water_conservation_verified: bool = True
    permanent_water_inclusion_exclusion_residual_sqkm: float = 0.0
    domain_both_dry_sqkm: float = 0.0
    domain_optical_cloud_sar_dry_sqkm: float = 0.0
    domain_optical_cloud_sar_nodata_sqkm: float = 0.0
    domain_optical_dry_sar_nodata_sqkm: float = 0.0
    domain_optical_nodata_sar_dry_sqkm: float = 0.0
    domain_both_nodata_sqkm: float = 0.0
    full_grid_conservation_verified: bool = True
    full_grid_residual_sqkm: float = 0.0
    description: str

class ImpactLevel(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    MODERATE = "Moderate"
    MONITORING = "Monitoring"
    SAFE = "Safe"

class HistoricalEvent(BaseModel):
    name: str
    date_range: str
    affected_population: int
    notes: str

class StudyArea(BaseModel):
    id: str
    name: str
    district: str
    province: str
    description: str
    bbox: List[float]  # [min_lon, min_lat, max_lon, max_lat]
    center: List[float]
    default_zoom: float
    historical_events: List[HistoricalEvent] = []
    polygon: Optional[Dict[str, Any]] = None
    area_type: str = "basin"  # "basin", "district", "region"
    area_sqkm: Optional[float] = None
    terai_category: Optional[str] = "outer_terai"
    pcode: Optional[str] = None
    districts_count: Optional[int] = None
    source_dataset: Optional[str] = None
    license: Optional[str] = None
    settlement_coverage_status: Optional[str] = "verified"

class SettlementRecord(BaseModel):
    id: str
    name: str
    local_name: Optional[str] = None
    study_area: Optional[str] = None
    district: str
    district_pcode: Optional[str] = None
    municipality: Optional[str] = None
    municipality_pcode: Optional[str] = None
    coordinates: List[float]
    elevation_m: Optional[float] = None
    population: Optional[int] = None
    household_count: Optional[int] = None
    critical_infrastructure: List[str] = []
    flood_vulnerability: Optional[str] = None
    river_proximity_m: Optional[float] = None
    settlement_type: str = "village"
    geometry_type: str = "Point"
    source_dataset: str = "OpenStreetMap / HOTOSM"
    source_id: Optional[str] = None
    retrieval_date: str = "2026-10-24"
    verification_status: str = "osm_verified_populated_place"
    is_legacy_fixture: bool = False

class GeographyProvenanceResponse(BaseModel):
    status: str
    administrative_manifest: Dict[str, Any]
    settlements_manifest: Dict[str, Any]
    total_districts: int
    total_settlements: int
    coverage_warnings: List[str] = []

class SatelliteSceneMetadata(BaseModel):
    scene_id: str
    platform: str = "Sentinel-2B"
    instrument: str = "MSI Level-2A"
    acquisition_date: str
    cloud_cover_percent: float
    spatial_resolution_m: float = 10.0
    bounding_box: List[float]
    bands: List[str]
    source: DataSourceType = DataSourceType.STAC_ELEMENT84
    sun_elevation: Optional[float] = 62.4
    data_quality_score: float = 98.2
    preview_url: Optional[str] = None
    native_crs: Optional[Union[str, int]] = "EPSG:32645"
    asset_urls: Dict[str, str] = {}

class AnalysisRunRequest(BaseModel):
    study_area_id: str = Field(default="koshi_basin", description="Study area or district identifier")
    pre_flood_date_start: str = Field(default="2024-09-01", description="Baseline start date (YYYY-MM-DD)")
    pre_flood_date_end: str = Field(default="2024-09-25", description="Baseline end date (YYYY-MM-DD)")
    post_flood_date_start: str = Field(default="2024-09-26", description="Post-event observation start date (YYYY-MM-DD)")
    post_flood_date_end: str = Field(default="2024-10-15", description="Post-event observation end date (YYYY-MM-DD)")
    max_cloud_cover_percent: float = Field(default=50.0, ge=0.0, le=100.0, description="Maximum scene-level cloud cover tolerance (0-100%)")
    water_index: WaterIndexType = Field(default=WaterIndexType.MNDWI, description="Optical water index algorithm")
    water_threshold: float = Field(default=0.05, ge=-0.10, le=0.25, description="Optical water index classification threshold (-0.10 to +0.25)")
    filter_permanent_water: bool = Field(default=True, description="Whether to subtract pre-event baseline water bodies to isolate new inundation")
    min_mapping_unit_pixels: int = Field(default=5, ge=1, le=20, description="Minimum mapping unit connected-component size in pixels (1-20)")
    min_valid_coverage_percent: float = Field(default=30.0, ge=5.0, le=100.0, description="Minimum valid observation domain coverage before warning (5-100%)")
    enable_mosaicing: bool = Field(default=True, description="Enable multi-granule Sentinel-2 mosaicing across adjacent MGRS tiles")
    provider: SatelliteProvider = SatelliteProvider.AUTO
    data_source: DataSourceType = DataSourceType.STAC_ELEMENT84
    sensor_mode: SensorMode = Field(default=SensorMode.SENTINEL_2_OPTICAL, description="Sensor architecture: Optical, SAR, or Dual-Sensor Synergy")
    sar_polarization: SARPolarization = Field(default=SARPolarization.VV, description="Sentinel-1 SAR polarization channel")
    sar_threshold_db: float = Field(default=-15.5, ge=-30.0, le=0.0, description="SAR specular backscatter threshold in dB")
    sar_change_threshold_db: float = Field(default=-2.5, ge=-15.0, le=0.0, description="SAR temporal backscatter drop threshold in dB")

    @model_validator(mode="after")
    def validate_temporal_ordering(self) -> "AnalysisRunRequest":
        date_fields = [
            ("pre_flood_date_start", self.pre_flood_date_start),
            ("pre_flood_date_end", self.pre_flood_date_end),
            ("post_flood_date_start", self.post_flood_date_start),
            ("post_flood_date_end", self.post_flood_date_end),
        ]
        parsed_dates = {}
        for name, val in date_fields:
            try:
                parsed_dates[name] = datetime.strptime(val, "%Y-%m-%d").date()
            except Exception:
                raise ValueError(f"Invalid date format for '{name}': '{val}'. Must be YYYY-MM-DD.")

        if parsed_dates["pre_flood_date_start"] > parsed_dates["pre_flood_date_end"]:
            raise ValueError(
                f"Invalid baseline window: pre_flood_date_start ({self.pre_flood_date_start}) "
                f"must be <= pre_flood_date_end ({self.pre_flood_date_end})."
            )
        if parsed_dates["post_flood_date_start"] > parsed_dates["post_flood_date_end"]:
            raise ValueError(
                f"Invalid observation window: post_flood_date_start ({self.post_flood_date_start}) "
                f"must be <= post_flood_date_end ({self.post_flood_date_end})."
            )
        if parsed_dates["pre_flood_date_start"] > parsed_dates["post_flood_date_start"]:
            raise ValueError(
                f"Invalid temporal sequence: pre-flood baseline start ({self.pre_flood_date_start}) "
                f"cannot be later than post-flood observation start ({self.post_flood_date_start})."
            )
        return self

class SettlementImpact(BaseModel):
    settlement_id: str
    name: str
    local_name: str
    district: str
    municipality: str
    coordinates: List[float]
    elevation_m: float
    population: int
    household_count: int
    impact_level: ImpactLevel
    flooded_area_near_sqkm: float
    distance_to_flood_m: float
    critical_infrastructure_at_risk: List[str]
    evacuation_priority: int
    exposure_percentage: float
    recommended_action: str
    exposure_proxy_type: str = "Proximity Buffer (UTM Metric)"
    gridded_baseline_population: Optional[float] = None
    estimated_exposed_population: Optional[float] = None
    provisional_priority_tier: Optional[str] = None
    priority_score: Optional[float] = None
    priority_reasons: List[str] = []

class PopulationDatasetMetadata(BaseModel):
    dataset_name: str = "WorldPop 2020 Building Settlement Grid Masked (BSGM) Constrained"
    source_url: str = "https://data.worldpop.org/GIS/Population/Global_2000_2020_Constrained/2020/BSGM/NPL/npl_ppp_2020_constrained.tif"
    citation: str = "WorldPop (www.worldpop.org - School of Geography and Environmental Science, University of Southampton; Department of Geography and Geosciences, University of Louisville; Departement de Geographie, Universite de Namur) and Center for International Earth Science Information Network (CIESIN), Columbia University (2020). Global High Resolution Population-Denominators Project - Funded by The Bill and Melinda Gates Foundation."
    license: str = "Creative Commons Attribution 4.0 International (CC BY 4.0)"
    reference_year: int = 2020
    native_spatial_resolution_m: float = 100.0
    units: str = "Estimated Persons per Grid Cell (Dasymetric Count)"
    crs: str = "EPSG:4326"
    availability_status: str = "AVAILABLE"  # or "UNAVAILABLE_DATASET"

class SettlementPopulationExposure(BaseModel):
    settlement_id: str
    name: str
    local_name: str
    district: str
    municipality: str
    coordinates: List[float]
    elevation_m: float
    census_baseline_population: int
    gridded_baseline_population: float
    estimated_exposed_population: float
    census_scaled_exposed_population: int
    exposure_percentage: float
    direct_inundation_detected: bool
    distance_to_flood_m: float
    flooded_area_near_sqkm: float
    critical_infrastructure_at_risk: List[str] = []
    river_proximity_m: float
    flood_hazard_severity: str
    provisional_priority_rank: int
    provisional_priority_tier: str
    priority_score: float
    priority_reasons: List[str] = []
    operational_status: str = "PROVISIONAL_DECISION_SUPPORT"
    recommended_action: str
    uncertainty_notes: str

class PopulationExposureResult(BaseModel):
    study_area_id: str
    timestamp: str
    population_metadata: PopulationDatasetMetadata
    total_domain_resident_population: float
    total_domain_exposed_population: float
    overall_exposure_percentage: float
    cloud_masked_population: float
    cloud_pierced_exposed_population: float
    settlements: List[SettlementPopulationExposure] = []
    vector_geojson_url: Optional[str] = None
    double_counting_prevention_method: str = "Pixel-level unique lat/lon aggregation and Voronoi-partitioned non-overlapping settlement catchment allocation"
    uncertainty_disclaimer: str

class SettlementImpactSummary(BaseModel):
    total_settlements_analyzed: int
    critical_count: int
    high_count: int
    moderate_count: int
    monitoring_count: int
    safe_count: int
    total_exposed_population: int
    critical_infrastructure_count: int
    settlements: List[SettlementImpact]
    provenance: str = "Estimated Population Exposure Proxy: Model-derived via 1.5km geodesic proximity buffer around detected floodwaters using Nepal CBS 2021 municipal census populations (estimates potential population in proximity to flood hazard, not confirmed casualties or evacuees)"

class ValidationMetrics(BaseModel):
    reference_dataset: Optional[str] = None
    reference_date: Optional[str] = None
    true_positives_sqkm: Optional[float] = None
    false_positives_sqkm: Optional[float] = None
    false_negatives_sqkm: Optional[float] = None
    true_negatives_sqkm: Optional[float] = None
    precision: Optional[float] = None
    recall: Optional[float] = None
    f1_score: Optional[float] = None
    iou_jaccard: Optional[float] = None
    overall_accuracy: Optional[float] = None
    validation_status: str = "UNAVAILABLE_REFERENCE_DATA"
    notes: str

class RasterDiagnosticInfo(BaseModel):
    dimensions: str
    total_pixels: int
    valid_pixels: int
    valid_percentage: float
    nodata_percentage: float
    min_value: float
    max_value: float
    mean_value: float
    sensor: str
    scene_id: Optional[str] = None
    acquisition_date: Optional[str] = None

class FloodAnalysisResult(BaseModel):
    run_id: str
    timestamp: str
    study_area: StudyArea
    provider_used: str
    utm_zone_crs: str
    native_spatial_resolution_m: float = 10.0
    effective_grid_resolution_desc: str = "400 x 500 canonical grid (~120m x 139m / 1.655 ha per cell in EPSG:4326)"
    pre_scene: SatelliteSceneMetadata
    post_scene: SatelliteSceneMetadata
    pre_scenes: List[SatelliteSceneMetadata] = []
    post_scenes: List[SatelliteSceneMetadata] = []
    tiles_mosaicked: List[str] = []
    is_mosaic: bool = False
    mosaic_provenance: Optional[Dict[str, Any]] = None
    mosaic_warning: Optional[str] = None
    water_index_used: WaterIndexType
    threshold_applied: float
    total_study_area_sqkm: float
    permanent_water_sqkm: float
    optical_permanent_water_sqkm: Optional[float] = None
    sar_permanent_water_sqkm: Optional[float] = None
    combined_permanent_water_sqkm: Optional[float] = None
    pre_flood_water_sqkm: float
    post_flood_water_sqkm: float
    newly_inundated_sqkm: float
    newly_inundated_hectares: float
    cloud_masked_sqkm: float
    cloud_mask_percentage: float
    nodata_masked_sqkm: float = 0.0
    nodata_mask_percentage: float = 0.0
    valid_observation_percent: float
    low_coverage_warning: bool = False
    coverage_warning_message: Optional[str] = None
    min_valid_coverage_percent: float = 30.0
    impact_summary: SettlementImpactSummary
    validation: ValidationMetrics
    sensor_mode: SensorMode = SensorMode.SENTINEL_2_OPTICAL
    degraded_mode: bool = Field(
        default=False,
        description="True when multi-sensor synergy falls back to single-sensor due to sensor unavailability"
    )
    degraded_warning: Optional[str] = Field(
        default=None,
        description="Detailed explanation of sensor unavailability and fallback limitations"
    )
    pipeline_configuration: Dict[str, Any] = Field(
        default_factory=dict,
        description="Resolved execution-time parameters used to generate this analysis"
    )
    water_index_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Mathematical formulation, bands, thresholds, and consensus combination rules applied"
    )
    mmu_details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Spatial filtering parameters, raster cell dimensions, and area metric conversions"
    )
    sar_result: Optional[SARAnalysisResult] = None
    synergy_result: Optional[DualSensorSynergyResult] = None
    population_exposure: Optional[PopulationExposureResult] = None
    receded_water_sqkm: float = 0.0
    receded_water_hectares: float = 0.0
    unchanged_dry_sqkm: float = 0.0
    analysis_uncertainty_percent: float = 0.0
    search_window: Dict[str, str] = {}
    satellite_imagery_urls: Dict[str, str] = {}
    raster_diagnostics: Dict[str, RasterDiagnosticInfo] = {}
    raster_outputs: Dict[str, str] = {}
    vector_outputs: Dict[str, str] = {}
    report_download_url: Optional[str] = None

class JobStatusType(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class AnalysisJobProgress(BaseModel):
    run_id: str
    status: JobStatusType
    stage: str
    progress_percent: int
    started_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None
    result: Optional[FloodAnalysisResult] = None
