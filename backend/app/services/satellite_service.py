"""
Genuine Satellite Data Acquisition & Surface Reflectance Ingestion Service.
Supports Public STAC Catalogs (Element84 AWS STAC / Planetary Computer) and Google Earth Engine.
Reads genuine Sentinel-2 Level-2A surface reflectance bands (B03 Green, B08 NIR, B11 SWIR, and SCL)
over HTTP via windowed rasterio reads.
Never substitutes failed acquisitions with random numbers or synthetic ellipses in production.
"""

import os
import asyncio
import concurrent.futures
import httpx
import numpy as np
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
import rasterio
from rasterio.transform import from_bounds, Affine
from rasterio.warp import reproject, Resampling, transform_bounds
from rasterio.windows import from_bounds as window_from_bounds, Window
import pyproj

from ..schemas.models import SatelliteSceneMetadata, DataSourceType, SatelliteProvider
from ..geospatial.nepal_data import STUDY_AREAS
from ..geospatial.raster_processor import get_utm_epsg_for_lon
from ..geospatial.indices import create_nodata_mask, create_cloud_mask_scl

STAC_ENDPOINT = os.getenv("STAC_API_ENDPOINT", "https://earth-search.aws.element84.com/v1/search")
CACHE_DIR = os.path.abspath("data/cache/stac")

class SatelliteService:
    def __init__(self):
        self.gee_available = self._check_earth_engine_status()
        self.provider_mode = os.getenv("SATELLITE_PROVIDER", "auto").lower()
        os.makedirs(CACHE_DIR, exist_ok=True)

    def _check_earth_engine_status(self) -> bool:
        """
        Tests whether Google Earth Engine credentials and project configuration are active.
        Reports honest connection status without simulating false authentication.
        """
        try:
            import ee
            ee.Initialize()
            return True
        except Exception:
            return False

    async def search_stac_scenes(
        self,
        bbox: List[float],
        date_start: str,
        date_end: str,
        max_cloud_cover: float = 50.0,
        limit: int = 10
    ) -> List[SatelliteSceneMetadata]:
        """
        Queries public STAC API for real Sentinel-2 L2A scenes covering the bounding box and dates.
        Returns empty list if no genuine scenes match the criteria.
        """
        results = []
        datetime_range = f"{date_start}T00:00:00Z/{date_end}T23:59:59Z"
        payload = {
            "collections": ["sentinel-2-l2a"],
            "bbox": bbox,
            "datetime": datetime_range,
            "query": {
                "eo:cloud_cover": {"lte": max_cloud_cover}
            },
            "limit": limit,
            "sortby": [{"field": "properties.datetime", "direction": "desc"}]
        }

        for attempt in range(2):
            try:
                async with httpx.AsyncClient(timeout=35.0) as client:
                    res = await client.post(STAC_ENDPOINT, json=payload)
                    if res.status_code == 200:
                        data = res.json()
                        for item in data.get("features", []):
                            props = item.get("properties", {})
                            scene_id = item.get("id", "S2_SCENE")
                            acq_date = props.get("datetime", date_start)[:10]
                            cloud = float(props.get("eo:cloud_cover", 0.0))

                            # Extract genuine asset links
                            assets = item.get("assets", {})
                            asset_urls = {}
                            for band_name, key in [("B03", "green"), ("B08", "nir"), ("B11", "swir16"), ("SCL", "scl")]:
                                if key in assets:
                                    asset_urls[band_name] = assets[key].get("href", "")

                            results.append(SatelliteSceneMetadata(
                                scene_id=scene_id,
                                platform=props.get("platform", "Sentinel-2"),
                                instrument="MSI Level-2A",
                                acquisition_date=acq_date,
                                cloud_cover_percent=round(cloud, 2),
                                spatial_resolution_m=10.0,
                                bounding_box=item.get("bbox", bbox),
                                bands=["B03", "B08", "B11", "SCL"],
                                source=DataSourceType.STAC_ELEMENT84,
                                sun_elevation=props.get("view:sun_elevation", 60.0),
                                data_quality_score=round(max(0.0, 100.0 - cloud), 1),
                                preview_url=assets.get("thumbnail", {}).get("href"),
                                native_crs=f"EPSG:{props['proj:epsg']}" if props.get("proj:epsg") else "EPSG:32645",
                                asset_urls=asset_urls
                            ))
                        break
            except Exception as e:
                if attempt == 0:
                    await asyncio.sleep(1.0)
                    continue
                print(f"[STAC Search Error] Failed to search scenes from {STAC_ENDPOINT}: {e}")

        # Smart adaptive fallback: if strict cloud threshold yielded zero scenes, broaden tolerance
        if not results and max_cloud_cover < 50.0:
            return await self.search_stac_scenes(
                bbox=bbox,
                date_start=date_start,
                date_end=date_end,
                max_cloud_cover=50.0,
                limit=limit
            )

        return results

    async def find_best_scene(
        self,
        bbox: List[float],
        date_start: str,
        date_end: str,
        max_cloud_cover: float = 50.0,
        preferred_tile: Optional[str] = None
    ) -> Optional[SatelliteSceneMetadata]:
        """
        Discovers genuine Sentinel-2 scene with lowest cloud cover within the specified temporal window.
        If preferred_tile is supplied, prioritizes scenes from the same MGRS tile for consistent swath coverage.
        """
        scenes = await self.search_stac_scenes(
            bbox=bbox,
            date_start=date_start,
            date_end=date_end,
            max_cloud_cover=max_cloud_cover
        )

        if not scenes:
            return None

        if preferred_tile:
            matching = [s for s in scenes if preferred_tile.upper() in s.scene_id.upper()]
            if matching:
                matching.sort(key=lambda s: s.cloud_cover_percent)
                return matching[0]

        # Sort by cloud cover ascending to select the clearest usable observation
        scenes.sort(key=lambda s: s.cloud_cover_percent)
        return scenes[0]

    async def find_best_scenes_multi_tile(
        self,
        bbox: List[float],
        date_start: str,
        date_end: str,
        max_cloud_cover: float = 50.0
    ) -> List[SatelliteSceneMetadata]:
        """
        Discovers genuine Sentinel-2 scenes for all intersecting MGRS tiles covering the study area bounding box.
        Dynamically extracts all tile IDs from STAC results (e.g. 45RVK and 45RWK for Koshi Basin).
        For each tile, selects the clearest scene, prioritizing coincident same-day passes when available.
        """
        scenes = await self.search_stac_scenes(
            bbox=bbox,
            date_start=date_start,
            date_end=date_end,
            max_cloud_cover=max_cloud_cover
        )

        if not scenes:
            return []

        # Group scenes by MGRS tile identifier (e.g., "45RWK", "45RVK")
        tile_groups: Dict[str, List[SatelliteSceneMetadata]] = {}
        for s in scenes:
            parts = s.scene_id.split('_')
            tile = parts[1] if len(parts) > 1 else "TILE"
            tile_groups.setdefault(tile, []).append(s)

        # Check if there is a common acquisition date across all detected tiles
        common_dates = None
        for tile, t_scenes in tile_groups.items():
            t_dates = {s.acquisition_date for s in t_scenes}
            if common_dates is None:
                common_dates = t_dates
            else:
                common_dates = common_dates.intersection(t_dates)

        selected_scenes: List[SatelliteSceneMetadata] = []
        best_common_date = None
        if common_dates:
            date_cloud_scores = []
            for d in common_dates:
                scores = [min(s.cloud_cover_percent for s in tile_groups[t] if s.acquisition_date == d) for t in tile_groups]
                date_cloud_scores.append((sum(scores) / len(scores), d))
            date_cloud_scores.sort()
            best_common_date = date_cloud_scores[0][1]

        for tile, t_scenes in sorted(tile_groups.items()):
            if best_common_date:
                matching_date = [s for s in t_scenes if s.acquisition_date == best_common_date]
                if matching_date:
                    matching_date.sort(key=lambda s: s.cloud_cover_percent)
                    selected_scenes.append(matching_date[0])
                    continue

            # Fallback: pick clearest scene for this tile
            t_scenes.sort(key=lambda s: s.cloud_cover_percent)
            selected_scenes.append(t_scenes[0])

        return selected_scenes

    def mosaic_tile_bands(
        self,
        scenes_with_bands: List[Tuple[SatelliteSceneMetadata, Dict[str, np.ndarray]]],
        grid_shape: Tuple[int, int] = (400, 500)
    ) -> Tuple[Dict[str, np.ndarray], Dict[str, Any]]:
        """
        Mosaics multi-tile Sentinel-2 bands onto the canonical target grid.
        Implements scientifically correct validity precedence:
        - Valid pixels always take precedence over NoData or cloudy pixels.
        - Where multiple tiles are valid in overlap zones, deterministic precedence chooses the clearer observation (lower scene cloud cover).
        - Cloudy observations are preserved over NoData to maintain atmospheric cloud accounting.
        - Outside-swath NoData occurs strictly where all tiles have NoData.
        """
        rows, cols = grid_shape
        if not scenes_with_bands:
            raise ValueError("No tile bands provided for mosaicing.")

        if len(scenes_with_bands) == 1:
            scene, bands = scenes_with_bands[0]
            tile = scene.scene_id.split('_')[1] if '_' in scene.scene_id else "TILE"
            meta = {
                "tiles_mosaicked": [tile],
                "scene_ids": [scene.scene_id],
                "acquisition_dates": [scene.acquisition_date],
                "is_mosaic": False,
                "is_single_pass": True,
                "date_difference_warning": None
            }
            return bands, meta

        # Sort tiles by scene cloud cover ascending (clearest tile has highest priority for tie-breaking)
        sorted_tiles = sorted(scenes_with_bands, key=lambda sb: sb[0].cloud_cover_percent)

        mosaic_bands: Dict[str, np.ndarray] = {
            b: np.zeros((rows, cols), dtype=np.uint8 if b == "SCL" else np.float32)
            for b in ["B03", "B08", "B11", "SCL"]
        }
        assigned_mask = np.zeros((rows, cols), dtype=bool)

        tile_data = []
        tile_names = []
        scene_ids = []
        acq_dates = []

        for scene, bands in sorted_tiles:
            tile = scene.scene_id.split('_')[1] if '_' in scene.scene_id else "TILE"
            tile_names.append(tile)
            scene_ids.append(scene.scene_id)
            acq_dates.append(scene.acquisition_date)

            nd = create_nodata_mask(bands["SCL"], [bands["B03"], bands["B08"], bands["B11"]])
            cl = create_cloud_mask_scl(bands["SCL"]) & (~nd)
            val = (~nd) & (~cl)
            tile_data.append((scene, bands, nd, cl, val))

        # Pass 1: Assign valid (clear-sky) observations
        for scene, bands, nd, cl, val in tile_data:
            take = val & (~assigned_mask)
            for b in mosaic_bands:
                mosaic_bands[b][take] = bands[b][take]
            assigned_mask |= take

        # Pass 2: Assign atmospheric cloud observations (prefer cloudy view over missing data)
        for scene, bands, nd, cl, val in tile_data:
            take = cl & (~assigned_mask)
            for b in mosaic_bands:
                mosaic_bands[b][take] = bands[b][take]
            assigned_mask |= take

        # Pass 3: Remaining unassigned pixels are true NoData across all tiles (outside all swaths)
        # mosaic_bands is already 0.0 / 0 for those pixels.

        distinct_dates = sorted(list(set(acq_dates)))
        is_single_pass = (len(distinct_dates) == 1)
        date_warning = None
        if not is_single_pass:
            date_warning = (
                f"Multi-date mosaic warning: tiles were acquired on different dates ({', '.join(distinct_dates)}). "
                f"Observations do not represent a single instantaneous satellite pass."
            )

        meta = {
            "tiles_mosaicked": sorted(list(set(tile_names))),
            "scene_ids": scene_ids,
            "acquisition_dates": distinct_dates,
            "is_mosaic": True,
            "is_single_pass": is_single_pass,
            "date_difference_warning": date_warning
        }

        return mosaic_bands, meta

    def read_real_band_window(
        self,
        asset_url: str,
        bbox: List[float],
        target_shape: Tuple[int, int] = (400, 500),
        is_categorical: bool = False,
        scene_id: str = "scene",
        band_name: str = "band"
    ) -> np.ndarray:
        """
        Reads actual satellite pixel data for the specified bounding box from a remote Cloud Optimized GeoTIFF (COG).
        Reprojects directly into the canonical EPSG:4326 analysis grid so every pixel matches the geographic transform.
        Caches retrieved rasters locally in 'data/cache/stac/' to accelerate repeated analyses.
        """
        cache_path = os.path.join(CACHE_DIR, f"{scene_id}_{band_name}_{target_shape[0]}x{target_shape[1]}.npy")

        if os.path.exists(cache_path):
            try:
                cached_data = np.load(cache_path)
                return cached_data
            except Exception:
                pass

        if not asset_url:
            raise ValueError(f"No asset URL provided for band '{band_name}' in scene '{scene_id}'")

        min_lon, min_lat, max_lon, max_lat = bbox
        rows, cols = target_shape
        dst_transform = from_bounds(min_lon, min_lat, max_lon, max_lat, cols, rows)
        resample_method = Resampling.nearest if is_categorical else Resampling.bilinear

        # Remote COG read and reprojection environment with bounded timeouts and VSI cache
        try:
            with rasterio.Env(
                AWS_NO_SIGN_REQUEST="YES",
                GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
                CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".tif",
                VSI_CACHE="TRUE",
                VSI_CACHE_SIZE="50000000",
                GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
                GDAL_HTTP_TIMEOUT="30",
                GDAL_HTTP_MAX_RETRY="3"
            ):
                with rasterio.open(asset_url) as src:
                    dst_data = np.zeros((rows, cols), dtype=np.uint8 if is_categorical else np.float32)

                    # Compute intersection between source raster bounds and requested study area
                    src_bbox = transform_bounds("EPSG:4326", src.crs, min_lon, min_lat, max_lon, max_lat)
                    sb = src.bounds
                    ix_min_x = max(src_bbox[0], sb.left)
                    ix_min_y = max(src_bbox[1], sb.bottom)
                    ix_max_x = min(src_bbox[2], sb.right)
                    ix_max_y = min(src_bbox[3], sb.top)

                    # If this tile does not intersect the bounding box, return empty/nodata array immediately
                    if ix_min_x >= ix_max_x or ix_min_y >= ix_max_y:
                        result = dst_data
                    else:
                        win = window_from_bounds(ix_min_x, ix_min_y, ix_max_x, ix_max_y, transform=src.transform)
                        win = win.round_offsets().round_shape()
                        win = win.intersection(Window(0, 0, src.width, src.height))

                        if win.width > 0 and win.height > 0:
                            # Read decimated window to use fast COG overviews rather than downloading full 100MB
                            sample_h = min(int(win.height), rows * 2)
                            sample_w = min(int(win.width), cols * 2)
                            win_data = src.read(
                                1,
                                window=win,
                                out_shape=(sample_h, sample_w),
                                resampling=Resampling.nearest if is_categorical else Resampling.bilinear
                            )
                            win_trans = rasterio.windows.transform(win, src.transform)
                            scaled_transform = win_trans * Affine.scale(win.width / sample_w, win.height / sample_h)

                            reproject(
                                source=win_data,
                                destination=dst_data,
                                src_transform=scaled_transform,
                                src_crs=src.crs,
                                dst_transform=dst_transform,
                                dst_crs="EPSG:4326",
                                resampling=resample_method
                            )

                    if is_categorical:
                        result = dst_data.astype(np.uint8)
                    else:
                        # Apply Sentinel-2 L2A surface reflectance scaling factor (DN * 0.0001)
                        result = (dst_data.astype(np.float32) * 0.0001)
                        # Filter invalid negative or saturated reflectance values
                        result = np.clip(result, 0.0, 1.0)

                    # Save to cache
                    try:
                        np.save(cache_path, result)
                    except Exception:
                        pass

                    return result
        except Exception as e:
            # If network read fails, provide clear scientific failure message
            raise ValueError(
                f"Failed to stream Sentinel-2 band '{band_name}' from remote STAC asset for scene '{scene_id}' ({e}). "
                f"Please ensure network access to AWS STAC or broaden temporal search window."
            )

    def load_surface_reflectance_bands(
        self,
        scene: SatelliteSceneMetadata,
        bbox: List[float],
        grid_shape: Tuple[int, int] = (400, 500)
    ) -> Dict[str, np.ndarray]:
        """
        Loads genuine multi-spectral surface reflectance bands (B03, B08, B11, SCL)
        from actual Sentinel-2 L2A COG assets.
        Never generates random arrays or mathematical ellipses.
        """
        asset_urls = scene.asset_urls
        if not asset_urls:
            raise ValueError(
                f"Scene '{scene.scene_id}' does not have real asset URLs. "
                f"Cannot acquire genuine satellite observations."
            )

        band_specs = [
            ("B03", False),
            ("B08", False),
            ("B11", False),
            ("SCL", True)
        ]

        def _fetch(spec):
            band_name, is_categorical = spec
            data = self.read_real_band_window(
                asset_url=asset_urls.get(band_name, ""),
                bbox=bbox,
                target_shape=grid_shape,
                is_categorical=is_categorical,
                scene_id=scene.scene_id,
                band_name=band_name
            )
            return band_name, data

        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            loaded_bands = dict(executor.map(_fetch, band_specs))

        return loaded_bands
