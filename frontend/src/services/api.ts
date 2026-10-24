import {
  StudyArea,
  SettlementImpact,
  FloodAnalysisResult,
  AnalysisRunRequest,
  SatelliteSceneMetadata,
  AnalysisJobProgress
} from '../types';

const API_BASE = '/api';

export const api = {
  async getStatus(): Promise<{
    system: string;
    version: string;
    status: string;
    earth_engine_authenticated: boolean;
    earth_engine_status: string;
    primary_optical_source: string;
    geodesic_projection: string;
    default_basin: string;
  }> {
    const res = await fetch(`${API_BASE}/status`);
    if (!res.ok) throw new Error('Failed to retrieve system status');
    return res.json();
  },

  async getStudyAreas(): Promise<StudyArea[]> {
    const res = await fetch(`${API_BASE}/study-areas`);
    if (!res.ok) throw new Error('Failed to retrieve study areas');
    return res.json();
  },

  async getSettlements(studyAreaId?: string, limit?: number, query?: string): Promise<SettlementImpact[]> {
    const params = new URLSearchParams();
    if (studyAreaId) params.append('study_area_id', studyAreaId);
    if (limit) params.append('limit', limit.toString());
    if (query) params.append('query', query);
    const queryString = params.toString();
    const url = queryString ? `${API_BASE}/settlements?${queryString}` : `${API_BASE}/settlements`;
    const res = await fetch(url);
    if (!res.ok) throw new Error('Failed to retrieve settlements');
    return res.json();
  },

  async getSatelliteScenes(params: {
    study_area_id: string;
    date_start: string;
    date_end: string;
    max_cloud_cover?: number;
    sensor_mode?: string;
  }): Promise<{ source: string; count: number; scenes: any[] }> {
    const query = new URLSearchParams({
      study_area_id: params.study_area_id,
      date_start: params.date_start,
      date_end: params.date_end,
      max_cloud_cover: (params.max_cloud_cover ?? 50.0).toString(),
      ...(params.sensor_mode ? { sensor_mode: params.sensor_mode } : {})
    });
    const res = await fetch(`${API_BASE}/satellite-scenes?${query.toString()}`);
    if (!res.ok) throw new Error('Failed to search satellite scenes');
    return res.json();
  },

  async getActiveJob(): Promise<AnalysisJobProgress | null> {
    try {
      const res = await fetch(`${API_BASE}/jobs/active`);
      if (!res.ok) return null;
      return res.json();
    } catch {
      return null;
    }
  },

  async cancelActiveJob(): Promise<void> {
    try {
      await fetch(`${API_BASE}/jobs/active/cancel`, { method: 'POST' });
    } catch {
      // ignore
    }
  },

  async getJob(runId: string): Promise<AnalysisJobProgress> {
    const res = await fetch(`${API_BASE}/jobs/${encodeURIComponent(runId)}`);
    if (!res.ok) throw new Error('Failed to fetch job progress');
    return res.json();
  },

  async runAnalysis(req: AnalysisRunRequest, signal?: AbortSignal): Promise<FloodAnalysisResult> {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 180000); // 3-minute safety timeout
    
    // Listen to parent signal if provided
    if (signal) {
      signal.addEventListener('abort', () => controller.abort());
    }

    try {
      const res = await fetch(`${API_BASE}/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(req),
        signal: controller.signal
      });
      clearTimeout(timeoutId);
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: 'Analysis failed' }));
        throw new Error(err.detail || 'Flood analysis pipeline execution failed');
      }
      return res.json();
    } catch (err: any) {
      clearTimeout(timeoutId);
      if (err.name === 'AbortError') {
        throw new Error('Analysis timed out or was cancelled by user. Please try a narrower window or dismiss.');
      }
      throw err;
    }
  },

  async getResult(runId: string): Promise<FloodAnalysisResult> {
    const res = await fetch(`${API_BASE}/results/${runId}`);
    if (!res.ok) throw new Error('Failed to retrieve analysis result');
    return res.json();
  },

  getReportUrl(runId: string): string {
    return `${API_BASE}/reports/${runId}`;
  }
};
