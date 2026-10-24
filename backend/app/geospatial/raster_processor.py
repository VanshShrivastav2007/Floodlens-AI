"""
Geospatial Raster & Vector Processing for Nepal Terai Flood Intelligence.
Handles dynamic UTM Zone determination (UTM 44N / 45N), georeferencing,
GeoTIFF creation, vector polygonization, metric area calculations, and proximity settlement impacts.
"""

import os
import json
import numpy as np
from typing import Dict, Any, List, Tuple, Optional, Union
import rasterio
from rasterio.transform import from_bounds
from rasterio.features import shapes
from shapely.geometry import shape, Point, mapping, MultiPolygon, Polygon
from shapely.ops import unary_union, transform as shapely_transform
import pyproj
from pyproj import Transformer, Geod
from PIL import Image

def get_utm_epsg_for_lon(lon: float) -> str:
    """
    Returns appropriate UTM CRS for Nepal Terai:
    - West Nepal (78°E - 84°E, e.g. Banke, Bardiya, Kailali, West Rapti): EPSG:32644 (UTM Zone 44N)
    - Central & East Nepal (84°E - 90°E, e.g. Koshi Basin, Bagmati, Rautahat, Chitwan): EPSG:32645 (UTM Zone 45N)
    """
    if lon < 84.0:
        return "EPSG:32644"
    return "EPSG:32645"

def get_transformer_for_bbox(bbox: List[float]) -> Tuple[str, Transformer, Transformer]:
    """
    Returns (utm_epsg, to_utm_transformer, to_wgs84_transformer) for the bounding box.
    """
    center_lon = (bbox[0] + bbox[2]) / 2.0
    utm_epsg = get_utm_epsg_for_lon(center_lon)
    to_utm = Transformer.from_crs("EPSG:4326", utm_epsg, always_xy=True)
    to_wgs84 = Transformer.from_crs(utm_epsg, "EPSG:4326", always_xy=True)
    return utm_epsg, to_utm, to_wgs84

from pyproj import Transformer, Geod
from typing import Dict, Any, List, Tuple, Optional, Union

def compute_raster_cell_areas_wgs84(
    bbox: List[float],
    width: int,
    height: int
) -> np.ndarray:
    """
    Computes exact 1D array of WGS84 ellipsoidal geodesic cell areas (in m^2)
    for each row r from 0 to height-1 according to the EPSG:4326 affine transform.
    Row 0 corresponds to the northernmost latitude band, row (height-1) to the southernmost.
    """
    min_lon, min_lat, max_lon, max_lat = bbox
    geod = Geod(ellps="WGS84")
    dlat = (max_lat - min_lat) / float(height)
    dlon = (max_lon - min_lon) / float(width)

    row_areas_m2 = np.zeros(height, dtype=np.float64)
    for r in range(height):
        lat_top = max_lat - r * dlat
        lat_bottom = lat_top - dlat
        cell_area_m2, _ = geod.polygon_area_perimeter(
            [0.0, dlon, dlon, 0.0, 0.0],
            [lat_bottom, lat_bottom, lat_top, lat_top, lat_bottom]
        )
        row_areas_m2[r] = abs(cell_area_m2)
    return row_areas_m2

def calculate_projected_area(
    target: Union[int, np.ndarray],
    bbox: List[float],
    width: int,
    height: int,
    pixel_size_m: Optional[Tuple[float, float]] = None
) -> Tuple[float, float, str]:
    """
    Calculates genuine metric area in square kilometers and hectares.
    Uses defensible per-cell geodesic areas on the WGS84 ellipsoid based on the actual
    EPSG:4326 affine transform. If a 2D mask is provided, each row is weighted by its
    exact latitudinal cell area, eliminating latitudinal distortion.
    If pixel_size_m is explicitly provided or target is an integer, uniform cell area is applied.
    """
    center_lon = (bbox[0] + bbox[2]) / 2.0
    utm_epsg = get_utm_epsg_for_lon(center_lon)

    if pixel_size_m is not None:
        pixel_width_m, pixel_height_m = pixel_size_m
        pixel_area_m2 = pixel_width_m * pixel_height_m
        if isinstance(target, np.ndarray):
            count = int(np.sum(target > 0))
        else:
            count = int(target)
        total_area_m2 = float(count) * pixel_area_m2
    elif isinstance(target, np.ndarray) and target.ndim == 2:
        # Exact row-wise geodesic weighting according to the affine transform
        row_areas_m2 = compute_raster_cell_areas_wgs84(bbox, width, height)
        row_counts = np.sum(target > 0, axis=1)
        total_area_m2 = float(np.sum(row_counts * row_areas_m2))
    else:
        # Count-based calculation using mean geodesic cell area of the grid
        row_areas_m2 = compute_raster_cell_areas_wgs84(bbox, width, height)
        mean_cell_area_m2 = float(np.mean(row_areas_m2))
        count = int(np.sum(target > 0)) if isinstance(target, np.ndarray) else int(target)
        total_area_m2 = float(count) * mean_cell_area_m2

    area_sqkm = total_area_m2 / 1_000_000.0
    area_hectares = area_sqkm * 100.0

    return round(area_sqkm, 3), round(area_hectares, 1), utm_epsg

def export_mask_to_geotiff(
    raster_data: np.ndarray,
    bbox: List[float],
    output_path: str,
    dtype: str = "uint8",
    nodata: int = 255,
    crs: str = "EPSG:4326"
) -> str:
    """
    Writes 2D numpy array to georeferenced GeoTIFF with correct affine transform and nodata.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    height, width = raster_data.shape
    min_lon, min_lat, max_lon, max_lat = bbox

    transform = from_bounds(min_lon, min_lat, max_lon, max_lat, width, height)

    with rasterio.open(
        output_path,
        'w',
        driver='GTiff',
        height=height,
        width=width,
        count=1,
        dtype=dtype,
        crs=crs,
        transform=transform,
        nodata=nodata,
        compress='deflate'
    ) as dst:
        dst.write(raster_data.astype(dtype), 1)

    return output_path

def generate_false_color_composite(
    swir_b11: np.ndarray,
    nir_b08: np.ndarray,
    green_b03: np.ndarray
) -> np.ndarray:
    """
    Constructs standard False-Color Water / Flood Enhancement composite (SWIR-NIR-Green)
    using percentile linear stretch [2%, 98%].
    Deep water appears dark navy/black, healthy vegetation is vibrant green,
    clouds are bright cyan/white, and bare sediment/settlements are brownish.
    Returns uint8 array of shape (height, width, 3).
    """
    def stretch(band: np.ndarray) -> np.ndarray:
        valid_vals = band[~np.isnan(band) & (band > 0)]
        if valid_vals.size == 0:
            return np.full_like(band, 18, dtype=np.uint8)
        p2, p98 = np.nanpercentile(valid_vals, (2, 98))
        if p98 <= p2:
            return np.full_like(band, 18, dtype=np.uint8)
        norm = np.clip((band - p2) / (p98 - p2), 0.0, 1.0) * 235.0 + 20.0
        norm_uint8 = norm.astype(np.uint8)
        norm_uint8[np.isnan(band) | (band <= 0)] = 18
        return norm_uint8

    r = stretch(swir_b11)
    g = stretch(nir_b08)
    b = stretch(green_b03)
    return np.stack([r, g, b], axis=-1)

def generate_true_color_composite(
    red_b04: Optional[np.ndarray],
    green_b03: np.ndarray,
    blue_b02: Optional[np.ndarray],
    nir_b08: Optional[np.ndarray] = None
) -> np.ndarray:
    """
    Constructs natural True-Color RGB composite from Red (B04), Green (B03), and Blue (B02)
    or simulated natural color from NIR/Green.
    Returns uint8 array of shape (height, width, 3).
    """
    def stretch(band: np.ndarray, max_val: float = 0.3) -> np.ndarray:
        norm = np.clip(band / max_val, 0.0, 1.0) * 235.0 + 20.0
        res = norm.astype(np.uint8)
        res[np.isnan(band) | (band <= 0)] = 18
        return res

    if red_b04 is not None and blue_b02 is not None:
        r = stretch(red_b04)
        g = stretch(green_b03)
        b = stretch(blue_b02)
    elif nir_b08 is not None:
        # Calibrated pseudo-natural color if only B03, B08, B11 are present
        r = stretch(green_b03 * 0.75 + nir_b08 * 0.25)
        g = stretch(green_b03)
        b = stretch(green_b03 * 0.55)
    else:
        r = g = b = stretch(green_b03)

    return np.stack([r, g, b], axis=-1)

def generate_sar_grayscale_image(
    sar_db: np.ndarray,
    valid_mask: np.ndarray
) -> np.ndarray:
    """
    Maps calibrated Sentinel-1 RTC backscatter (dB) into uint8 RGB image.
    Applies dynamic 2%-98% percentile stretch over valid observation pixels.
    Specular water surfaces appear dark charcoal (~28-45), rough soil/vegetation
    appears mid-gray (~110-170), settlements appear bright (>210).
    NoData / out-of-swath pixels are assigned a distinct neutral dark slate pattern (RGB: 18, 22, 28)
    with subtle diagonal grid texture so they are never confused with water or broken renders.
    Returns uint8 array of shape (height, width, 3).
    """
    height, width = sar_db.shape
    rgb = np.zeros((height, width, 3), dtype=np.uint8)

    # Base background for out-of-swath NoData: dark slate with subtle texture
    rows_grid, cols_grid = np.indices((height, width))
    hatch = ((rows_grid + cols_grid) % 6) < 3
    base_nodata = np.where(hatch, 18, 24).astype(np.uint8)
    rgb[:, :, 0] = base_nodata
    rgb[:, :, 1] = base_nodata + 4
    rgb[:, :, 2] = base_nodata + 8

    finite_mask = valid_mask & ~np.isnan(sar_db) & np.isfinite(sar_db) & (sar_db > -45.0) & (sar_db < 20.0)
    valid_vals = sar_db[finite_mask]

    if valid_vals.size > 0:
        p2 = float(np.percentile(valid_vals, 2))
        p98 = float(np.percentile(valid_vals, 98))
        # Ensure robust dynamic range span (at least 6 dB)
        if (p98 - p2) < 6.0:
            p2 = min(p2, -25.0)
            p98 = max(p98, -5.0)

        # Stretch valid pixels into [28, 245]
        scaled = np.clip((sar_db[finite_mask] - p2) / (p98 - p2), 0.0, 1.0)
        stretched = (28.0 + scaled * 217.0).astype(np.uint8)

        for c in range(3):
            rgb[finite_mask, c] = stretched

    return rgb

def compute_raster_diagnostic_metadata(
    raster_data: np.ndarray,
    valid_mask: Optional[np.ndarray] = None,
    sensor_name: str = "Sentinel"
) -> Dict[str, Any]:
    """
    Computes diagnostic telemetry for an observation raster.
    """
    height, width = raster_data.shape[:2]
    total_pixels = height * width
    if valid_mask is not None:
        valid_count = int(np.sum(valid_mask & ~np.isnan(raster_data)))
    else:
        valid_count = int(np.sum(~np.isnan(raster_data)))

    nodata_count = total_pixels - valid_count
    valid_pct = round((valid_count / float(total_pixels)) * 100.0, 1) if total_pixels > 0 else 0.0
    nodata_pct = round(100.0 - valid_pct, 1)

    finite_vals = raster_data[np.isfinite(raster_data)]
    min_val = round(float(np.nanmin(finite_vals)), 3) if finite_vals.size > 0 else 0.0
    max_val = round(float(np.nanmax(finite_vals)), 3) if finite_vals.size > 0 else 0.0
    mean_val = round(float(np.nanmean(finite_vals)), 3) if finite_vals.size > 0 else 0.0

    return {
        "dimensions": f"{width} × {height}",
        "total_pixels": total_pixels,
        "valid_pixels": valid_count,
        "valid_percentage": valid_pct,
        "nodata_percentage": nodata_pct,
        "min_value": min_val,
        "max_value": max_val,
        "mean_value": mean_val,
        "sensor": sensor_name
    }

def generate_flood_difference_rgba(
    newly_inundated: np.ndarray,
    permanent_water: np.ndarray,
    receded_water: np.ndarray,
    cloud_mask: np.ndarray,
    nodata_mask: np.ndarray
) -> np.ndarray:
    """
    Constructs a 4-channel transparent RGBA flood difference overlay:
    - Newly Inundated: Bright Cyan [0, 243, 255, 235]
    - Permanent Baseline Water: Royal Blue [37, 99, 235, 215]
    - Receded Water: Warning Amber [245, 158, 11, 215]
    - Cloud / Invalid: Hatched Slate Gray [100, 116, 139, 175] with 4x4 diagonal hatch
    - Unchanged Land: [0, 0, 0, 0] (transparent)
    Returns uint8 array of shape (height, width, 4).
    """
    height, width = newly_inundated.shape
    rgba = np.zeros((height, width, 4), dtype=np.uint8)

    # Permanent Water (Blue)
    rgba[permanent_water] = [37, 99, 235, 215]

    # Receded Water (Amber)
    rgba[receded_water] = [245, 158, 11, 215]

    # Newly Inundated (Bright Cyan)
    rgba[newly_inundated] = [0, 243, 255, 235]

    # Cloud & NoData with diagonal hatching pattern
    rows_grid, cols_grid = np.indices((height, width))
    hatch_pattern = ((rows_grid + cols_grid) % 4) < 2
    cloud_hatch = (cloud_mask | nodata_mask) & hatch_pattern
    rgba[cloud_hatch] = [100, 116, 139, 175]

    return rgba

def export_image_to_png(image_array: np.ndarray, output_path: str) -> str:
    """
    Saves RGB or RGBA numpy array to PNG file.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    img = Image.fromarray(image_array)
    img.save(output_path, format="PNG", optimize=True)
    return output_path

def export_multiclass_difference_geotiff(
    difference_grid: np.ndarray,
    bbox: List[float],
    output_path: str
) -> str:
    """
    Exports 8-bit multi-class change detection GeoTIFF:
    0: Unchanged Dry Land
    1: Newly Inundated Floodwater
    2: Permanent / Baseline Water
    3: Receded Water
    4: Cloud Obscured
    255: NoData / Outside Swath
    """
    return export_mask_to_geotiff(
        raster_data=difference_grid,
        bbox=bbox,
        output_path=output_path,
        dtype='uint8',
        nodata=255
    )

def vectorize_flood_extent(
    flood_mask: np.ndarray,
    bbox: List[float],
    output_geojson_path: Optional[str] = None,
    simplify_tolerance: float = 0.0003,
    detection_method: Optional[str] = None
) -> Dict[str, Any]:
    """
    Converts binary flood mask into GeoJSON MultiPolygon feature collection.
    Coordinates are formatted in WGS84 (EPSG:4326) compliant with RFC 7946.
    """
    height, width = flood_mask.shape
    min_lon, min_lat, max_lon, max_lat = bbox
    transform = from_bounds(min_lon, min_lat, max_lon, max_lat, width, height)

    features = []
    mask_uint8 = (flood_mask == 1).astype(np.uint8)
    method_str = detection_method or "Satellite Optical Water Index & MMU Filter"

    for geom_dict, val in shapes(mask_uint8, mask=(mask_uint8 == 1), transform=transform):
        if val == 1:
            geom = shape(geom_dict)
            if geom.is_valid and not geom.is_empty and geom.area > 0:
                if simplify_tolerance > 0:
                    geom = geom.simplify(simplify_tolerance, preserve_topology=True)
                features.append({
                    "type": "Feature",
                    "properties": {
                        "class": "Newly Inundated Floodwater",
                        "severity": "Inundated",
                        "detection_method": method_str
                    },
                    "geometry": mapping(geom)
                })

    geojson_collection = {
        "type": "FeatureCollection",
        "crs": {
            "type": "name",
            "properties": {"name": "urn:ogc:def:crs:OGC:1.3:CRS84"}
        },
        "features": features
    }

    if output_geojson_path:
        os.makedirs(os.path.dirname(output_geojson_path), exist_ok=True)
        with open(output_geojson_path, "w", encoding="utf-8") as f:
            json.dump(geojson_collection, f, indent=2)

    return geojson_collection

def assess_settlement_impacts(
    flood_mask: np.ndarray,
    bbox: List[float],
    settlements: List[Dict[str, Any]],
    study_area_id: str
) -> Dict[str, Any]:
    """
    Evaluates settlement inundation exposure and proximity using genuine metric distance.
    Uses dynamic UTM projection (Zone 44N or 45N) for accurate geodesic distance and buffer geometry.
    Note: Point locations serve as a proximity exposure proxy for municipal centroids.
    """
    # Strict filtering by active study area
    target_settlements = [s for s in settlements if s.get("study_area") == study_area_id]

    if not target_settlements:
        return {
            "total_settlements_analyzed": 0,
            "critical_count": 0,
            "high_count": 0,
            "moderate_count": 0,
            "monitoring_count": 0,
            "safe_count": 0,
            "total_exposed_population": 0,
            "critical_infrastructure_count": 0,
            "settlements": [],
            "provenance": "No settlements configured for this study area"
        }

    height, width = flood_mask.shape
    min_lon, min_lat, max_lon, max_lat = bbox
    utm_epsg, to_utm, _ = get_transformer_for_bbox(bbox)

    # Convert flood mask to UTM geometries for metric buffer analysis
    transform_wgs = from_bounds(min_lon, min_lat, max_lon, max_lat, width, height)
    mask_uint8 = (flood_mask == 1).astype(np.uint8)

    flood_geoms_utm = []
    for geom_dict, val in shapes(mask_uint8, mask=(mask_uint8 == 1), transform=transform_wgs):
        if val == 1:
            geom_wgs = shape(geom_dict)
            if geom_wgs.is_valid and not geom_wgs.is_empty:
                # Transform geometry to UTM
                geom_utm = shapely_transform(to_utm.transform, geom_wgs)
                if geom_utm.is_valid:
                    flood_geoms_utm.append(geom_utm)

    union_flood_utm = unary_union(flood_geoms_utm) if flood_geoms_utm else None

    analyzed_settlements = []
    total_exposed_population = 0
    total_infra_at_risk = 0
    counts = {"Critical": 0, "High": 0, "Moderate": 0, "Monitoring": 0, "Safe": 0}

    for s_info in target_settlements:
        coords = s_info["coordinates"]  # [lon, lat]
        pt_x, pt_y = to_utm.transform(coords[0], coords[1])
        pt_utm = Point(pt_x, pt_y)

        # Distance to flood extent in UTM meters
        dist_m = 99999.0
        is_directly_inundated = False

        # Grid coordinate for point check
        col = int((coords[0] - min_lon) / (max_lon - min_lon) * width) if max_lon > min_lon else 0
        row = int((max_lat - coords[1]) / (max_lat - min_lat) * height) if max_lat > min_lat else 0

        if 0 <= col < width and 0 <= row < height:
            if flood_mask[row, col] == 1:
                is_directly_inundated = True
                dist_m = 0.0

        if not is_directly_inundated and union_flood_utm and not union_flood_utm.is_empty:
            dist_m = round(float(pt_utm.distance(union_flood_utm)), 1)

        # Buffer calculation: 1500m buffer in genuine metric meters
        flooded_in_buffer_sqkm = 0.0
        if union_flood_utm and not union_flood_utm.is_empty:
            buffer_utm = pt_utm.buffer(1500.0)  # 1.5 km metric radius
            inter = buffer_utm.intersection(union_flood_utm)
            if not inter.is_empty:
                flooded_in_buffer_sqkm = round(float(inter.area) / 1_000_000.0, 3)

        # Impact classification rules
        exposure_pct = 0.0
        if is_directly_inundated or dist_m < 250:
            impact_level = "Critical"
            exposure_pct = min(100.0, 75.0 + (flooded_in_buffer_sqkm * 10))
            priority = 1
            action = "Immediate rescue/evacuation staging; deploy high-alert sirens; prepare emergency medical airlift."
        elif dist_m < 750 or flooded_in_buffer_sqkm > 0.8:
            impact_level = "High"
            exposure_pct = min(85.0, 45.0 + (flooded_in_buffer_sqkm * 8))
            priority = 2
            action = "Activate community elevated flood shelters; preposition clean water & food rations."
        elif dist_m < 1800 or flooded_in_buffer_sqkm > 0.2:
            impact_level = "Moderate"
            exposure_pct = min(40.0, 20.0 + (flooded_in_buffer_sqkm * 5))
            priority = 3
            action = "Monitor river gauge telemetry & Koshi Barrage discharge rates; inspect embankment spurs."
        elif dist_m < 3500:
            impact_level = "Monitoring"
            exposure_pct = 5.0
            priority = 4
            action = "Maintain local emergency contact watch; monitor ward road access."
        else:
            impact_level = "Safe"
            exposure_pct = 0.0
            priority = 5
            action = "No direct flood hazard detected within 3.5 km; potential regional relief staging site."

        counts[impact_level] += 1
        # Estimated exposed population based on municipal ward census
        exposed_pop = int(s_info["population"] * (exposure_pct / 100.0))
        total_exposed_population += exposed_pop

        infra_at_risk = []
        if impact_level in ["Critical", "High", "Moderate"]:
            infra_at_risk = s_info.get("critical_infrastructure", [])
            total_infra_at_risk += len(infra_at_risk)

        analyzed_settlements.append({
            "settlement_id": s_info["id"],
            "name": s_info["name"],
            "local_name": s_info.get("local_name", s_info["name"]),
            "district": s_info["district"],
            "municipality": s_info["municipality"],
            "coordinates": coords,
            "elevation_m": s_info.get("elevation_m", 75.0),
            "population": s_info["population"],
            "household_count": s_info.get("household_count", int(s_info["population"] / 5)),
            "impact_level": impact_level,
            "flooded_area_near_sqkm": flooded_in_buffer_sqkm,
            "distance_to_flood_m": dist_m,
            "critical_infrastructure_at_risk": infra_at_risk,
            "evacuation_priority": priority,
            "exposure_percentage": round(exposure_pct, 1),
            "recommended_action": action,
            "exposure_proxy_type": "Proximity Buffer (UTM Metric)"
        })

    analyzed_settlements.sort(key=lambda x: (x["evacuation_priority"], -x["population"]))

    return {
        "total_settlements_analyzed": len(target_settlements),
        "critical_count": counts["Critical"],
        "high_count": counts["High"],
        "moderate_count": counts["Moderate"],
        "monitoring_count": counts["Monitoring"],
        "safe_count": counts["Safe"],
        "total_exposed_population": total_exposed_population,
        "critical_infrastructure_count": total_infra_at_risk,
        "settlements": analyzed_settlements,
        "provenance": f"Nepal Administrative Records & OpenStreetMap (Projected in {utm_epsg})"
    }
