import React, { useState } from 'react';
import { 
  Users, 
  AlertTriangle, 
  ShieldAlert, 
  Building2, 
  MapPin, 
  Search, 
  Download, 
  ArrowUpDown,
  CheckCircle2,
  Filter
} from 'lucide-react';
import { SettlementImpact, SettlementImpactSummary, ImpactLevel } from '../../types';

interface SettlementImpactViewProps {
  impactSummary: SettlementImpactSummary | null;
  onSelectSettlement: (s: SettlementImpact) => void;
  onNavigateToMap: () => void;
}

export const SettlementImpactView: React.FC<SettlementImpactViewProps> = ({
  impactSummary,
  onSelectSettlement,
  onNavigateToMap
}) => {
  const [filterSeverity, setFilterSeverity] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  if (!impactSummary) {
    return (
      <div className="p-8 text-center font-mono text-slate-400">
        Run flood analysis to populate settlement impact exposure data.
      </div>
    );
  }

  const settlements = impactSummary.settlements.filter((s) => {
    const matchesSeverity = filterSeverity === 'ALL' || s.impact_level.toUpperCase() === filterSeverity;
    const matchesSearch = s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          s.municipality.toLowerCase().includes(searchQuery.toLowerCase()) ||
                          s.district.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesSeverity && matchesSearch;
  });

  const exportCSV = () => {
    const headers = [
      'Settlement ID', 'Name', 'Local Name', 'District', 'Municipality',
      'Census 2021 Pop', 'WorldPop Gridded Pop', 'Est Exposed Pop', 'Elevation (m)', 
      'Distance to Flood (m)', 'Impact Level', 'Provisional Priority Tier', 'Priority Score',
      'Priority Reasons', 'Exposure %', 'Critical Infrastructure', 'Recommended Action'
    ];

    const rows = impactSummary.settlements.map(s => [
      s.settlement_id,
      `"${s.name}"`,
      `"${s.local_name}"`,
      `"${s.district}"`,
      `"${s.municipality}"`,
      s.population,
      s.gridded_baseline_population ?? s.population,
      s.estimated_exposed_population ?? Math.round(s.population * (s.exposure_percentage / 100)),
      s.elevation_m,
      s.distance_to_flood_m,
      s.impact_level,
      `"${s.provisional_priority_tier ?? 'N/A'}"`,
      s.priority_score ?? 0,
      `"${(s.priority_reasons ?? []).join('; ')}"`,
      s.exposure_percentage,
      `"${s.critical_infrastructure_at_risk.join('; ')}"`,
      `"${s.recommended_action}"`
    ]);

    const csvContent = 'data:text/csv;charset=utf-8,' + [headers.join(','), ...rows.map(e => e.join(','))].join('\n');
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `nepal_terai_settlement_impact_${Date.now()}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="p-6 max-w-6xl mx-auto space-y-6 font-mono text-slate-200">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-command-700/60 pb-4">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2.5">
            <Users className="w-5 h-5 text-cyan-glow" />
            <span>Nepal Terai Settlement Exposure &amp; Vulnerability Register</span>
          </h2>
          <div className="text-xs text-slate-400 mt-1">
            Real Geographical Settlement Intersections with Optical Flood Extent
          </div>
        </div>

        <button
          onClick={exportCSV}
          className="px-3.5 py-1.5 rounded hud-panel hover:border-cyan-glow/50 text-xs text-cyan-glow flex items-center space-x-2 transition-all self-start sm:self-auto"
        >
          <Download className="w-3.5 h-3.5" />
          <span>EXPORT SETTLEMENT CSV</span>
        </button>
      </div>

      {/* Summary Stat Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="hud-panel p-4 rounded-xl border-l-4 border-l-rose-500 space-y-1">
          <div className="text-[10px] uppercase text-slate-400">Critical Priority</div>
          <div className="text-2xl font-bold text-rose-400">{impactSummary.critical_count}</div>
          <div className="text-[10px] text-slate-500">Inundation within 250m</div>
        </div>

        <div className="hud-panel p-4 rounded-xl border-l-4 border-l-amber-500 space-y-1">
          <div className="text-[10px] uppercase text-slate-400">High Risk</div>
          <div className="text-2xl font-bold text-amber-400">{impactSummary.high_count}</div>
          <div className="text-[10px] text-slate-500">Inundation within 750m</div>
        </div>

        <div className="hud-panel p-4 rounded-xl border-l-4 border-l-cyan-500 space-y-1">
          <div className="text-[10px] uppercase text-slate-400">Exposed Population</div>
          <div className="text-2xl font-bold text-cyan-glow">
            {impactSummary.total_exposed_population.toLocaleString()}
          </div>
          <div className="text-[10px] text-slate-500">Across high &amp; critical zones</div>
        </div>

        <div className="hud-panel p-4 rounded-xl border-l-4 border-l-blue-500 space-y-1">
          <div className="text-[10px] uppercase text-slate-400">Infra Compromised</div>
          <div className="text-2xl font-bold text-blue-400">{impactSummary.critical_infrastructure_count}</div>
          <div className="text-[10px] text-slate-500">Hospitals, sirens, substations</div>
        </div>
      </div>

      {/* Search & Filter Toolbar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3 hud-panel p-3 rounded-lg">
        {/* Search */}
        <div className="relative w-full sm:w-80">
          <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            placeholder="Search settlement, ward or district..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="w-full bg-command-950 border border-slate-700 rounded pl-9 pr-3 py-1.5 text-xs text-white placeholder-slate-500 focus:border-cyan-glow focus:outline-none"
          />
        </div>

        {/* Severity Filter Buttons */}
        <div className="flex items-center space-x-1.5 self-stretch sm:self-auto overflow-x-auto">
          {['ALL', 'CRITICAL', 'HIGH', 'MODERATE', 'SAFE'].map((lvl) => (
            <button
              key={lvl}
              onClick={() => setFilterSeverity(lvl)}
              className={`px-2.5 py-1 rounded text-[11px] uppercase transition-all whitespace-nowrap ${
                filterSeverity === lvl
                  ? 'bg-cyan-500/20 text-cyan-glow border border-cyan-glow/40 font-bold'
                  : 'text-slate-400 hover:text-white hover:bg-command-800'
              }`}
            >
              {lvl}
            </button>
          ))}
        </div>
      </div>

      {/* Data Table */}
      <div className="hud-panel rounded-xl overflow-hidden border border-command-700/60">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-command-900/80 text-slate-400 uppercase text-[10px] border-b border-command-700/60">
              <tr>
                <th className="p-3.5">Priority</th>
                <th className="p-3.5">Settlement (Local Name)</th>
                <th className="p-3.5">Ward &amp; District</th>
                <th className="p-3.5 text-right">Census Pop</th>
                <th className="p-3.5 text-right">WorldPop Exposed</th>
                <th className="p-3.5 text-right">Flood Distance</th>
                <th className="p-3.5">Critical Infrastructure</th>
                <th className="p-3.5">Operational Directive</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-command-700/40">
              {settlements.map((s) => {
                let badgeStyle = 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30';
                if (s.provisional_priority_tier?.includes('Tier 1') || s.impact_level === 'Critical') {
                  badgeStyle = 'bg-rose-500/20 text-rose-400 border-rose-500/40 shadow-glow-alert';
                } else if (s.provisional_priority_tier?.includes('Tier 2') || s.impact_level === 'High') {
                  badgeStyle = 'bg-amber-500/20 text-amber-400 border-amber-500/40';
                } else if (s.impact_level === 'Moderate') {
                  badgeStyle = 'bg-cyan-500/20 text-cyan-300 border-cyan-500/30';
                }

                return (
                  <tr
                    key={s.settlement_id}
                    onClick={() => {
                      onSelectSettlement(s);
                      onNavigateToMap();
                    }}
                    className="hover:bg-cyan-500/5 cursor-pointer transition-colors"
                  >
                    <td className="p-3.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-bold border inline-block ${badgeStyle}`}>
                        {s.provisional_priority_tier ? s.provisional_priority_tier.split(':')[0] : s.impact_level}
                      </span>
                      {s.priority_score != null && (
                        <div className="text-[9px] text-cyan-300/80 font-mono mt-0.5">{s.priority_score} pts</div>
                      )}
                    </td>
                    <td className="p-3.5">
                      <div className="font-bold text-white flex items-center space-x-1.5">
                        <span>{s.name}</span>
                        <span className="text-[11px] text-slate-400 font-sans">({s.local_name})</span>
                      </div>
                      <div className="text-[10px] text-slate-500">Elev: {s.elevation_m}m AMSL</div>
                    </td>
                    <td className="p-3.5 text-slate-300">
                      <div>{s.municipality}</div>
                      <div className="text-[10px] text-slate-500">{s.district} District</div>
                    </td>
                    <td className="p-3.5 text-right font-bold text-white">
                      {s.population ? s.population.toLocaleString() : 'N/A (OSM)'}
                    </td>
                    <td className="p-3.5 text-right font-bold">
                      {s.estimated_exposed_population != null ? (
                        <div>
                          <span className="text-rose-400">~{Math.round(s.estimated_exposed_population).toLocaleString()}</span>
                          <div className="text-[9px] text-slate-500 font-normal">{(s.exposure_percentage ?? 0).toFixed(1)}%</div>
                        </div>
                      ) : (
                        <span className="text-slate-400">~{Math.round((s.population || 0) * ((s.exposure_percentage || 0) / 100)).toLocaleString()}</span>
                      )}
                    </td>
                    <td className="p-3.5 text-right font-bold">
                      <span className={s.distance_to_flood_m < 250 ? 'text-rose-400' : 'text-slate-300'}>
                        {s.distance_to_flood_m} m
                      </span>
                    </td>
                    <td className="p-3.5 text-[11px] text-slate-300">
                      {s.critical_infrastructure_at_risk.length > 0 ? (
                        <div className="text-amber-300/90 font-sans">
                          {s.critical_infrastructure_at_risk.join(', ')}
                        </div>
                      ) : (
                        <span className="text-slate-500">None detected</span>
                      )}
                    </td>
                    <td className="p-3.5 text-[11px] text-slate-400 max-w-xs font-sans">
                      {s.recommended_action}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
