import React from 'react';
import { 
  Globe2, 
  Cpu, 
  Satellite, 
  Map as MapIcon, 
  Users, 
  CheckCircle2, 
  FileDown, 
  Database,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { ActiveNavTab } from '../../types';

interface SidebarRailProps {
  activeTab: ActiveNavTab;
  onSelectTab: (tab: ActiveNavTab) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export const SidebarRail: React.FC<SidebarRailProps> = ({
  activeTab,
  onSelectTab,
  isCollapsed,
  onToggleCollapse
}) => {
  const navItems = [
    { id: 'overview' as ActiveNavTab, label: 'Overview', icon: Globe2, desc: 'Problem context & basins' },
    { id: 'analysis' as ActiveNavTab, label: 'Flood Analysis', icon: Cpu, desc: 'Indices & detection engine' },
    { id: 'satellite' as ActiveNavTab, label: 'Satellite Imagery', icon: Satellite, desc: 'Sentinel-2 L2A comparison' },
    { id: 'map' as ActiveNavTab, label: 'Flood Map', icon: MapIcon, desc: 'Interactive GIS viewport' },
    { id: 'impact' as ActiveNavTab, label: 'Settlement Impact', icon: Users, desc: 'Exposure & risk register' },
    { id: 'validation' as ActiveNavTab, label: 'Validation', icon: CheckCircle2, desc: 'Scientific benchmarks & accuracy' },
    { id: 'reports' as ActiveNavTab, label: 'Reports & Exports', icon: FileDown, desc: 'GeoTIFF, GeoJSON & Briefing' },
    { id: 'settings' as ActiveNavTab, label: 'Data Sources', icon: Database, desc: 'GEE & STAC endpoints' },
  ];

  return (
    <aside 
      className={`h-[calc(100vh-4rem)] shrink-0 border-r border-command-700/60 bg-command-950/90 backdrop-blur-md flex flex-col justify-between transition-all duration-300 z-30 ${
        isCollapsed ? 'w-16' : 'w-64'
      }`}
    >
      {/* Navigation Links */}
      <div className="py-4 space-y-1 px-2 overflow-y-auto">
        <div className="px-3 pb-2 text-[10px] uppercase font-mono tracking-wider text-slate-500 flex items-center justify-between">
          {!isCollapsed && <span>Navigation Modules</span>}
        </div>

        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;

          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`w-full flex items-center rounded-lg transition-all text-left group relative ${
                isCollapsed ? 'justify-center p-3' : 'px-3 py-2.5 space-x-3'
              } ${
                isActive 
                  ? 'bg-cyan-500/15 text-cyan-glow border border-cyan-glow/40 shadow-glow-cyan' 
                  : 'text-slate-400 hover:text-slate-200 hover:bg-command-800/60'
              }`}
              title={isCollapsed ? `${item.label} — ${item.desc}` : undefined}
            >
              <Icon className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-cyan-glow' : 'text-slate-400 group-hover:text-cyan-glow transition-colors'}`} />
              
              {!isCollapsed && (
                <div className="truncate flex-1">
                  <div className="text-xs font-mono font-medium leading-tight">{item.label}</div>
                  <div className="text-[10px] text-slate-500 truncate">{item.desc}</div>
                </div>
              )}

              {isActive && (
                <div className="absolute right-0 top-1/2 -translate-y-1/2 w-1 h-5 rounded-l bg-cyan-glow" />
              )}
            </button>
          );
        })}
      </div>

      {/* Collapse Toggle Footer */}
      <div className="p-3 border-t border-command-700/60 flex items-center justify-between">
        {!isCollapsed && (
          <div className="text-[10px] font-mono text-slate-500">
            v1.0.0 &bull; TERAI OPS
          </div>
        )}
        <button
          onClick={onToggleCollapse}
          className="p-1.5 rounded hud-panel hover:text-cyan-glow transition-colors text-slate-400 ml-auto"
          title={isCollapsed ? 'Expand Navigation' : 'Collapse Navigation'}
        >
          {isCollapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>
    </aside>
  );
};
