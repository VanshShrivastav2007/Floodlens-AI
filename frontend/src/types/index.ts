export type WaterIndexType = 'NDWI' | 'MNDWI' | 'COMBINED';

export type DataSourceType = 
  | 'Sentinel-2 L2A (Harmonized)'
  | 'Earth Search AWS STAC (Sentinel-2)'
  | 'Google Earth Engine (COPERNICUS/S2_SR_HARMONIZED)'
  | 'Pre-loaded Calibrated S2 Terai Scenes';

export type ImpactLevel = 'Critical' | 'High' | 'Moderate' | 'Monitoring' | 'Safe';

export interface HistoricalEvent {
  name: string;
  date_range: string;
  affected_population: number;
  notes: string;
}

export interface StudyArea {
  id: string;
  name: string;
  district: string;
  province: string;
  description: string;
  bbox: [number, number, number, number]; // [min_lon, min_lat, max_lon, max_lat]
  center: [number, number];
  default_zoom: number;
  historical_events: HistoricalEvent[];
  polygon?: any;
  area_type?: 'basin' | 'district' | 'region';
  terai_category?: string;
  pcode?: string;
  area_sqkm?: number;
  districts_count?: number;
  source_dataset?: string;
  license?: string;
  settlement_coverage_status?: string;
}

export interface SatelliteSceneMetadata {
  scene_id: string;
  platform: string;
  instrument: string;
  acquisition_date: string;
  cloud_cover_percent: number;
  spatial_resolution_m: number;
  bounding_box: number[];
  bands: string[];
  source: DataSourceType;
  sun_elevation?: number;
  data_quality_score: number;
  preview_url?: string;
}

export interface SettlementImpact {
  settlement_id: string;
  name: string;
  local_name: string;
  district: string;
  municipality: string;
  coordinates: [number, number];
  elevation_m: number;
  population: number;
  household_count: number;
  impact_level: ImpactLevel;
  flooded_area_near_sqkm: number;
  distance_to_flood_m: number;
  critical_infrastructure_at_risk: string[];
  evacuation_priority: number;
  exposure_percentage: number;
  recommended_action: string;
  exposure_proxy_type?: string;
  gridded_baseline_population?: number;
  estimated_exposed_population?: number;
  provisional_priority_tier?: string;
  priority_score?: number;
  priority_reasons?: string[];
}

export interface PopulationDatasetMetadata {
  dataset_name: string;
  source_url: string;
  citation: string;
  license: string;
  reference_year: number;
  native_spatial_resolution_m: number;
  units: string;
  crs: string;
  availability_status: 'AVAILABLE' | 'UNAVAILABLE_DATASET';
}

export interface SettlementPopulationExposure {
  settlement_id: string;
  name: string;
  local_name: string;
  district: string;
  municipality: string;
  coordinates: [number, number];
  elevation_m: number;
  census_baseline_population: number;
  gridded_baseline_population: number;
  estimated_exposed_population: number;
  census_scaled_exposed_population: number;
  exposure_percentage: number;
  direct_inundation_detected: boolean;
  distance_to_flood_m: number;
  flooded_area_near_sqkm: number;
  critical_infrastructure_at_risk: string[];
  river_proximity_m: number;
  flood_hazard_severity: string;
  provisional_priority_rank: number;
  provisional_priority_tier: string;
  priority_score: number;
  priority_reasons: string[];
  operational_status: string;
  recommended_action: string;
  uncertainty_notes: string;
}

export interface PopulationExposureResult {
  study_area_id: string;
  timestamp: string;
  population_metadata: PopulationDatasetMetadata;
  total_domain_resident_population: number;
  total_domain_exposed_population: number;
  overall_exposure_percentage: number;
  cloud_masked_population: number;
  cloud_pierced_exposed_population: number;
  settlements: SettlementPopulationExposure[];
  vector_geojson_url?: string | null;
  double_counting_prevention_method: string;
  uncertainty_disclaimer: string;
}

export interface SettlementImpactSummary {
  total_settlements_analyzed: number;
  critical_count: number;
  high_count: number;
  moderate_count: number;
  monitoring_count: number;
  safe_count: number;
  total_exposed_population: number;
  critical_infrastructure_count: number;
  settlements: SettlementImpact[];
  provenance?: string;
}

export interface ValidationMetrics {
  reference_dataset?: string | null;
  reference_date?: string | null;
  true_positives_sqkm?: number | null;
  false_positives_sqkm?: number | null;
  false_negatives_sqkm?: number | null;
  true_negatives_sqkm?: number | null;
  precision?: number | null;
  recall?: number | null;
  f1_score?: number | null;
  iou_jaccard?: number | null;
  overall_accuracy?: number | null;
  validation_status: string;
  notes: string;
}

export type SensorMode = 'SENTINEL_2_OPTICAL' | 'SENTINEL_1_SAR' | 'DUAL_SENSOR_SYNERGY';
export type SARPolarization = 'VV' | 'VH' | 'VV+VH';

export interface SARSceneMetadata {
  scene_id: string;
  platform: string;
  instrument: string;
  product_type: string;
  polarization: string;
  acquisition_date: string;
  orbit_direction: string;
  relative_orbit: number;
  spatial_resolution_m: number;
  bounding_box: number[];
  backscatter_quantity: string;
  mean_backscatter_db?: number;
  asset_urls?: Record<string, string>;
  provider: string;
}

export interface SARAnalysisResult {
  pre_scene: SARSceneMetadata;
  post_scene: SARSceneMetadata;
  polarization: string;
  threshold_db: number;
  change_threshold_db: number;
  valid_sar_coverage_percent: number;
  valid_sar_sqkm: number;
  sar_footprint_coverage_percent?: number;
  sar_nodata_sqkm?: number;
  sar_nodata_coverage_percent?: number;
  sar_newly_inundated_sqkm: number;
  sar_newly_inundated_hectares: number;
  sar_permanent_water_sqkm: number;
  sar_mean_backscatter_change_db: number;
  geotiff_path?: string;
  processing_steps: string[];
  uncertainty_notice: string;
}

export interface DualSensorSynergyResult {
  optical_flood_sqkm: number;
  sar_flood_sqkm: number;
  consensus_confirmed_flood_sqkm: number;
  cloud_pierced_sar_flood_sqkm?: number;
  sar_flood_optical_nodata_sqkm?: number;
  sar_discordant_flood_sqkm?: number;
  optical_outside_sar_swath_sqkm?: number;
  optical_discordant_flood_sqkm?: number;
  cloud_pierced_flood_sqkm: number;
  optical_only_flood_sqkm: number;
  total_multi_sensor_flood_sqkm: number;
  sum_flood_partitions_sqkm?: number;
  flood_union_conservation_verified?: boolean;
  flood_conservation_residual_sqkm?: number;
  sensor_agreement_percent: number;
  domain_total_sqkm?: number;
  domain_permanent_water_sqkm?: number;
  optical_permanent_water_sqkm?: number;
  sar_permanent_water_sqkm?: number;
  combined_permanent_water_union_sqkm?: number;
  permanent_water_conservation_verified?: boolean;
  permanent_water_inclusion_exclusion_residual_sqkm?: number;
  domain_both_dry_sqkm?: number;
  domain_optical_cloud_sar_dry_sqkm?: number;
  domain_optical_cloud_sar_nodata_sqkm?: number;
  domain_optical_dry_sar_nodata_sqkm?: number;
  domain_optical_nodata_sar_dry_sqkm?: number;
  domain_both_nodata_sqkm?: number;
  full_grid_conservation_verified?: boolean;
  full_grid_residual_sqkm?: number;
  description: string;
}

export interface RasterDiagnosticInfo {
  dimensions: string;
  total_pixels: number;
  valid_pixels: number;
  valid_percentage: number;
  nodata_percentage: number;
  min_value: number;
  max_value: number;
  mean_value: number;
  sensor: string;
  scene_id?: string;
  acquisition_date?: string;
}

export interface FloodAnalysisResult {
  run_id: string;
  timestamp: string;
  study_area: StudyArea;
  provider_used?: string;
  utm_zone_crs?: string;
  native_spatial_resolution_m?: number;
  effective_grid_resolution_desc?: string;
  pre_scene: SatelliteSceneMetadata;
  post_scene: SatelliteSceneMetadata;
  pre_scenes?: SatelliteSceneMetadata[];
  post_scenes?: SatelliteSceneMetadata[];
  tiles_mosaicked?: string[];
  is_mosaic?: boolean;
  mosaic_provenance?: Record<string, any>;
  mosaic_warning?: string | null;
  water_index_used: WaterIndexType;
  threshold_applied: number;
  total_study_area_sqkm: number;
  permanent_water_sqkm: number;
  optical_permanent_water_sqkm?: number;
  sar_permanent_water_sqkm?: number;
  combined_permanent_water_sqkm?: number;
  pre_flood_water_sqkm: number;
  post_flood_water_sqkm: number;
  newly_inundated_sqkm: number;
  newly_inundated_hectares: number;
  cloud_masked_sqkm: number;
  cloud_mask_percentage: number;
  nodata_masked_sqkm?: number;
  nodata_mask_percentage?: number;
  valid_observation_percent: number;
  low_coverage_warning?: boolean;
  coverage_warning_message?: string | null;
  min_valid_coverage_percent?: number;
  impact_summary: SettlementImpactSummary;
  validation?: ValidationMetrics;
  sensor_mode?: SensorMode;
  degraded_mode?: boolean;
  degraded_warning?: string | null;
  pipeline_configuration?: Record<string, any>;
  water_index_details?: Record<string, any>;
  mmu_details?: Record<string, any>;
  sar_result?: SARAnalysisResult;
  synergy_result?: DualSensorSynergyResult;
  population_exposure?: PopulationExposureResult;
  receded_water_sqkm?: number;
  receded_water_hectares?: number;
  unchanged_dry_sqkm?: number;
  analysis_uncertainty_percent?: number;
  search_window?: {
    event_window?: string;
    event_title?: string;
    pre_search_start?: string;
    pre_search_end?: string;
    post_search_start?: string;
    post_search_end?: string;
    actual_pre_date?: string;
    actual_post_date?: string;
  };
  satellite_imagery_urls?: {
    pre_true_color?: string;
    post_true_color?: string;
    pre_false_color?: string;
    post_false_color?: string;
    pre_sar?: string;
    post_sar?: string;
    flood_difference_overlay?: string;
    flood_difference_geotiff?: string;
  };
  raster_diagnostics?: Record<string, RasterDiagnosticInfo>;
  raster_outputs: Record<string, string>;
  vector_outputs: Record<string, string>;
  report_download_url?: string;
}

export interface AnalysisRunRequest {
  study_area_id: string;
  pre_flood_date_start: string;
  pre_flood_date_end: string;
  post_flood_date_start: string;
  post_flood_date_end: string;
  max_cloud_cover_percent: number;
  min_valid_coverage_percent?: number;
  water_index: WaterIndexType;
  water_threshold: number;
  filter_permanent_water: boolean;
  min_mapping_unit_pixels: number;
  data_source: DataSourceType;
  enable_mosaicing?: boolean;
  sensor_mode?: SensorMode;
  sar_polarization?: SARPolarization;
  sar_threshold_db?: number;
  sar_change_threshold_db?: number;
}

export interface AnalysisJobProgress {
  run_id: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  stage: string;
  progress_percent: number;
  started_at: string;
  completed_at?: string | null;
  error?: string | null;
  result?: FloodAnalysisResult | null;
}

export type ActiveNavTab = 
  | 'overview'
  | 'analysis'
  | 'satellite'
  | 'map'
  | 'impact'
  | 'validation'
  | 'reports'
  | 'settings';
