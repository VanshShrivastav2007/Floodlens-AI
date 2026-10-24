import React, { useState, useEffect, useRef } from 'react';
import { 
  StudyArea, 
  SettlementImpact, 
  FloodAnalysisResult, 
  AnalysisRunRequest, 
  ActiveNavTab 
} from './types';
import { api } from './services/api';
import { CinematicGlobeIntro } from './components/3d/CinematicGlobeIntro';
import { AtmosphericBackground } from './components/3d/AtmosphericBackground';
import { TopNav } from './components/layout/TopNav';
import { SidebarRail } from './components/layout/SidebarRail';
import { TimelineBar } from './components/layout/TimelineBar';
import { RightAnalysisPanel } from './components/layout/RightAnalysisPanel';
import { GeospatialMap } from './components/map/GeospatialMap';
import { OverviewView } from './components/views/OverviewView';
import { FloodAnalysisView } from './components/views/FloodAnalysisView';
import { SatelliteImageryView } from './components/views/SatelliteImageryView';
import { SettlementImpactView } from './components/views/SettlementImpactView';
import { ValidationView } from './components/views/ValidationView';
import { ReportsExportView } from './components/views/ReportsExportView';
import { SettingsView } from './components/views/SettingsView';
import { ErrorBoundary } from './components/common/ErrorBoundary';

export const App: React.FC = () => {
  const [showIntro, setShowIntro] = useState<boolean>(true);
  const [activeTab, setActiveTab] = useState<ActiveNavTab>('map');
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState<boolean>(false);

  const [studyAreas, setStudyAreas] = useState<StudyArea[]>([
    {
      id: 'koshi_basin',
      name: 'Koshi River Basin (Eastern Terai)',
      district: 'Sunsari / Morang / Saptari',
      province: 'Koshi & Madhesh Province',
      description: 'High-risk monsoon flood zone along the Saptakoshi river system, including Sunsari, Morang, and Saptari lowlands.',
      bbox: [86.75, 26.35, 87.35, 26.85],
      center: [87.05, 26.60],
      default_zoom: 10.5,
      historical_events: [
        {
          name: '2024 Late Monsoon Extreme Flood',
          date_range: '2024-09-26 to 2024-10-02',
          affected_population: 120000,
          notes: 'Unprecedented late-season atmospheric depression causing Koshi barrage peak discharge > 661,000 cusecs.'
        }
      ]
    },
    {
      id: 'bagmati_rautahat',
      name: 'Bagmati & Lalbakaiya Basin (Central Terai)',
      district: 'Rautahat / Sarlahi',
      province: 'Madhesh Province',
      description: 'Recurrent flash and riverine flooding around Gaur, Malangwa, and confluence plains.',
      bbox: [85.15, 26.70, 85.65, 27.10],
      center: [85.40, 26.90],
      default_zoom: 11,
      historical_events: []
    },
    {
      id: 'west_rapti_banke',
      name: 'West Rapti Basin (Western Terai)',
      district: 'Banke',
      province: 'Lumbini Province',
      description: 'Downstream Rapti river floodplain including Holiya, Fattepur, and Nepalgunj outskirts.',
      bbox: [81.50, 27.90, 82.00, 28.25],
      center: [81.75, 28.08],
      default_zoom: 11,
      historical_events: []
    }
  ]);

  const [activeStudyArea, setActiveStudyArea] = useState<StudyArea>(studyAreas[0]);
  const [activeParams, setActiveParams] = useState<AnalysisRunRequest>({
    study_area_id: 'koshi_basin',
    pre_flood_date_start: '2024-09-01',
    pre_flood_date_end: '2024-09-25',
    post_flood_date_start: '2024-09-26',
    post_flood_date_end: '2024-10-15',
    max_cloud_cover_percent: 50.0,
    water_index: 'MNDWI',
    water_threshold: 0.05,
    filter_permanent_water: true,
    min_mapping_unit_pixels: 5,
    data_source: 'Sentinel-2 L2A (Harmonized)',
    enable_mosaicing: true,
    sensor_mode: 'SENTINEL_2_OPTICAL'
  });
  const [settlements, setSettlements] = useState<SettlementImpact[]>([]);
  const [selectedSettlement, setSelectedSettlement] = useState<SettlementImpact | null>(null);
  const [analysisResult, setAnalysisResult] = useState<FloodAnalysisResult | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [loadingStage, setLoadingStage] = useState<string>('Initializing satellite ingestion...');
  const [loadingProgress, setLoadingProgress] = useState<number>(0);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);
  const requestSeqRef = useRef<number>(0);
  const activeStudyAreaRef = useRef<StudyArea>(activeStudyArea);
  activeStudyAreaRef.current = activeStudyArea;

  // Load study areas and initial data
  useEffect(() => {
    const initData = async () => {
      try {
        const areas = await api.getStudyAreas();
        if (areas && areas.length > 0) {
          setStudyAreas(areas);
          setActiveStudyArea(areas[0]);
        }
      } catch (err) {
        console.warn('API study areas offline, using calibrated defaults:', err);
      }

      // Run default analysis on mount for immediate rich visualization with verified cloud-calibrated window
      handleRunAnalysis({
        study_area_id: 'koshi_basin',
        pre_flood_date_start: '2024-09-01',
        pre_flood_date_end: '2024-09-25',
        post_flood_date_start: '2024-09-26',
        post_flood_date_end: '2024-10-15',
        max_cloud_cover_percent: 50.0,
        water_index: 'MNDWI',
        water_threshold: 0.05,
        filter_permanent_water: true,
        min_mapping_unit_pixels: 5,
        data_source: 'Sentinel-2 L2A (Harmonized)',
        enable_mosaicing: true,
        sensor_mode: 'SENTINEL_2_OPTICAL'
      });
    };

    initData();
  }, []);

  // Update settlements when study area changes
  useEffect(() => {
    const fetchSettlements = async () => {
      try {
        const data = await api.getSettlements(activeStudyArea.id);
        if (data && data.length > 0) {
          setSettlements(data);
        }
      } catch (err) {
        console.warn('Using existing settlements:', err);
      }
    };
    fetchSettlements();
  }, [activeStudyArea]);

  const handleRunAnalysis = async (params: AnalysisRunRequest) => {
    // If an analysis is already in progress, cancel it gracefully to prioritize the new user action
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      api.cancelActiveJob().catch(() => {});
    }

    const currentSeq = ++requestSeqRef.current;
    setActiveParams(params);
    setIsLoading(true);
    setLoadingStage('Querying Copernicus STAC for Real Satellite Scenes...');
    setLoadingProgress(10);
    setErrorMsg(null);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    // Real-time backend job polling
    const pollInterval = setInterval(async () => {
      if (currentSeq !== requestSeqRef.current) {
        clearInterval(pollInterval);
        return;
      }
      try {
        const job = await api.getActiveJob();
        if (job && job.status === 'processing') {
          if (job.stage) setLoadingStage(job.stage);
          if (typeof job.progress_percent === 'number') setLoadingProgress(job.progress_percent);
        } else if (job && job.status === 'failed') {
          clearInterval(pollInterval);
          setIsLoading(false);
          setErrorMsg(job.error || 'Flood detection pipeline failed.');
        }
      } catch {
        // Non-blocking poll failure
      }
    }, 750);

    try {
      const res = await api.runAnalysis(params, controller.signal);
      // Discard stale response if a newer request was dispatched
      if (currentSeq !== requestSeqRef.current) return;

      // Ensure the returned result matches the requested study area
      if (res.study_area && res.study_area.id !== params.study_area_id) {
        console.warn('Discarding mismatched study area result:', res.study_area.id, 'expected:', params.study_area_id);
        return;
      }

      setAnalysisResult(res);
      if (res.impact_summary && res.impact_summary.settlements) {
        setSettlements(res.impact_summary.settlements);
      }
      setLoadingProgress(100);
      setLoadingStage('Analysis Complete');
    } catch (err: any) {
      if (currentSeq !== requestSeqRef.current) return;
      if (err.name === 'AbortError') {
        return;
      }
      console.error('Analysis execution failed:', err);
      setErrorMsg(err.message || 'Failed to execute flood detection engine.');
    } finally {
      clearInterval(pollInterval);
      if (currentSeq === requestSeqRef.current) {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    }
  };

  const handleCancelAnalysis = async () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    try {
      await api.cancelActiveJob();
    } catch {
      // ignore
    }
    setIsLoading(false);
    setErrorMsg('Analysis dismissed. Base map and previously cached metrics unlocked.');
  };

  const handleSelectStudyArea = (area: StudyArea) => {
    setActiveStudyArea(area);
    setAnalysisResult(null); // Clear mismatched previous flood results
    setSelectedSettlement(null); // Clear previous settlement selection
    const updatedParams: AnalysisRunRequest = {
      ...activeParams,
      study_area_id: area.id
    };
    setActiveParams(updatedParams);
    handleRunAnalysis(updatedParams);
  };

  return (
    <div className="relative h-screen max-h-screen bg-command-950 text-slate-100 flex flex-col font-sans overflow-hidden select-none">
      {/* 3D Cinematic Earth Opening Sequence */}
      {showIntro && (
        <CinematicGlobeIntro onComplete={() => setShowIntro(false)} />
      )}

      {/* Persistent 3D Atmospheric Background */}
      <AtmosphericBackground />

      {/* Top Command Center Navigation */}
      <TopNav
        studyAreas={studyAreas}
        activeStudyArea={activeStudyArea}
        onSelectStudyArea={handleSelectStudyArea}
        analysisResult={analysisResult}
        activeParams={activeParams}
        onOpenReports={() => setActiveTab('reports')}
        onOpenSettings={() => setActiveTab('settings')}
      />

      {/* Main Workspace Body */}
      <div className="flex-1 flex overflow-hidden relative z-10 min-h-0">
        {/* Left Navigation Rail */}
        <SidebarRail
          activeTab={activeTab}
          onSelectTab={(tab) => setActiveTab(tab)}
          isCollapsed={isSidebarCollapsed}
          onToggleCollapse={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
        />

        {/* Center Viewport */}
        <main className="flex-1 relative flex flex-col overflow-hidden bg-command-950/60 min-h-0">
          {errorMsg && (
            <div className="absolute top-4 left-1/2 -translate-x-1/2 z-50 bg-rose-950/90 border border-rose-500 text-rose-200 px-4 py-2 rounded-lg text-xs font-mono shadow-2xl flex items-center space-x-2">
              <span>{errorMsg}</span>
              <button onClick={() => setErrorMsg(null)} className="ml-2 font-bold hover:text-white">&times;</button>
            </div>
          )}

          {/* Conditional View Rendering */}
          <div className={`flex-1 relative min-h-0 ${activeTab === 'map' ? 'overflow-hidden' : 'overflow-y-auto'}`}>
            {activeTab === 'map' && (
              <ErrorBoundary fallbackTitle="Geospatial Map Rendering Exception">
                <GeospatialMap
                  studyArea={activeStudyArea}
                  settlements={settlements}
                  analysisResult={analysisResult}
                  selectedSettlement={selectedSettlement}
                  onSelectSettlement={setSelectedSettlement}
                  isLoading={isLoading}
                  loadingStage={loadingStage}
                  loadingProgress={loadingProgress}
                  onDismissLoading={handleCancelAnalysis}
                />
              </ErrorBoundary>
            )}

            {activeTab === 'overview' && (
              <OverviewView
                studyAreas={studyAreas}
                activeStudyArea={activeStudyArea}
                onSelectStudyArea={(area) => {
                  handleSelectStudyArea(area);
                  setActiveTab('map');
                }}
                onNavigateToAnalysis={() => setActiveTab('analysis')}
                analysisResult={analysisResult}
              />
            )}

            {activeTab === 'analysis' && (
              <FloodAnalysisView
                studyArea={activeStudyArea}
                activeParams={activeParams}
                onUpdateParams={setActiveParams}
                onRunAnalysis={(params) => {
                  handleRunAnalysis(params);
                  setActiveTab('map');
                }}
                analysisResult={analysisResult}
                isLoading={isLoading}
              />
            )}

            {activeTab === 'satellite' && (
              <SatelliteImageryView
                analysisResult={analysisResult}
                studyArea={activeStudyArea}
                onTriggerAnalysis={() => {
                  handleRunAnalysis({
                    ...activeParams,
                    study_area_id: activeStudyArea.id
                  });
                }}
                onNavigateToAnalysis={() => setActiveTab('analysis')}
              />
            )}

            {activeTab === 'impact' && (
              <SettlementImpactView
                impactSummary={analysisResult?.impact_summary || null}
                onSelectSettlement={setSelectedSettlement}
                onNavigateToMap={() => setActiveTab('map')}
              />
            )}

            {activeTab === 'validation' && (
              <ValidationView analysisResult={analysisResult} />
            )}

            {activeTab === 'reports' && (
              <ReportsExportView analysisResult={analysisResult} />
            )}

            {activeTab === 'settings' && (
              <SettingsView />
            )}
          </div>

          {/* Bottom Analysis Timeline */}
          <TimelineBar
            analysisResult={analysisResult}
            activeStudyArea={activeStudyArea}
            activeParams={activeParams}
            onRunAnalysis={() => {
              if (activeStudyArea) {
                handleRunAnalysis({
                  ...activeParams,
                  study_area_id: activeStudyArea.id
                });
              }
            }}
            isLoading={isLoading}
            loadingStage={loadingStage}
            loadingProgress={loadingProgress}
          />
        </main>

        {/* Right Live Analysis Panel (Visible on Map and Analysis Views) */}
        {activeTab === 'map' && (
          <RightAnalysisPanel
            analysisResult={analysisResult}
            selectedSettlement={selectedSettlement}
            onSelectSettlement={setSelectedSettlement}
            onOpenReport={() => setActiveTab('reports')}
            isLoading={isLoading}
            loadingStage={loadingStage}
            loadingProgress={loadingProgress}
          />
        )}
      </div>
    </div>
  );
};

export default App;
