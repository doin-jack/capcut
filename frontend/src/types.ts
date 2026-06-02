// 백엔드 Pydantic 모델 대응 타입 (Design 2)

export interface CropBox {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface ClipProps {
  crop: CropBox | null;
  rotation: number;
  flip_h: boolean;
  flip_v: boolean;
  scale: number;
  opacity: number;
  filter_type: string | null;
  filter_intensity: number;
}

export interface Segment {
  id: string;
  src_start: number;
  src_end: number;
  enabled: boolean;
  props: ClipProps;
}

export interface Region {
  start: number;
  end: number;
  reason: string;
}

export interface DetectedRegions {
  silence: Region[];
  freeze: Region[];
  stutter: Region[];
}

export interface Project {
  id: string;
  name: string;
  source_path: string;
  duration: number;
  fps: number;
  width: number;
  height: number;
  segments: Segment[];
  detected: DetectedRegions;
  subtitle_srt_path: string | null;
  capcut_draft_path: string | null;
}

export interface AnalyzeParams {
  min_silence_ms: number;
  silence_thresh_db: number;
  ssim_thresh: number;
  min_freeze_ms: number;
  model_size: string;
  language: string | null;
}

export interface AnalyzeProgress {
  stage: string;
  progress: number;
  detail?: string;
}

export const defaultClipProps = (): ClipProps => ({
  crop: null,
  rotation: 0,
  flip_h: false,
  flip_v: false,
  scale: 1,
  opacity: 1,
  filter_type: null,
  filter_intensity: 100,
});
