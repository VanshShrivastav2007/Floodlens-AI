import React from 'react';
import { Calendar, Clock, Play, CheckCircle2, AlertCircle, RefreshCw } from 'lucide-react';
import { FloodAnalysisResult, StudyArea, AnalysisRunRequest } from '../../types';

interface TimelineBarProps {
  analysisResult: FloodAnalysisResult | null;
  activeStudyArea?: StudyArea;
  activeParams?: AnalysisRunRequest | null;
  onRunAnalysis: () => void;
  isLoading: boolean;
  loadingStage?: string;
  loadingProgress?: number;
}

export const TimelineBar: React.FC<TimelineBarProps> = ({
  analysisResult,
  activeStudyArea,
  activeParams,
  onRunAnalysis,
  isLoading,
  loadingStage,
  loadingProgress = 0
}) => {
  const preDate = analysisResult?.search_window?.actual_pre_date || 
    analysisResult?.pre_scene?.acquisition_date || 
    activeParams?.pre_flood_date_start || 
    '2024-09-15';

  const postDate = analysisResult?.search_window?.actual_post_date || 
    analysisResult?.post_scene?.acquisition_date || 
    activeParams?.post_flood_date_start || 
    '2024-09-29';

  const eventRange = analysisResult?.search_window?.event_window || 
    (activeParams ? `${activeParams.post_flood_date_start} to ${activeParams.post_flood_date_end}` : 'Active Monsoon Crest');

  const eventTitle = analysisResult?.search_window?.event_title || 
    `${activeStudyArea?.name?.split('(')[0]?.trim() || 'Basin'} Discharge & Inundation Surge`;

  const sensorDesc = (analysisResult?.sensor_mode || activeParams?.sensor_mode) === 'SENTINEL_1_SAR'
    ? 'Sentinel-1 C-SAR RTC'
    : (analysisResult?.sensor_mode || activeParams?.sensor_mode) === 'DUAL_SENSOR_SYNERGY'
      ? 'Dual S2 Optical + S1 SAR'
      : 'Sentinel-2 L2A (10m Native)';

  const stages = [
    {
      id: 'pre',
      title: 'Pre-Flood Baseline',
      date: preDate,
      status: 'Observed',
      desc: `${sensorDesc} Baseline`
    },
    {
      id: 'event',
      title: 'Monsoon Flood Crest',
      date: eventRange,
      status: 'Event Peak',
      desc: eventTitle
    },
    {
      id: 'post',
      title: 'Post-Flood Observation',
      date: postDate,
      status: 'Observed',
      desc: `${sensorDesc} Crest`
    },
    {
      id: 'detection',
      title: 'Water Index & Anomaly',
      date: 'Change Detection',
      status: analysisResult ? 'Complete' : 'Ready',
      desc: 'Baseline Separated & Filtered'
    },
    {
      id: 'impact',
      title: 'Settlement Impact Vector',
      date: 'Exposure Model',
      status: analysisResult ? 'Evaluated' : 'Pending',
      desc: 'Wards & Population Assessed'
    }
  ];

  return (
    <div className="h-20 border-t border-command-700/60 bg-command-950/95 backdrop-blur-md px-6 flex items-center justify-between z-30 font-mono">
      {/* Timeline Milestones */}
      <div className="flex-1 flex items-center justify-start space-x-6 overflow-x-auto py-2">
        {stages.map((stage, idx) => (
          <div key={stage.id} className="flex items-center space-x-3 flex-shrink-0 group">
            {/* Step Marker Node */}
            <div className="flex flex-col items-center">
              <div className={`w-6 h-6 rounded-full border flex items-center justify-center text-[10px] font-bold transition-all ${
                stage.status === 'Event Peak'
                  ? 'border-rose-500 bg-rose-950/60 text-rose-400 shadow-glow-alert'
                  : (analysisResult || idx < 3)
                    ? 'border-cyan-glow bg-cyan-950/60 text-cyan-glow shadow-glow-cyan'
                    : 'border-slate-700 bg-command-900 text-slate-500'
              }`}>
                {idx + 1}
              </div>
            </div>

            {/* Step Label */}
            <div>
              <div className="text-[11px] font-semibold text-slate-200 flex items-center space-x-1.5">
                <span>{stage.title}</span>
                <span className={`text-[9px] px-1.5 py-0.2 rounded ${
                  stage.status === 'Event Peak'
                    ? 'bg-rose-900/50 text-rose-300'
                    : 'bg-command-800 text-cyan-glow'
                }`}>
                  {stage.status}
                </span>
              </div>
              <div className="text-[10px] text-slate-400">
                {stage.date} &bull; <span className="text-slate-500">{stage.desc}</span>
              </div>
            </div>

            {/* Connecting Chevron/Line */}
            {idx < stages.length - 1 && (
              <div className="w-8 h-[1px] bg-command-700 ml-3" />
            )}
          </div>
        ))}
      </div>

      {/* Right Re-run Analysis Action */}
      <div className="pl-6 border-l border-command-700/60 flex items-center space-x-3">
        <button
          onClick={onRunAnalysis}
          disabled={isLoading}
          className="px-4 py-2 rounded bg-gradient-to-r from-cyan-500 to-blue-600 hover:from-cyan-400 hover:to-blue-500 text-black font-semibold text-xs tracking-wide transition-all shadow-glow-cyan flex items-center space-x-2 disabled:opacity-50 cursor-pointer"
        >
          {isLoading ? (
            <>
              <RefreshCw className="w-3.5 h-3.5 animate-spin" />
              <span>{loadingProgress ? `${loadingProgress}% PROCESSING` : 'PROCESSING...'}</span>
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5 fill-black" />
              <span>RE-RUN PIPELINE</span>
            </>
          )}
        </button>
      </div>
    </div>
  );
};
