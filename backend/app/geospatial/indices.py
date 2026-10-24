"""
Geospatial Water Indices and Flood Detection Engine.
Implements NDWI, MNDWI, cloud masking, morphological noise suppression,
and change detection for Sentinel-2 MSI surface reflectance imagery.
"""

import numpy as np
from typing import Tuple, Optional, Dict, Any
from scipy import ndimage

def calculate_ndwi(green: np.ndarray, nir: np.ndarray, valid_mask: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Computes Normalized Difference Water Index (NDWI):
    NDWI = (Green - NIR) / (Green + NIR)
    Sentinel-2 bands: Green = B03 (560 nm), NIR = B08 (842 nm)
    Range: [-1.0, 1.0]. Water bodies typically yield values > 0.0 to 0.2.
    """
    green = green.astype(np.float32)
    nir = nir.astype(np.float32)

    numerator = green - nir
    denominator = green + nir

    # Prevent division by zero and extreme float artifacts
    with np.errstate(divide='ignore', invalid='ignore'):
        ndwi = np.where(denominator != 0, numerator / denominator, -1.0)
        ndwi = np.nan_to_num(ndwi, nan=-1.0, posinf=1.0, neginf=-1.0)

    if valid_mask is not None:
        ndwi = np.where(valid_mask, ndwi, -9999.0)

    return ndwi

def calculate_mndwi(green: np.ndarray, swir: np.ndarray, valid_mask: Optional[np.ndarray] = None) -> np.ndarray:
    """
    Computes Modified Normalized Difference Water Index (MNDWI):
    MNDWI = (Green - SWIR) / (Green + SWIR)
    Sentinel-2 bands: Green = B03 (560 nm), SWIR = B11 (1610 nm)
    SWIR significantly suppresses built-up land and urban shadows that often cause
    false positives in standard NDWI across Terai market centers.
    """
    green = green.astype(np.float32)
    swir = swir.astype(np.float32)

    numerator = green - swir
    denominator = green + swir

    with np.errstate(divide='ignore', invalid='ignore'):
        mndwi = np.where(denominator != 0, numerator / denominator, -1.0)
        mndwi = np.nan_to_num(mndwi, nan=-1.0, posinf=1.0, neginf=-1.0)

    if valid_mask is not None:
        mndwi = np.where(valid_mask, mndwi, -9999.0)

    return mndwi

def compute_otsu_threshold(index_raster: np.ndarray, mask: Optional[np.ndarray] = None) -> float:
    """
    Calculates dynamic bimodal Otsu threshold for water index raster.
    Returns optimal threshold separating water from dry land.
    """
    if mask is not None:
        valid_vals = index_raster[(mask) & (index_raster > -1.0) & (index_raster <= 1.0)]
    else:
        valid_vals = index_raster[(index_raster > -1.0) & (index_raster <= 1.0)]

    if len(valid_vals) == 0:
        return 0.05

    # Scale values to 0-255 histogram bins
    min_v, max_v = -1.0, 1.0
    scaled = np.clip(((valid_vals - min_v) / (max_v - min_v) * 255).astype(np.uint8), 0, 255)
    hist, _ = np.histogram(scaled, bins=256, range=(0, 256))
    total_pixels = len(scaled)

    if total_pixels == 0:
        return 0.05

    current_max = 0.0
    threshold_bin = 128
    weight_background = 0.0
    sum_b = 0.0
    sum_total = np.sum(np.arange(256) * hist)

    for i in range(256):
        weight_background += hist[i]
        if weight_background == 0:
            continue
        weight_foreground = total_pixels - weight_background
        if weight_foreground == 0:
            break

        sum_b += i * hist[i]
        mean_b = sum_b / weight_background
        mean_f = (sum_total - sum_b) / weight_foreground

        # Between-class variance
        var_between = weight_background * weight_foreground * ((mean_b - mean_f) ** 2)

        if var_between > current_max:
            current_max = var_between
            threshold_bin = i

    optimal_threshold = (threshold_bin / 255.0) * (max_v - min_v) + min_v
    # Clamp to reasonable water threshold range for Sentinel-2 in Terai [-0.1, 0.25]
    return float(np.clip(optimal_threshold, -0.10, 0.25))

def create_nodata_mask(scl_raster: np.ndarray, band_rasters: Optional[list] = None) -> np.ndarray:
    """
    Identifies missing data, sensor defects, or out-of-swath pixels where:
    - SCL == 0 (ESA NO_DATA / outside granule swath)
    - SCL == 1 (ESA SATURATED_OR_DEFECTIVE / detector failure)
    - Surface reflectance bands have zero/NaN values outside the sensor granule.
    """
    nodata = (scl_raster == 0) | (scl_raster == 1)
    if band_rasters:
        for b in band_rasters:
            nodata |= (b <= 0.0) | np.isnan(b)
    return nodata

def create_cloud_mask_scl(scl_raster: np.ndarray, include_nodata: bool = False) -> np.ndarray:
    """
    Generates atmospheric cloud and cloud shadow mask from Sentinel-2 Scene Classification Layer (SCL).
    Official ESA Sentinel-2 SCL Classes:
      0: NO_DATA (Sensor swath edge)
      1: SATURATED_OR_DEFECTIVE (Instrument defect / radiometric saturation - handled in nodata mask)
      2: DARK_AREA_PIXELS
      3: CLOUD_SHADOWS (Atmospheric)
      4: VEGETATION
      5: NOT_VEGETATED
      6: WATER
      7: UNCLASSIFIED
      8: CLOUD_MEDIUM_PROBABILITY (Atmospheric)
      9: CLOUD_HIGH_PROBABILITY (Atmospheric)
      10: THIN_CIRRUS (Atmospheric)
      11: SNOW_OR_ICE

    Returns boolean array: True = Atmospheric Cloud/Shadow, False = Clear
    """
    if include_nodata:
        cloud_classes = [0, 1, 3, 8, 9, 10, 11]
    else:
        # Strict atmospheric cloud & shadow classes (excludes 0: NO_DATA and 1: SATURATED_OR_DEFECTIVE)
        cloud_classes = [3, 8, 9, 10, 11]

    is_cloud = np.isin(scl_raster, cloud_classes)
    return is_cloud

def filter_minimum_mapping_unit(binary_mask: np.ndarray, min_pixels: int = 5) -> np.ndarray:
    """
    Removes isolated noise pixels below minimum mapping unit (MMU) threshold
    using connected component labeling.
    """
    if min_pixels <= 1:
        return binary_mask

    # 8-connectivity structure
    structure = np.ones((3, 3), dtype=int)
    labeled, num_features = ndimage.label(binary_mask, structure=structure)

    if num_features == 0:
        return binary_mask

    # Count sizes of each component
    component_sizes = np.bincount(labeled.ravel())
    # Identify components with size >= min_pixels (exclude background index 0)
    too_small = component_sizes < min_pixels
    too_small_mask = too_small[labeled]

    cleaned_mask = binary_mask.copy()
    cleaned_mask[too_small_mask] = False

    return cleaned_mask

def detect_flood_extent(
    pre_water: np.ndarray,
    post_water: np.ndarray,
    pre_cloud: np.ndarray,
    post_cloud: np.ndarray,
    pre_nodata: Optional[np.ndarray] = None,
    post_nodata: Optional[np.ndarray] = None,
    filter_permanent: bool = True,
    min_mmu_pixels: int = 5
) -> Dict[str, Any]:
    """
    Comprehensive flood extent detection and change analysis.
    Identifies:
    1. Valid observation area (clear of both clouds and out-of-swath nodata in both observations).
    2. Permanent / pre-existing water bodies.
    3. Post-flood total water extent.
    4. Newly inundated flood pixels: post_water AND NOT pre_water AND valid_observation.
    5. Applies minimum mapping unit filtering to suppress speckle false positives.
    Crucial rule: Unobserved pixels (cloud or nodata) are NEVER treated as dry land.
    """
    if pre_nodata is None:
        pre_nodata = np.zeros_like(pre_cloud, dtype=bool)
    if post_nodata is None:
        post_nodata = np.zeros_like(post_cloud, dtype=bool)

    # Valid observation mask (pixels clear of clouds AND valid in both scenes)
    valid_mask = (~pre_cloud) & (~post_cloud) & (~pre_nodata) & (~post_nodata)

    # Raw newly inundated pixels
    if filter_permanent:
        newly_inundated_raw = (post_water == 1) & (pre_water == 0) & valid_mask
    else:
        newly_inundated_raw = (post_water == 1) & valid_mask

    # Suppress speckle noise using connected component MMU
    newly_inundated_filtered = filter_minimum_mapping_unit(newly_inundated_raw, min_pixels=min_mmu_pixels)

    # Separate atmospheric cloud from sensor swath nodata
    cloud_mask_combined = (pre_cloud | post_cloud) & (~pre_nodata) & (~post_nodata)
    nodata_mask_combined = pre_nodata | post_nodata

    return {
        "valid_mask": valid_mask,
        "cloud_mask": cloud_mask_combined,
        "nodata_mask": nodata_mask_combined,
        "pre_water_mask": (pre_water == 1) & valid_mask,
        "post_water_mask": (post_water == 1) & valid_mask,
        "newly_inundated": newly_inundated_filtered,
        "raw_inundated_pixel_count": int(np.sum(newly_inundated_raw)),
        "filtered_inundated_pixel_count": int(np.sum(newly_inundated_filtered)),
        "pre_water_pixel_count": int(np.sum((pre_water == 1) & valid_mask)),
        "post_water_pixel_count": int(np.sum((post_water == 1) & valid_mask)),
        "cloud_pixel_count": int(np.sum(cloud_mask_combined)),
        "nodata_pixel_count": int(np.sum(nodata_mask_combined)),
        "valid_pixel_count": int(np.sum(valid_mask)),
        "total_pixel_count": int(valid_mask.size)
    }
