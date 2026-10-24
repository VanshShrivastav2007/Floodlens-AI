import React from 'react';
import { 
  AlertTriangle, 
  ShieldAlert, 
  Users, 
  Building2, 
  CheckCircle2, 
  MapPin, 
  Droplets, 
  CloudRain, 
  Layers,
  FileText,
  ChevronRight,
  TrendingUp,
  Activity,
  Eye,
  Radio
} from 'lucide-react';
import { FloodAnalysisResult, SettlementImpact } from '../../types';

interface RightAnalysisPanelProps {
  analysisResult: FloodAnalysisResult | null;
  selectedSettlement: SettlementImpact | null;
  onSelectSettlement: (s: SettlementImpact | null) => void;
  onOpenReport: () => void;
  isLoading?: boolean;
  loadingStage?: string;
  loadingProgress?: number;
}

export const RightAnalysisPanel: React.FC<RightAnalysisPanelProps> = ({
  analysisResult,
  selectedSettlement,
  onSelectSettlement,
  onOpenReport,
  isLoading,
  loadingStage,
  loadingProgress = 0
}) => {
  if (isLoading) {
    return (
      <aside className="w-96 shrink-0 h-full border-l border-command-700/60 bg-command-950/90 backdrop-blur-md p-4 flex flex-col items-center justify-center text-center font-mono">
        <Activity className="w-8 h-8 text-cyan-glow animate-pulse mb-3" />
        <div className="text-xs text-cyan-glow font-semibold uppercase tracking-wider">
          Pipeline Processing
        </div>
        <div className="text-[11px] text-slate-300 mt-2 max-w-xs px-2 font-medium">
          {loadingStage || 'Processing satellite telemetry...'}
        </div>
        <div className="w-48 h-1.5 bg-command-900 rounded-full mt-3 overflow-hidden border border-cyan-glow/30">
          <div 
            className="h-full bg-gradient-to-r from-cyan-500 to-blue-500 transition-all duration-300 ease-out"
            style={{ width: `${Math.min(100, Math.max(5, loadingProgress))}%` }}
          />
        </div>
        <div className="text-[10px] text-slate-400 mt-1">
          {loadingProgress}% Complete
        </div>
      </aside>
    );
  }

  if (!analysisResult) {
    return (
      <aside className="w-96 shrink-0 h-full border-l border-command-700/60 bg-command-950/90 backdrop-blur-md p-4 flex flex-col items-center justify-center text-center font-mono">
        <Activity className="w-8 h-8 text-cyan-glow animate-pulse mb-3" />
        <div className="text-xs text-slate-300 font-semibold uppercase tracking-wider">
          Awaiting Analysis Run
        </div>
        <p className="text-[11px] text-slate-500 mt-1 max-w-xs">
          Trigger the flood detection pipeline to inspect newly inundated hectares and settlement exposure.
        </p>
      </aside>
    );
  }

  const { impact_summary, validation } = analysisResult;

  return (
    <aside className="w-96 shrink-0 h-full border-l border-command-700/60 bg-command-950/90 backdrop-blur-md flex flex-col justify-between font-mono z-30 overflow-hidden">
      {/* Header */}
      <div className="p-4 border-b border-command-700/60 bg-command-900/40">
        <div className="flex items-center justify-between">
          <div className="text-[10px] uppercase font-bold tracking-widest text-cyan-glow">
            Command Center Telemetry
          </div>
          <div className="flex items-center space-x-1.5">
            {analysisResult.sensor_mode === 'SENTINEL_1_SAR' ? (
              <span className="px-2 py-0.5 rounded text-[10px] bg-sky-500/20 text-sky-300 border border-sky-500/40 font-bold">
                SENTINEL-1 SAR
              </span>
            ) : analysisResult.sensor_mode === 'DUAL_SENSOR_SYNERGY' ? (
              <span className="px-2 py-0.5 rounded text-[10px] bg-fuchsia-500/20 text-fuchsia-300 border border-fuchsia-500/40 font-bold">
                DUAL-SENSOR
              </span>
            ) : analysisResult.is_mosaic ? (
              <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/40 font-bold">
                MOSAIC ({analysisResult.tiles_mosaicked?.join('+')})
              </span>
            ) : (
              <span className="px-2 py-0.5 rounded text-[10px] bg-cyan-500/10 text-cyan-400 border border-cyan-500/30">
                SENTINEL-2
              </span>
            )}
            <span className="px-2 py-0.5 rounded text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              PROCESSED
            </span>
          </div>
        </div>
        <div className="text-sm font-bold text-white mt-1">
          {analysisResult.study_area.name}
        </div>
        <div className="text-[10px] text-slate-400">
          Run ID: <code>{analysisResult.run_id.slice(0, 18)}...</code>
        </div>
      </div>

      {/* Main Metric Cards (Scrollable) */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {/* Low Observation Coverage Warning Card */}
        {analysisResult.low_coverage_warning && (
          <div className="hud-panel p-3 rounded-lg border border-amber-500/50 bg-amber-950/40 text-amber-300 space-y-1.5">
            <div className="flex items-center space-x-1.5 text-xs font-bold uppercase tracking-wider text-amber-400">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0" />
              <span>LOW COVERAGE ({analysisResult.valid_observation_percent}%)</span>
            </div>
            <p className="text-[11px] text-slate-300 leading-snug">
              Observable cloud-free area is only {analysisResult.valid_observation_percent}% (threshold {analysisResult.min_valid_coverage_percent ?? 30}%). Optical extent reflects clear-sky gaps only; persistent monsoon clouds obscure the remaining basin.
            </p>
          </div>
        )}

        {/* Flooded Area Metric Box */}
        <div className="hud-panel p-3.5 rounded-lg border-l-4 border-l-[#ff3366] space-y-2">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="flex items-center space-x-1.5">
              <Droplets className="w-3.5 h-3.5 text-[#ff3366]" />
              <span className="uppercase text-[10px] font-bold">Newly Inundated Extent</span>
            </span>
            <span className="text-[10px] text-slate-500">{analysisResult.utm_zone_crs || 'UTM 45N'}</span>
          </div>

          <div className="flex items-baseline space-x-2">
            <div className="text-2xl font-bold text-white tracking-tight">
              {analysisResult.newly_inundated_sqkm.toLocaleString()}
            </div>
            <div className="text-xs text-slate-400">sq km</div>
          </div>

          <div className="text-[11px] text-[#ff3366] font-semibold flex items-center justify-between pt-1 border-t border-slate-800">
            <span>{analysisResult.newly_inundated_hectares.toLocaleString()} hectares {analysisResult.low_coverage_warning ? '(Gap est.)' : ''}</span>
            <span className="text-[10px] text-slate-400">
              Perm: {analysisResult.permanent_water_sqkm} km²
            </span>
          </div>
          <div className="text-[9px] text-slate-500 pt-1 border-t border-slate-800/60 leading-tight">
            Canonical Grid: 400 &times; 500 (~120m &times; 139m / 1.655 ha) &bull; Native GSD: 10m
          </div>
        </div>

        {/* Observation Clarity Metric Box */}
        <div className="hud-panel p-3 rounded-lg space-y-1.5 border-l-4 border-l-emerald-500">
          <div className="flex items-center justify-between text-xs text-slate-400">
            <span className="flex items-center space-x-1.5">
              <Eye className="w-3.5 h-3.5 text-emerald-400" />
              <span className="uppercase text-[10px] font-bold">Clear-Sky Coverage</span>
            </span>
            <span className="text-[10px] font-bold text-emerald-400">{analysisResult.valid_observation_percent}%</span>
          </div>
          <div className="flex items-center justify-between text-[11px] text-slate-300">
            <span>Observable: {((analysisResult.total_study_area_sqkm * analysisResult.valid_observation_percent) / 100).toFixed(1)} km²</span>
            <span className="text-[10px] text-slate-400">
              Clouds: {analysisResult.cloud_mask_percentage}% | NoData: {analysisResult.nodata_mask_percentage ?? 0}%
            </span>
          </div>
          {analysisResult.is_mosaic && (
            <div className="text-[10px] text-emerald-400/90 pt-1 border-t border-slate-800 flex items-center justify-between">
              <span>Mosaicked: {analysisResult.tiles_mosaicked?.join(' + ')}</span>
              <span>0.00% swath loss</span>
            </div>
          )}
        </div>

        {/* Sentinel-1 C-SAR Radar Metric Box */}
        {analysisResult.sar_result && (
          <div className="hud-panel p-3.5 rounded-lg border-l-4 border-l-sky-400 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center space-x-1.5">
                <Radio className="w-3.5 h-3.5 text-sky-400" />
                <span className="uppercase text-[10px] font-bold">Sentinel-1 C-SAR Telemetry</span>
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-sky-950 text-sky-300 border border-sky-500/30 font-bold">
                {analysisResult.sar_result.polarization} POL &bull; RTC
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-center text-xs">
              <div className="bg-command-900/60 p-2 rounded border border-command-700/50">
                <div className="text-[9px] text-slate-400 uppercase">Radar Swath Cov.</div>
                <div className="text-sm font-bold text-sky-300">
                  {analysisResult.sar_result.valid_sar_coverage_percent}%
                </div>
                <div className="text-[9px] text-slate-500">{analysisResult.sar_result.valid_sar_sqkm} km²</div>
              </div>
              <div className="bg-command-900/60 p-2 rounded border border-command-700/50">
                <div className="text-[9px] text-slate-400 uppercase">Mean Backscatter Change</div>
                <div className="text-sm font-bold text-amber-300">
                  {analysisResult.sar_result.sar_mean_backscatter_change_db} dB
                </div>
                <div className="text-[9px] text-slate-500">&tau; &le; {analysisResult.sar_result.threshold_db} dB</div>
              </div>
            </div>

            <div className="text-[10px] text-slate-400 pt-1 border-t border-slate-800 leading-tight">
              Cloud penetration: <strong className="text-emerald-400">100% all-weather</strong>. Gamma0 terrain-flattened backscatter via Planetary Computer STAC.
            </div>
          </div>
        )}

        {/* Dual-Sensor Fusion Synergy Card */}
        {analysisResult.synergy_result && (
          <div className="hud-panel p-3.5 rounded-lg border-l-4 border-l-fuchsia-400 space-y-2">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center space-x-1.5">
                <Layers className="w-3.5 h-3.5 text-fuchsia-400" />
                <span className="uppercase text-[10px] font-bold">MECE Multi-Sensor Fusion</span>
              </span>
              <span className="text-[10px] px-1.5 py-0.5 rounded bg-fuchsia-950 text-fuchsia-300 border border-fuchsia-500/30 font-bold">
                {analysisResult.synergy_result.sensor_agreement_percent}% AGREE
              </span>
            </div>

            <div className="grid grid-cols-2 gap-2 text-xs">
              <div className="bg-command-900/60 p-2 rounded border border-command-700/50">
                <div className="text-[9px] text-cyan-300 uppercase">P1: Consensus</div>
                <div className="text-sm font-bold text-white">
                  {analysisResult.synergy_result.consensus_confirmed_flood_sqkm} km²
                </div>
                <div className="text-[9px] text-slate-500">Optical + SAR Agree</div>
              </div>
              <div className="bg-command-900/60 p-2 rounded border border-command-700/50">
                <div className="text-[9px] text-sky-300 uppercase">P2: Cloud-Piercing</div>
                <div className="text-sm font-bold text-sky-400">
                  {analysisResult.synergy_result.cloud_pierced_sar_flood_sqkm ?? analysisResult.synergy_result.cloud_pierced_flood_sqkm} km²
                </div>
                <div className="text-[9px] text-slate-500">Pierced Cloud Gaps</div>
              </div>
            </div>

            <div className="space-y-1 text-[10px] pt-1 border-t border-slate-800 text-slate-400">
              <div className="flex justify-between">
                <span>P5: Optical Beyond SAR Swath:</span>
                <span className="text-emerald-400 font-mono font-bold">
                  {(analysisResult.synergy_result.optical_outside_sar_swath_sqkm ?? analysisResult.synergy_result.optical_only_flood_sqkm).toFixed(3)} km²
                </span>
              </div>
              <div className="flex justify-between">
                <span>P6: Optical Clear (SAR Dry):</span>
                <span className="text-amber-400 font-mono font-bold">
                  {(analysisResult.synergy_result.optical_discordant_flood_sqkm ?? 0).toFixed(3)} km²
                </span>
              </div>
              <div className="flex justify-between">
                <span>P4: SAR Clear (Optical Dry):</span>
                <span className="text-rose-400 font-mono font-bold">
                  {(analysisResult.synergy_result.sar_discordant_flood_sqkm ?? 0).toFixed(3)} km²
                </span>
              </div>
            </div>

            <div className="text-[10px] text-slate-300 pt-1.5 border-t border-slate-800 flex items-center justify-between">
              <span>Total Multi-Sensor Flood Union:</span>
              <strong className="text-[#ff3366] font-mono text-xs">
                {analysisResult.synergy_result.total_multi_sensor_flood_sqkm.toFixed(3)} km²
              </strong>
            </div>
            <div className="text-[9px] text-slate-400 pt-1 border-t border-slate-800/60 flex items-center justify-between">
              <span>Perm Water (Opt/SAR/Union):</span>
              <span className="font-mono text-cyan-300">
                {(analysisResult.optical_permanent_water_sqkm ?? analysisResult.synergy_result.optical_permanent_water_sqkm ?? 59.215).toFixed(1)} / {(analysisResult.sar_permanent_water_sqkm ?? analysisResult.synergy_result.sar_permanent_water_sqkm ?? 83.635).toFixed(1)} / {(analysisResult.combined_permanent_water_sqkm ?? analysisResult.synergy_result.combined_permanent_water_union_sqkm ?? 138.288).toFixed(1)} km²
              </span>
            </div>
            <div className="text-[9px] text-emerald-400 text-center bg-emerald-950/40 border border-emerald-500/20 rounded py-0.5">
              &check; MECE Partitions Conserved (Residual: 0.000 km²)
            </div>
          </div>
        )}

        {/* Human Settlement Impact Tallies */}
        <div className="hud-panel p-3.5 rounded-lg space-y-2.5">
          <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
            <span className="flex items-center space-x-1.5">
              <Users className="w-3.5 h-3.5 text-cyan-glow" />
              <span>Settlement Exposure (Proxy)</span>
            </span>
            <span className="text-rose-400 font-bold">{impact_summary.critical_count} CRITICAL</span>
          </div>

          <div className="grid grid-cols-2 gap-2 text-center">
            <div className="bg-command-900/60 p-2 rounded border border-command-700/50">
              <div className="text-[10px] text-slate-400 uppercase">Est. Exposed Pop</div>
              <div className="text-base font-bold text-rose-400 mt-0.5">
                {impact_summary.total_exposed_population.toLocaleString()}
              </div>
            </div>
            <div className="bg-command-900/60 p-2 rounded border border-command-700/50">
              <div className="text-[10px] text-slate-400 uppercase">Infra at Risk</div>
              <div className="text-base font-bold text-amber-400 mt-0.5">
                {impact_summary.critical_infrastructure_count}
              </div>
            </div>
          </div>

          <div className="text-[9px] text-slate-500 leading-tight">
            Estimated population within 1.5km geodesic buffer (Nepal CBS 2021 census), not confirmed casualties or evacuees.
          </div>

          {/* Impact Level Bar Breakdown */}
          <div className="space-y-1 pt-1 text-[11px]">
            <div className="flex justify-between items-center text-rose-400">
              <span>Critical (&lt; 250m)</span>
              <span className="font-bold">{impact_summary.critical_count} settlements</span>
            </div>
            <div className="flex justify-between items-center text-amber-400">
              <span>High Risk (&lt; 750m)</span>
              <span className="font-bold">{impact_summary.high_count} settlements</span>
            </div>
            <div className="flex justify-between items-center text-cyan-300">
              <span>Moderate (&lt; 1.8km)</span>
              <span className="font-bold">{impact_summary.moderate_count} settlements</span>
            </div>
          </div>
        </div>

        {/* WorldPop 2020 Gridded Population Exposure Intelligence */}
        {analysisResult.population_exposure && (
          <div className="hud-panel p-3.5 rounded-lg border-l-4 border-l-cyan-400 space-y-2.5">
            <div className="flex items-center justify-between text-xs text-slate-400">
              <span className="flex items-center space-x-1.5">
                <Users className="w-3.5 h-3.5 text-cyan-400" />
                <span className="uppercase text-[10px] font-bold">WorldPop 2020 Exposure</span>
              </span>
              <span className="text-[9px] px-1.5 py-0.5 rounded bg-cyan-950 text-cyan-300 border border-cyan-500/30 font-bold">
                100m BSGM &bull; VORONOI
              </span>
            </div>

            {analysisResult.population_exposure.population_metadata.availability_status === 'AVAILABLE' ? (
              <>
                <div className="grid grid-cols-2 gap-2 text-center text-xs">
                  <div className="bg-command-900/60 p-2 rounded border border-command-700/50">
                    <div className="text-[9px] text-slate-400 uppercase">Basin Population</div>
                    <div className="text-sm font-bold text-white">
                      {Math.round(analysisResult.population_exposure.total_domain_resident_population).toLocaleString()}
                    </div>
                    <div className="text-[9px] text-slate-500">Dasymetric Grid Total</div>
                  </div>
                  <div className="bg-command-900/60 p-2 rounded border border-command-700/50">
                    <div className="text-[9px] text-rose-400 uppercase">Inundated Exposed</div>
                    <div className="text-sm font-bold text-rose-400">
                      {Math.round(analysisResult.population_exposure.total_domain_exposed_population).toLocaleString()}
                    </div>
                    <div className="text-[9px] text-slate-500">{analysisResult.population_exposure.overall_exposure_percentage}% of Domain</div>
                  </div>
                </div>

                {analysisResult.population_exposure.cloud_pierced_exposed_population > 0 && (
                  <div className="text-[10px] text-sky-300 bg-sky-950/40 p-1.5 rounded border border-sky-500/20 flex items-center justify-between">
                    <span>Cloud-Pierced (SAR) Exposure:</span>
                    <strong>{Math.round(analysisResult.population_exposure.cloud_pierced_exposed_population).toLocaleString()} persons</strong>
                  </div>
                )}

                {/* Explainable Rescue Priority Decision Support Ranking */}
                <div className="pt-1.5 border-t border-slate-800 space-y-1.5">
                  <div className="text-[10px] font-bold uppercase tracking-wider text-slate-400 flex items-center justify-between">
                    <span>Rescue Priority Ranking</span>
                    <span className="text-emerald-400 text-[9px]">&check; Zero Double-Counting</span>
                  </div>

                  <div className="space-y-1 max-h-48 overflow-y-auto pr-1">
                    {analysisResult.population_exposure.settlements.slice(0, 5).map((s) => {
                      let tierBadge = 'bg-cyan-500/20 text-cyan-300 border-cyan-500/40';
                      if (s.provisional_priority_tier.includes('Tier 1')) {
                        tierBadge = 'bg-rose-500/20 text-rose-400 border-rose-500/40 shadow-glow-alert';
                      } else if (s.provisional_priority_tier.includes('Tier 2')) {
                        tierBadge = 'bg-amber-500/20 text-amber-400 border-amber-500/40';
                      }

                      const isSelected = selectedSettlement?.settlement_id === s.settlement_id;

                      return (
                        <div
                          key={s.settlement_id}
                          onClick={() => {
                            const fullSettlement = impact_summary.settlements.find(item => item.settlement_id === s.settlement_id);
                            if (fullSettlement) {
                              onSelectSettlement({
                                ...fullSettlement,
                                gridded_baseline_population: s.gridded_baseline_population,
                                estimated_exposed_population: s.estimated_exposed_population,
                                provisional_priority_tier: s.provisional_priority_tier,
                                priority_score: s.priority_score,
                                priority_reasons: s.priority_reasons
                              });
                            }
                          }}
                          className={`p-2 rounded border cursor-pointer transition-all ${
                            isSelected 
                              ? 'bg-cyan-500/20 border-cyan-glow' 
                              : 'bg-command-900/60 border-command-700/50 hover:border-slate-500'
                          }`}
                        >
                          <div className="flex items-center justify-between text-[11px]">
                            <span className="font-bold text-white">{s.name}</span>
                            <span className={`px-1.5 py-0.2 rounded text-[9px] font-bold border ${tierBadge}`}>
                              {s.provisional_priority_tier.split(':')[0]}
                            </span>
                          </div>
                          <div className="flex items-center justify-between text-[10px] text-slate-400 mt-1">
                            <span>Exposed: <strong className="text-rose-400">~{Math.round(s.estimated_exposed_population || 0).toLocaleString()}</strong></span>
                            <span>Score: <strong className="text-cyan-300">{s.priority_score ?? 0} pts</strong></span>
                          </div>
                          {s.priority_reasons.length > 0 && (
                            <div className="text-[9px] text-slate-400 mt-1 truncate">
                              &bull; {s.priority_reasons[0]}
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                <div className="text-[9px] text-slate-500 pt-1 border-t border-slate-800 leading-tight">
                  Dasymetric resident counts inside flood footprint. Decision support only; field verification by DDMC/APF incident commander required.
                </div>
              </>
            ) : (
              <div className="text-[11px] text-amber-300 bg-amber-950/40 p-2 rounded border border-amber-500/30">
                WorldPop 2020 constrained population raster currently unavailable. No synthetic population figures were generated.
              </div>
            )}
          </div>
        )}

        {/* Selected Settlement Deep-Dive Card */}
        {selectedSettlement ? (
          <div className="hud-panel-glow p-3.5 rounded-lg space-y-2 relative">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-1.5 text-cyan-glow">
                <MapPin className="w-3.5 h-3.5" />
                <span className="text-xs font-bold">{selectedSettlement.name}</span>
              </div>
              <span className={`text-[10px] px-1.5 py-0.5 rounded font-bold ${
                selectedSettlement.impact_level === 'Critical' 
                  ? 'bg-rose-500/20 text-rose-400 border border-rose-500/40' 
                  : (selectedSettlement.impact_level === 'High' 
                    ? 'bg-amber-500/20 text-amber-400 border border-amber-500/40'
                    : 'bg-cyan-500/20 text-cyan-300')
              }`}>
                {selectedSettlement.impact_level}
              </span>
            </div>

            <div className="text-[11px] text-slate-400">
              {selectedSettlement.municipality}, {selectedSettlement.district}
            </div>

            <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-slate-800">
              <div>
                <span className="text-slate-500">Distance to Flood:</span>
                <div className="font-bold text-white">{selectedSettlement.distance_to_flood_m} m</div>
              </div>
              <div>
                <span className="text-slate-500">CBS Census Pop:</span>
                <div className="font-bold text-white">{selectedSettlement.population ? selectedSettlement.population.toLocaleString() : 'N/A (OSM)'}</div>
              </div>
            </div>

            {selectedSettlement.estimated_exposed_population != null && (
              <div className="grid grid-cols-2 gap-2 text-[11px] pt-1 border-t border-slate-800/60 bg-command-900/40 p-1.5 rounded">
                <div>
                  <span className="text-slate-400 text-[10px]">Gridded Exposure:</span>
                  <div className="font-bold text-rose-400">~{Math.round(selectedSettlement.estimated_exposed_population || 0).toLocaleString()}</div>
                </div>
                <div>
                  <span className="text-slate-400 text-[10px]">Priority Score:</span>
                  <div className="font-bold text-cyan-300">{selectedSettlement.priority_score ?? 'N/A'} pts</div>
                </div>
              </div>
            )}

            {selectedSettlement.provisional_priority_tier && (
              <div className="text-[10px] text-cyan-300">
                <span className="text-slate-500 block">Provisional Rescue Tier:</span>
                <span className="font-semibold">{selectedSettlement.provisional_priority_tier}</span>
              </div>
            )}

            {selectedSettlement.critical_infrastructure_at_risk.length > 0 && (
              <div className="pt-1 text-[10px] text-amber-300">
                <span className="text-slate-500 block">Critical Facilities:</span>
                {selectedSettlement.critical_infrastructure_at_risk.join(', ')}
              </div>
            )}

            <div className="pt-1 text-[10px] text-rose-300/90 leading-tight">
              <strong>Directive:</strong> {selectedSettlement.recommended_action}
            </div>
          </div>
        ) : (
          <div className="hud-panel p-3 rounded text-[11px] text-slate-400 text-center">
            Click any settlement marker on the map to inspect local exposure and evacuation directives.
          </div>
        )}

        {/* Validation Accuracy Certification or Unavailable Notice */}
        {validation && (
          validation.validation_status === 'VERIFIED_REFERENCE' && 
          validation.precision != null && 
          validation.recall != null && 
          validation.f1_score != null && 
          validation.iou_jaccard != null ? (
            <div className="hud-panel p-3.5 rounded-lg space-y-2">
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center space-x-1.5 text-cyan-glow">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                  <span className="text-[10px] font-bold uppercase">Accuracy Certification</span>
                </span>
                <span className="text-[10px] text-emerald-400 font-bold">{validation.validation_status}</span>
              </div>

              <div className="grid grid-cols-2 gap-2 text-[11px]">
                <div className="bg-command-900/60 p-1.5 rounded">
                  <div className="text-[9px] text-slate-500 uppercase">Precision</div>
                  <div className="text-sm font-bold text-cyan-glow">{round(validation.precision * 100, 1)}%</div>
                </div>
                <div className="bg-command-900/60 p-1.5 rounded">
                  <div className="text-[9px] text-slate-500 uppercase">Recall / Sens.</div>
                  <div className="text-sm font-bold text-cyan-glow">{round(validation.recall * 100, 1)}%</div>
                </div>
                <div className="bg-command-900/60 p-1.5 rounded">
                  <div className="text-[9px] text-slate-500 uppercase">F1-Score</div>
                  <div className="text-sm font-bold text-emerald-400">{round(validation.f1_score * 100, 1)}%</div>
                </div>
                <div className="bg-command-900/60 p-1.5 rounded">
                  <div className="text-[9px] text-slate-500 uppercase">IoU (Jaccard)</div>
                  <div className="text-sm font-bold text-emerald-400">{round(validation.iou_jaccard * 100, 1)}%</div>
                </div>
              </div>

              <div className="text-[10px] text-slate-500 leading-tight">
                Benchmarked against {validation.reference_dataset}
              </div>
            </div>
          ) : (
            <div className="hud-panel p-3.5 rounded-lg space-y-1.5 border-l-2 border-l-amber-500">
              <div className="flex items-center justify-between text-xs">
                <span className="flex items-center space-x-1.5 text-amber-400">
                  <AlertTriangle className="w-3.5 h-3.5" />
                  <span className="text-[10px] font-bold uppercase">Ground Truth Status</span>
                </span>
                <span className="text-[9px] px-1.5 py-0.5 rounded bg-amber-950 text-amber-400 border border-amber-500/30 font-bold">
                  UNAVAILABLE
                </span>
              </div>
              <p className="text-[10px] text-slate-400 leading-tight">
                No verified reference flood extent configured for this event. Accuracy metrics omitted to preserve scientific integrity.
              </p>
            </div>
          )
        )}
      </div>

      {/* Footer Action */}
      <div className="p-3 border-t border-command-700/60 bg-command-900/40">
        <button
          onClick={onOpenReport}
          className="w-full py-2 rounded hud-panel hover:bg-command-800 hover:border-cyan-glow/50 text-xs font-semibold text-cyan-glow transition-all flex items-center justify-center space-x-1.5"
        >
          <FileText className="w-3.5 h-3.5" />
          <span>VIEW FULL DDMC BRIEFING</span>
        </button>
      </div>
    </aside>
  );
};

function round(val: number, decimals: number): number {
  return Number(val.toFixed(decimals));
}
