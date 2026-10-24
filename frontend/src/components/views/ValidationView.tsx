import React from 'react';
import { 
  CheckCircle2, 
  ShieldCheck, 
  BarChart3, 
  HelpCircle, 
  Layers, 
  AlertTriangle,
  Info,
  ExternalLink,
  ShieldAlert
} from 'lucide-react';
import { FloodAnalysisResult } from '../../types';

interface ValidationViewProps {
  analysisResult: FloodAnalysisResult | null;
}

export const ValidationView: React.FC<ValidationViewProps> = ({
  analysisResult
}) => {
  const val = analysisResult?.validation;
  const isVerified = val && val.validation_status === 'VERIFIED_REFERENCE' && val.precision !== null && val.precision !== undefined;

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-6 font-mono text-slate-200">
      {/* Title */}
      <div className="flex items-center justify-between border-b border-command-700/60 pb-3">
        <div>
          <h2 className="text-xl font-bold text-white flex items-center space-x-2.5">
            <CheckCircle2 className="w-5 h-5 text-emerald-400" />
            <span>Accuracy Assessment &amp; Reference Validation</span>
          </h2>
          <div className="text-xs text-slate-400 mt-1">
            Independent Verification Against Documented Ground Reference Datasets
          </div>
        </div>

        <div className={`px-3 py-1 rounded text-xs font-bold border ${
          isVerified 
            ? 'bg-emerald-500/15 border-emerald-500/40 text-emerald-400' 
            : 'bg-amber-500/15 border-amber-500/40 text-amber-400'
        }`}>
          {isVerified ? 'VERIFIED REFERENCE' : 'UNAVAILABLE REFERENCE DATA'}
        </div>
      </div>

      {/* Low Coverage Warning Banner */}
      {analysisResult?.low_coverage_warning && (
        <div className="hud-panel p-4 rounded-xl border border-amber-500/60 bg-amber-950/30 text-amber-200 space-y-1.5">
          <div className="flex items-center space-x-2 text-sm font-bold text-amber-400">
            <AlertTriangle className="w-4 h-4 text-amber-400 shrink-0" />
            <span>LOW OBSERVATION COVERAGE WARNING ({analysisResult.valid_observation_percent}% OBSERVABLE)</span>
          </div>
          <p className="text-xs text-slate-300 font-sans leading-relaxed">
            {analysisResult.coverage_warning_message}
          </p>
        </div>
      )}

      {isVerified ? (
        <>
          {/* Real KPI Cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className="hud-panel p-4 rounded-xl space-y-1">
              <div className="text-[10px] uppercase text-slate-400">Intersection over Union (IoU)</div>
              <div className="text-2xl font-bold text-cyan-glow">
                {round(val.iou_jaccard! * 100, 1)}%
              </div>
              <div className="text-[10px] text-slate-500">Jaccard Index on flood pixels</div>
            </div>

            <div className="hud-panel p-4 rounded-xl space-y-1">
              <div className="text-[10px] uppercase text-slate-400">Harmonic F1-Score</div>
              <div className="text-2xl font-bold text-emerald-400">
                {round(val.f1_score! * 100, 1)}%
              </div>
              <div className="text-[10px] text-slate-500">Harmonic mean of Prec. &amp; Recall</div>
            </div>

            <div className="hud-panel p-4 rounded-xl space-y-1">
              <div className="text-[10px] uppercase text-slate-400">Detection Precision</div>
              <div className="text-2xl font-bold text-blue-400">
                {round(val.precision! * 100, 1)}%
              </div>
              <div className="text-[10px] text-slate-500">True Positives / All Detections</div>
            </div>

            <div className="hud-panel p-4 rounded-xl space-y-1">
              <div className="text-[10px] uppercase text-slate-400">Sensitivity / Recall</div>
              <div className="text-2xl font-bold text-purple-400">
                {round(val.recall! * 100, 1)}%
              </div>
              <div className="text-[10px] text-slate-500">Identified / All Ground Truth</div>
            </div>
          </div>

          {/* Real 2x2 Confusion Matrix */}
          <div className="hud-panel p-6 rounded-xl space-y-4">
            <div className="flex items-center justify-between border-b border-command-700/60 pb-2">
              <div className="text-xs font-bold uppercase tracking-wider text-cyan-glow flex items-center space-x-2">
                <BarChart3 className="w-4 h-4" />
                <span>Pixel Confusion Matrix (Projected Metric Hectares)</span>
              </div>
              <span className="text-[11px] text-slate-400">
                Reference: {val.reference_dataset} ({val.reference_date})
              </span>
            </div>

            <div className="overflow-x-auto pt-2">
              <table className="w-full text-center text-xs">
                <thead>
                  <tr className="text-slate-400">
                    <th className="p-3 text-left">Classification Matrix</th>
                    <th className="p-3 bg-command-900/60 border border-command-700/50">Reference: FLOODED</th>
                    <th className="p-3 bg-command-900/60 border border-command-700/50">Reference: DRY LAND</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td className="p-3 text-left font-bold text-slate-200 border border-command-700/50 bg-command-900/40">
                      Detected: <span className="text-[#ff3366]">FLOODED</span>
                    </td>
                    <td className="p-4 bg-emerald-950/30 border border-emerald-500/30 text-emerald-300">
                      <div className="text-base font-bold">
                        {val.true_positives_sqkm} sq km
                      </div>
                      <div className="text-[10px] text-emerald-400 uppercase font-semibold">True Positives (TP)</div>
                    </td>
                    <td className="p-4 bg-rose-950/20 border border-rose-500/30 text-rose-300">
                      <div className="text-base font-bold">
                        {val.false_positives_sqkm} sq km
                      </div>
                      <div className="text-[10px] text-rose-400 uppercase font-semibold">False Positives (FP)</div>
                    </td>
                  </tr>
                  <tr>
                    <td className="p-3 text-left font-bold text-slate-200 border border-command-700/50 bg-command-900/40">
                      Detected: <span className="text-slate-300">DRY LAND</span>
                    </td>
                    <td className="p-4 bg-amber-950/20 border border-amber-500/30 text-amber-300">
                      <div className="text-base font-bold">
                        {val.false_negatives_sqkm} sq km
                      </div>
                      <div className="text-[10px] text-amber-400 uppercase font-semibold">False Negatives (FN)</div>
                    </td>
                    <td className="p-4 bg-blue-950/20 border border-blue-500/30 text-blue-300">
                      <div className="text-base font-bold">
                        {val.true_negatives_sqkm} sq km
                      </div>
                      <div className="text-[10px] text-blue-400 uppercase font-semibold">True Negatives (TN)</div>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : (
        /* Honest Reference Data Unavailable Notice */
        <div className="hud-panel p-6 rounded-xl space-y-4 border-l-4 border-l-amber-500">
          <div className="flex items-center space-x-2.5 text-amber-400">
            <ShieldAlert className="w-5 h-5 flex-shrink-0" />
            <h3 className="text-sm font-bold uppercase tracking-wider">
              Independent Reference Data Status: Not Configured for this Observation
            </h3>
          </div>

          <p className="text-xs text-slate-300 leading-relaxed font-sans">
            Validation unavailable: No independent ground-truth reference flood extent (e.g., Copernicus Emergency Management Service activation or ICIMOD field delineation) is currently registered for this study area and observation window.
          </p>

          <div className="bg-command-900/70 p-4 rounded-lg border border-command-700/60 space-y-2 text-xs">
            <div className="font-bold text-white flex items-center space-x-2">
              <Info className="w-4 h-4 text-cyan-glow" />
              <span>Scientific Remote Sensing Integrity Notice:</span>
            </div>
            <p className="text-slate-400 font-sans text-[11px] leading-relaxed">
              In accordance with international disaster mapping protocols, precision, recall, and F1-scores are strictly computed only against verified, independent ground truth. They are omitted here rather than displaying simulated or unverified statistics.
            </p>
            <div className="text-[11px] text-cyan-glow pt-1">
              To evaluate against a real ground reference: place a verified GeoTIFF or GeoJSON in <code>data/reference/</code>.
            </div>
          </div>
        </div>
      )}

      {/* Scientific Validation Principles */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
        <div className="hud-panel p-4 rounded-xl space-y-2">
          <div className="text-cyan-glow font-bold flex items-center space-x-1.5">
            <ShieldCheck className="w-4 h-4" />
            <span>Cloud Masking Integrity</span>
          </div>
          <p className="text-slate-300 text-[11px] leading-relaxed font-sans">
            In accordance with international emergency mapping standards, cloud-covered and shadow pixels are strictly tagged as unobservable and excluded from validation. They are never falsely counted as dry land, preserving analytical truth.
          </p>
        </div>

        <div className="hud-panel p-4 rounded-xl space-y-2">
          <div className="text-cyan-glow font-bold flex items-center space-x-1.5">
            <Layers className="w-4 h-4" />
            <span>Planned Sentinel-1 Radar Extension</span>
          </div>
          <p className="text-slate-300 text-[11px] leading-relaxed font-sans">
            For persistent monsoon cloud cover periods, the pipeline architecture supports drop-in integration of Sentinel-1 C-band Synthetic Aperture Radar (SAR) backscatter thresholding (VV/VH polarizations) to penetrate cloud cover.
          </p>
        </div>
      </div>
    </div>
  );
};

function round(val: number, decimals: number): number {
  return Number(val.toFixed(decimals));
}
