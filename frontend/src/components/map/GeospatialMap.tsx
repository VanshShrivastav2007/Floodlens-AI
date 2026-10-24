import React, { useEffect, useRef, useState } from 'react';
import maplibregl from 'maplibre-gl';
import { 
  Layers, 
  Eye, 
  EyeOff, 
  Maximize2, 
  RotateCcw, 
  MapPin, 
  Compass, 
  Sliders, 
  AlertTriangle,
  Info,
  CheckCircle2,
  Waves,
  Satellite as SatelliteIcon,
  Map as MapIcon
} from 'lucide-react';
import { StudyArea, SettlementImpact, FloodAnalysisResult } from '../../types';

interface GeospatialMapProps {
  studyArea: StudyArea;
  settlements: SettlementImpact[];
  analysisResult: FloodAnalysisResult | null;
  selectedSettlement: SettlementImpact | null;
  onSelectSettlement: (s: SettlementImpact | null) => void;
  isLoading: boolean;
  loadingStage?: string;
  loadingProgress?: number;
  onDismissLoading?: () => void;
}

type BasemapStyle = 'dark' | 'satellite' | 'streets';

const BASEMAP_TILES: Record<BasemapStyle, { name: string; tiles: string[]; maxzoom: number; attribution: string }> = {
  dark: {
    name: 'Dark Geospatial',
    tiles: [
      'https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
      'https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png',
      'https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}.png'
    ],
    maxzoom: 19,
    attribution: '&copy; OpenStreetMap contributors, &copy; CARTO'
  },
  satellite: {
    name: 'Satellite (Esri World Imagery)',
    tiles: [
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
    ],
    maxzoom: 18,
    attribution: '&copy; Esri, Maxar, Earthstar Geographics'
  },
  streets: {
    name: 'Street Map (Carto Voyager / OpenStreetMap)',
    tiles: [
      'https://a.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png',
      'https://b.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png',
      'https://c.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png'
    ],
    maxzoom: 19,
    attribution: '&copy; OpenStreetMap contributors, &copy; CARTO'
  }
};

export const GeospatialMap: React.FC<GeospatialMapProps> = ({
  studyArea,
  settlements,
  analysisResult,
  selectedSettlement,
  onSelectSettlement,
  isLoading,
  loadingStage,
  loadingProgress = 0,
  onDismissLoading
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);

  const [basemap, setBasemap] = useState<BasemapStyle>('dark');
  const [cursorCoords, setCursorCoords] = useState<{ lon: number; lat: number }>({
    lon: studyArea.center[0],
    lat: studyArea.center[1]
  });

  const [activeLayers, setActiveLayers] = useState({
    floodExtent: true,
    permanentWater: true,
    settlements: true,
    populationExposure: true,
    cloudMask: false,
    satelliteImagery: true
  });

  const [compareMode, setCompareMode] = useState<'flood' | 'pre' | 'post'>('flood');

  // Compute dynamic UTM zone for display
  const currentUtmZone = cursorCoords.lon < 84.0 ? 'UTM 44N (EPSG:32644)' : 'UTM 45N (EPSG:32645)';

  // Initialize MapLibre GL Map with all 3 basemap sources for seamless, instantaneous switching
  useEffect(() => {
    if (!mapContainerRef.current) return;

    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          'basemap-dark-source': {
            type: 'raster',
            tiles: BASEMAP_TILES.dark.tiles,
            tileSize: 256,
            attribution: BASEMAP_TILES.dark.attribution,
            maxzoom: 19
          },
          'basemap-satellite-source': {
            type: 'raster',
            tiles: BASEMAP_TILES.satellite.tiles,
            tileSize: 256,
            attribution: BASEMAP_TILES.satellite.attribution,
            maxzoom: 18
          },
          'basemap-streets-source': {
            type: 'raster',
            tiles: BASEMAP_TILES.streets.tiles,
            tileSize: 256,
            attribution: BASEMAP_TILES.streets.attribution,
            maxzoom: 19
          }
        },
        layers: [
          {
            id: 'basemap-dark-layer',
            type: 'raster',
            source: 'basemap-dark-source',
            minzoom: 0,
            maxzoom: 19,
            layout: {
              visibility: basemap === 'dark' ? 'visible' : 'none'
            }
          },
          {
            id: 'basemap-satellite-layer',
            type: 'raster',
            source: 'basemap-satellite-source',
            minzoom: 0,
            maxzoom: 18,
            layout: {
              visibility: basemap === 'satellite' ? 'visible' : 'none'
            }
          },
          {
            id: 'basemap-streets-layer',
            type: 'raster',
            source: 'basemap-streets-source',
            minzoom: 0,
            maxzoom: 19,
            layout: {
              visibility: basemap === 'streets' ? 'visible' : 'none'
            }
          }
        ]
      },
      center: studyArea.center,
      zoom: studyArea.default_zoom,
      pitch: 15,
      bearing: 0
    });

    map.addControl(new maplibregl.NavigationControl({ showCompass: true, visualizePitch: true }), 'top-right');
    map.addControl(new maplibregl.ScaleControl({ unit: 'metric' }), 'bottom-left');

    map.on('mousemove', (e) => {
      setCursorCoords({
        lon: Number(e.lngLat.lng.toFixed(5)),
        lat: Number(e.lngLat.lat.toFixed(5))
      });
    });

    map.on('error', (e) => {
      if (e?.error?.message?.includes('401') || e?.error?.message?.includes('403')) {
        console.warn('Basemap tile access notice:', e.error.message);
      }
    });

    map.on('load', () => {
      mapRef.current = map;
      // Add study area boundary source
      map.addSource('study-area-source', {
        type: 'geojson',
        data: {
          type: 'Feature',
          properties: { name: studyArea.name },
          geometry: studyArea.polygon || {
            type: 'Polygon',
            coordinates: [[
              [studyArea.bbox[0], studyArea.bbox[1]],
              [studyArea.bbox[2], studyArea.bbox[1]],
              [studyArea.bbox[2], studyArea.bbox[3]],
              [studyArea.bbox[0], studyArea.bbox[3]],
              [studyArea.bbox[0], studyArea.bbox[1]]
            ]]
          }
        }
      });

      // Study Area Bounding Box Outline
      map.addLayer({
        id: 'study-area-line',
        type: 'line',
        source: 'study-area-source',
        paint: {
          'line-color': '#00f3ff',
          'line-width': 2,
          'line-dasharray': [3, 2],
          'line-opacity': 0.8
        }
      });
    });

    const resizeObserver = new ResizeObserver(() => {
      if (mapRef.current) {
        mapRef.current.resize();
      }
    });

    if (mapContainerRef.current) {
      resizeObserver.observe(mapContainerRef.current);
    }

    return () => {
      resizeObserver.disconnect();
      map.remove();
      mapRef.current = null;
    };
  }, []);

  // Trigger map resize on state changes affecting layout
  useEffect(() => {
    if (!mapRef.current) return;
    const timer = setTimeout(() => {
      if (mapRef.current) {
        mapRef.current.resize();
      }
    }, 120);
    return () => clearTimeout(timer);
  }, [analysisResult, studyArea, isLoading]);

  // Update basemap when user changes selection
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    const setVisibility = () => {
      const allStyles: BasemapStyle[] = ['dark', 'satellite', 'streets'];
      allStyles.forEach(style => {
        const layerId = `basemap-${style}-layer`;
        if (map.getLayer(layerId)) {
          map.setLayoutProperty(layerId, 'visibility', basemap === style ? 'visible' : 'none');
        }
      });
    };

    if (map.isStyleLoaded()) {
      setVisibility();
    } else {
      map.once('style.load', setVisibility);
    }
  }, [basemap]);

  // Recenter when study area changes
  useEffect(() => {
    if (!mapRef.current) return;
    mapRef.current.flyTo({
      center: studyArea.center,
      zoom: studyArea.default_zoom,
      speed: 1.2
    });

    const source = mapRef.current.getSource('study-area-source') as maplibregl.GeoJSONSource;
    if (source) {
      source.setData({
        type: 'Feature',
        properties: { name: studyArea.name },
        geometry: studyArea.polygon || {
          type: 'Polygon',
          coordinates: [[
            [studyArea.bbox[0], studyArea.bbox[1]],
            [studyArea.bbox[2], studyArea.bbox[1]],
            [studyArea.bbox[2], studyArea.bbox[3]],
            [studyArea.bbox[0], studyArea.bbox[3]],
            [studyArea.bbox[0], studyArea.bbox[1]]
          ]]
        }
      });
    }
  }, [studyArea]);

  // Load and render Flood Extent Vectors when Analysis Result is available
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    // Check if result matches current study area
    const isMatchingArea = analysisResult && (!analysisResult.study_area || analysisResult.study_area.id === studyArea.id);

    if (!isMatchingArea || !analysisResult?.vector_outputs?.geojson) {
      if (map.getLayer('flood-fill-layer')) map.removeLayer('flood-fill-layer');
      if (map.getLayer('flood-outline-layer')) map.removeLayer('flood-outline-layer');
      if (map.getSource('flood-extent-source')) map.removeSource('flood-extent-source');
      return;
    }

    const geojsonUrl = analysisResult.vector_outputs.geojson;

    if (map.getLayer('flood-fill-layer')) map.removeLayer('flood-fill-layer');
    if (map.getLayer('flood-outline-layer')) map.removeLayer('flood-outline-layer');
    if (map.getSource('flood-extent-source')) map.removeSource('flood-extent-source');

    fetch(geojsonUrl)
      .then(res => res.json())
      .then(data => {
        if (!mapRef.current) return;
        // Verify current study area still matches when fetch resolves
        if (analysisResult.study_area && analysisResult.study_area.id !== studyArea.id) return;

        mapRef.current.addSource('flood-extent-source', {
          type: 'geojson',
          data: data
        });

        const isFloodVisible = activeLayers.floodExtent && compareMode !== 'pre';
        mapRef.current.addLayer({
          id: 'flood-fill-layer',
          type: 'fill',
          source: 'flood-extent-source',
          paint: {
            'fill-color': '#ff3366',
            'fill-opacity': isFloodVisible ? 0.72 : 0.0
          }
        });

        mapRef.current.addLayer({
          id: 'flood-outline-layer',
          type: 'line',
          source: 'flood-extent-source',
          paint: {
            'line-color': '#00f3ff',
            'line-width': 1.5,
            'line-opacity': isFloodVisible ? 0.95 : 0.0
          }
        });
      })
      .catch(err => console.error('Failed to load flood extent vectors:', err));
  }, [analysisResult, activeLayers.floodExtent, compareMode, studyArea.id]);

  // Load and render actual Analysis Satellite Imagery (Layer B) georeferenced over study basin
  useEffect(() => {
    const map = mapRef.current;
    if (!map || !map.isStyleLoaded()) return;

    const sourceId = 'analysis-imagery-source';
    const layerId = 'analysis-imagery-layer';

    const removeExisting = () => {
      if (map.getLayer(layerId)) map.removeLayer(layerId);
      if (map.getSource(sourceId)) map.removeSource(sourceId);
    };

    const isMatchingArea = analysisResult && (!analysisResult.study_area || analysisResult.study_area.id === studyArea.id);
    const urls = analysisResult?.satellite_imagery_urls;

    let targetImageUrl: string | null = null;
    if (isMatchingArea && activeLayers.satelliteImagery && urls) {
      if (compareMode === 'pre') {
        targetImageUrl = urls.pre_false_color || urls.pre_true_color || urls.pre_sar || null;
      } else if (compareMode === 'post') {
        targetImageUrl = urls.post_false_color || urls.post_true_color || urls.post_sar || null;
      } else {
        // 'flood' mode: show difference overlay raster if available
        targetImageUrl = urls.flood_difference_overlay || null;
      }
    }

    if (!targetImageUrl || !analysisResult?.study_area?.bbox) {
      removeExisting();
      return;
    }

    const bbox = analysisResult.study_area.bbox; // [min_lon, min_lat, max_lon, max_lat]
    const coordinates: [[number, number], [number, number], [number, number], [number, number]] = [
      [bbox[0], bbox[3]], // top-left
      [bbox[2], bbox[3]], // top-right
      [bbox[2], bbox[1]], // bottom-right
      [bbox[0], bbox[1]]  // bottom-left
    ];

    removeExisting();

    try {
      map.addSource(sourceId, {
        type: 'image',
        url: targetImageUrl,
        coordinates: coordinates
      });

      // Insert directly below study area line and flood layers
      const beforeLayer = map.getLayer('study-area-line')
        ? 'study-area-line'
        : (map.getLayer('flood-fill-layer') ? 'flood-fill-layer' : undefined);

      map.addLayer({
        id: layerId,
        type: 'raster',
        source: sourceId,
        paint: {
          'raster-opacity': compareMode === 'flood' ? 0.60 : 0.95,
          'raster-fade-duration': 200
        }
      }, beforeLayer);
    } catch (err) {
      console.warn('Failed to add analysis imagery raster layer to map:', err);
    }
  }, [analysisResult, activeLayers.satelliteImagery, compareMode, studyArea.id]);

  // Render Settlement Markers
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    markersRef.current.forEach(m => m.remove());
    markersRef.current = [];

    if (!activeLayers.settlements) return;

    const popLookup = new Map<string, any>();
    if (analysisResult?.population_exposure?.settlements) {
      analysisResult.population_exposure.settlements.forEach(p => {
        popLookup.set(p.settlement_id, p);
      });
    }

    settlements.forEach(s => {
      const settlementId = s.settlement_id || (s as any).id;
      const el = document.createElement('div');
      el.className = 'cursor-pointer group relative';

      const popItem = popLookup.get(settlementId);

      let colorClass = 'bg-emerald-500 text-emerald-300';
      let pingClass = '';

      const priorityTier = popItem?.provisional_priority_tier || '';

      if (activeLayers.populationExposure && popItem) {
        if (priorityTier.includes('Tier 1')) {
          colorClass = 'bg-rose-500 text-rose-300 shadow-glow-alert';
          pingClass = 'animate-ping';
        } else if (priorityTier.includes('Tier 2')) {
          colorClass = 'bg-amber-500 text-amber-300 shadow-glow-amber';
          pingClass = popItem.direct_inundation_detected ? 'animate-ping' : '';
        } else if (priorityTier.includes('Tier 3')) {
          colorClass = 'bg-cyan-500 text-cyan-300';
        }
      } else {
        if (s.impact_level === 'Critical') {
          colorClass = 'bg-rose-500 text-rose-300 shadow-glow-alert';
          pingClass = 'animate-ping';
        } else if (s.impact_level === 'High') {
          colorClass = 'bg-amber-500 text-amber-300';
        } else if (s.impact_level === 'Moderate') {
          colorClass = 'bg-cyan-500 text-cyan-300';
        }
      }

      const isSelected = selectedSettlement?.settlement_id === settlementId;

      el.innerHTML = `
        <div class="relative flex items-center justify-center">
          ${(pingClass && (s.impact_level === 'Critical' || priorityTier.includes('Tier 1'))) ? `<span class="absolute w-5 h-5 rounded-full ${colorClass} opacity-60 ${pingClass}"></span>` : ''}
          <div class="w-3.5 h-3.5 rounded-full border-2 ${isSelected ? 'border-white scale-125' : 'border-black'} ${colorClass} transition-transform"></div>
        </div>
      `;

      el.addEventListener('click', (e) => {
        e.stopPropagation();
        if (popItem) {
          onSelectSettlement({
            ...s,
            settlement_id: settlementId,
            gridded_baseline_population: popItem.gridded_baseline_population,
            estimated_exposed_population: popItem.estimated_exposed_population,
            provisional_priority_tier: popItem.provisional_priority_tier,
            priority_score: popItem.priority_score,
            priority_reasons: popItem.priority_reasons
          });
        } else {
          onSelectSettlement({ ...s, settlement_id: settlementId });
        }
      });

      const formattedPop = (typeof s.population === 'number' && s.population > 0)
        ? s.population.toLocaleString()
        : 'N/A (OSM)';

      const nameLabel = s.local_name && s.local_name !== s.name
        ? `${s.name} (${s.local_name})`
        : (s.name || 'Settlement');

      const adminLabel = [s.municipality, s.district].filter(Boolean).join(', ') || 'Nepal Terai';

      const popupHtml = `
        <div style="background: #070d1d; color: #fff; padding: 10px 12px; border-radius: 6px; font-family: sans-serif; font-size: 12px; border: 1px solid #1e293b; min-width: 210px;">
          <div style="font-weight: 700; color: #00f3ff; font-size: 13px;">${nameLabel}</div>
          <div style="color: #94a3b8; font-size: 11px;">${adminLabel}</div>
          
          <div style="margin-top: 6px; padding-top: 6px; border-top: 1px solid #1e293b; display: flex; justify-content: space-between; gap: 8px;">
            <span>Census Pop: <strong>${formattedPop}</strong></span>
            <span style="color: ${s.impact_level === 'Critical' ? '#ef4444' : (s.impact_level === 'High' ? '#f59e0b' : '#38bdf8')}; font-weight: 700;">${s.impact_level || 'Monitoring'}</span>
          </div>

          ${popItem ? `
          <div style="margin-top: 4px; padding: 4px 6px; background: rgba(56, 189, 248, 0.08); border: 1px solid rgba(56, 189, 248, 0.25); border-radius: 4px;">
            <div style="display: flex; justify-content: space-between; font-size: 11px;">
              <span style="color: #94a3b8;">WorldPop Exposed:</span>
              <strong style="color: #ff3366;">~${Math.round(popItem.estimated_exposed_population || 0).toLocaleString()}</strong>
            </div>
            <div style="display: flex; justify-content: space-between; font-size: 10px; margin-top: 2px;">
              <span style="color: #94a3b8;">Priority Tier:</span>
              <strong style="color: ${priorityTier.includes('Tier 1') ? '#ef4444' : (priorityTier.includes('Tier 2') ? '#f59e0b' : '#38bdf8')}">
                ${priorityTier.split(':')[0]} (${popItem.priority_score ?? 0} pts)
              </strong>
            </div>
          </div>
          ` : ''}

          <div style="margin-top: 4px; font-size: 10px; color: #94a3b8;">Dist to flood: <strong>${s.distance_to_flood_m != null ? `${s.distance_to_flood_m}m` : 'N/A'}</strong></div>
          ${popItem && popItem.priority_reasons?.length > 0 ? `<div style="font-size: 9px; color: #fca5a5; margin-top: 2px;">&bull; ${popItem.priority_reasons[0]}</div>` : ''}
          <div style="font-size: 8px; color: #64748b; margin-top: 4px;">WorldPop 2020 Dasymetric &bull; DDMC Decision Support</div>
        </div>
      `;

      const popup = new maplibregl.Popup({ offset: 12, closeButton: false })
        .setHTML(popupHtml);

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat(s.coordinates)
        .setPopup(popup)
        .addTo(map);

      markersRef.current.push(marker);
    });
  }, [settlements, activeLayers.settlements, activeLayers.populationExposure, analysisResult, selectedSettlement]);

  // Fly to selected settlement
  useEffect(() => {
    if (selectedSettlement && mapRef.current) {
      mapRef.current.flyTo({
        center: selectedSettlement.coordinates,
        zoom: 13,
        speed: 1.4
      });
    }
  }, [selectedSettlement]);

  const resetView = () => {
    if (mapRef.current) {
      mapRef.current.flyTo({
        center: studyArea.center,
        zoom: studyArea.default_zoom,
        pitch: 15,
        bearing: 0,
        speed: 1.2
      });
    }
  };

  return (
    <div className="relative w-full h-full flex flex-col overflow-hidden bg-command-950">
      {/* MapLibre WebGL Viewport */}
      <div ref={mapContainerRef} className="absolute inset-0 overflow-hidden cursor-crosshair" />

      {/* Loading Overlay */}
      {isLoading && (
        <div className="absolute inset-0 bg-command-950/75 backdrop-blur-sm z-30 flex flex-col items-center justify-center space-y-4 p-6">
          <div className="relative w-16 h-16 flex items-center justify-center">
            <div className="absolute inset-0 rounded-full border-2 border-cyan-glow/20 animate-ping" />
            <div className="w-12 h-12 rounded-full border-2 border-t-cyan-glow border-r-transparent border-b-blue-500 border-l-transparent animate-spin" />
            <Waves className="w-5 h-5 text-cyan-glow animate-pulse" />
          </div>
          <div className="text-center max-w-md">
            <div className="text-xs font-mono tracking-widest text-cyan-glow uppercase font-bold">
              {loadingStage || 'Ingesting Genuine Sentinel-2 L2A Surface Reflectance...'}
            </div>
            <div className="text-[11px] font-mono text-slate-400 mt-1">
              Element84 AWS STAC &bull; Dynamic {currentUtmZone}
            </div>

            {/* Visual Progress Bar */}
            <div className="w-64 h-1.5 bg-command-900 rounded-full mt-3 overflow-hidden border border-cyan-glow/30 mx-auto">
              <div 
                className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300 ease-out"
                style={{ width: `${Math.min(100, Math.max(5, loadingProgress))}%` }}
              />
            </div>
            <div className="text-[10px] font-mono text-slate-400 mt-1">
              {loadingProgress}% Complete
            </div>

            {/* Dismiss / Cancel Button */}
            {onDismissLoading && (
              <button
                onClick={onDismissLoading}
                className="mt-4 px-3 py-1.5 rounded bg-command-800/80 hover:bg-command-700 border border-slate-700 hover:border-slate-500 text-[10px] font-mono text-slate-300 hover:text-white transition-all shadow-md pointer-events-auto"
              >
                Dismiss Overlay / Explore Map
              </button>
            )}
          </div>
        </div>
      )}

      {/* Top Floating Map Controls */}
      <div className="absolute top-4 left-4 z-20 flex flex-wrap items-center gap-2">
        {/* Reset View Button */}
        <button
          onClick={resetView}
          className="px-3 py-1.5 rounded hud-panel hover:bg-command-800 text-xs font-mono text-slate-300 hover:text-cyan-glow flex items-center space-x-1.5 transition-all shadow-md"
          title="Reset View to Study Basin"
        >
          <RotateCcw className="w-3.5 h-3.5" />
          <span>RESET VIEW</span>
        </button>

        {/* Basemap Switcher (Dark / Satellite / Streets) */}
        <div className="hud-panel p-1 rounded flex items-center space-x-1 shadow-md">
          <button
            onClick={() => setBasemap('dark')}
            className={`px-2.5 py-1 rounded text-xs font-mono transition-all ${
              basemap === 'dark'
                ? 'bg-cyan-500/20 text-cyan-glow border border-cyan-glow/40 shadow-glow-cyan'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            DARK
          </button>
          <button
            onClick={() => setBasemap('satellite')}
            className={`px-2.5 py-1 rounded text-xs font-mono transition-all flex items-center space-x-1 ${
              basemap === 'satellite'
                ? 'bg-cyan-500/20 text-cyan-glow border border-cyan-glow/40 shadow-glow-cyan'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            <SatelliteIcon className="w-3 h-3" />
            <span>SATELLITE</span>
          </button>
          <button
            onClick={() => setBasemap('streets')}
            className={`px-2.5 py-1 rounded text-xs font-mono transition-all ${
              basemap === 'streets'
                ? 'bg-cyan-500/20 text-cyan-glow border border-cyan-glow/40 shadow-glow-cyan'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            STREETS
          </button>
        </div>

        {/* Observation Layer Mode Picker */}
        <div className="hud-panel p-1 rounded flex items-center space-x-1 shadow-md">
          <button
            onClick={() => setCompareMode('flood')}
            className={`px-2.5 py-1 rounded text-xs font-mono transition-all ${
              compareMode === 'flood'
                ? 'bg-cyan-500/20 text-cyan-glow border border-cyan-glow/40'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            FLOOD EXTENT
          </button>
          <button
            onClick={() => setCompareMode('pre')}
            className={`px-2.5 py-1 rounded text-xs font-mono transition-all ${
              compareMode === 'pre'
                ? 'bg-cyan-500/20 text-cyan-glow border border-cyan-glow/40'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            PRE-EVENT
          </button>
          <button
            onClick={() => setCompareMode('post')}
            className={`px-2.5 py-1 rounded text-xs font-mono transition-all ${
              compareMode === 'post'
                ? 'bg-cyan-500/20 text-cyan-glow border border-cyan-glow/40'
                : 'text-slate-400 hover:text-white'
            }`}
          >
            POST-EVENT
          </button>
        </div>
      </div>

      {/* Bottom Floating Coordinate & Scale HUD */}
      <div className="absolute bottom-4 left-4 z-20 flex items-center space-x-3 pointer-events-none">
        <div className="hud-panel px-3 py-1.5 rounded font-mono text-[11px] text-slate-300 flex items-center space-x-3 shadow-lg">
          <div className="flex items-center space-x-1 text-cyan-glow">
            <Compass className="w-3.5 h-3.5" />
            <span>WGS84</span>
          </div>
          <div>LON: <span className="text-white font-semibold">{cursorCoords.lon}° E</span></div>
          <div>LAT: <span className="text-white font-semibold">{cursorCoords.lat}° N</span></div>
          <div className="border-l border-slate-700 pl-2 text-slate-400">
            {currentUtmZone} &bull; ELEV ~74m
          </div>
        </div>
      </div>

      {/* Bottom Right Floating Map Legend */}
      <div className="absolute bottom-4 right-4 z-20 hud-panel p-3 rounded text-xs font-mono space-y-2 max-w-xs shadow-xl pointer-events-auto">
        <div className="text-[10px] uppercase font-bold tracking-wider text-slate-400 flex items-center justify-between border-b border-slate-800 pb-1.5">
          <span>GEOSPATIAL LEGEND</span>
          <Layers className="w-3 h-3 text-cyan-glow" />
        </div>

        <div className="space-y-1.5 text-[11px]">
          <div className="flex items-center space-x-2">
            <span className="w-3.5 h-3.5 rounded bg-[#ff3366] border border-cyan-glow inline-block" />
            <span className="text-slate-200">Newly Inundated Floodwater</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-3.5 h-2 rounded bg-cyan-600 inline-block" />
            <span className="text-slate-300">Baseline Permanent Water</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-rose-500 shadow-glow-alert inline-block" />
            <span className="text-slate-300">Critical Proximity (&lt; 250m)</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 inline-block" />
            <span className="text-slate-300">High Risk Proximity (&lt; 750m)</span>
          </div>
          <div className="flex items-center space-x-2">
            <span className="w-3.5 h-0.5 border-t-2 border-dashed border-cyan-glow inline-block" />
            <span className="text-slate-400">Study Area Bounding Box</span>
          </div>
        </div>

        {/* Layer Toggles */}
        <div className="pt-2 border-t border-slate-800/80 grid grid-cols-2 gap-2 text-[10px] text-slate-400">
          <label className="flex items-center space-x-1 cursor-pointer hover:text-white">
            <input 
              type="checkbox" 
              checked={activeLayers.floodExtent}
              onChange={(e) => setActiveLayers(prev => ({ ...prev, floodExtent: e.target.checked }))}
              className="rounded bg-command-900 border-slate-700 text-cyan-500 focus:ring-0 w-3 h-3"
            />
            <span>Flood Vector</span>
          </label>
          <label className="flex items-center space-x-1 cursor-pointer hover:text-white">
            <input 
              type="checkbox" 
              checked={activeLayers.satelliteImagery}
              onChange={(e) => setActiveLayers(prev => ({ ...prev, satelliteImagery: e.target.checked }))}
              className="rounded bg-command-900 border-slate-700 text-cyan-500 focus:ring-0 w-3 h-3"
            />
            <span>Sentinel Scene</span>
          </label>
          <label className="flex items-center space-x-1 cursor-pointer hover:text-white">
            <input 
              type="checkbox" 
              checked={activeLayers.settlements}
              onChange={(e) => setActiveLayers(prev => ({ ...prev, settlements: e.target.checked }))}
              className="rounded bg-command-900 border-slate-700 text-cyan-500 focus:ring-0 w-3 h-3"
            />
            <span>Settlements</span>
          </label>
          <label className="flex items-center space-x-1 cursor-pointer hover:text-white">
            <input 
              type="checkbox" 
              checked={activeLayers.populationExposure}
              onChange={(e) => setActiveLayers(prev => ({ ...prev, populationExposure: e.target.checked }))}
              className="rounded bg-command-900 border-slate-700 text-cyan-500 focus:ring-0 w-3 h-3"
            />
            <span>WorldPop Risk</span>
          </label>
        </div>
      </div>
    </div>
  );
};
