// 백엔드 API 클라이언트 (Design 4)
import axios from 'axios';
import type {
  AnalyzeParams,
  AnalyzeProgress,
  ClipProps,
  Project,
  Segment,
} from './types';

const BASE = 'http://localhost:8000';
const WS_BASE = 'ws://localhost:8000';

const http = axios.create({ baseURL: BASE });

export async function createProject(file: File, name: string): Promise<Project> {
  const form = new FormData();
  form.append('file', file);
  form.append('name', name);
  const { data } = await http.post<Project>('/projects', form);
  return data;
}

export async function getProject(id: string): Promise<Project> {
  const { data } = await http.get<Project>(`/projects/${id}`);
  return data;
}

export async function startAnalyze(
  id: string,
  params: AnalyzeParams,
): Promise<void> {
  await http.post(`/projects/${id}/analyze`, params);
}

/** 분석 진행률 WebSocket. onMessage 로 단계/진행률 전달, 완료/에러 시 자동 종료. */
export function openAnalyzeWs(
  id: string,
  onMessage: (p: AnalyzeProgress) => void,
  onClose?: () => void,
): WebSocket {
  const ws = new WebSocket(`${WS_BASE}/projects/${id}/analyze/ws`);
  ws.onmessage = (ev) => {
    const msg: AnalyzeProgress = JSON.parse(ev.data);
    onMessage(msg);
    if (msg.stage === 'done' || msg.stage === 'error') {
      ws.close();
    }
  };
  ws.onclose = () => onClose?.();
  return ws;
}

export async function listSegments(id: string): Promise<Segment[]> {
  const { data } = await http.get<Segment[]>(`/projects/${id}/segments`);
  return data;
}

export async function patchSegment(
  id: string,
  sid: string,
  patch: { props?: ClipProps; enabled?: boolean },
): Promise<Segment> {
  const { data } = await http.patch<Segment>(
    `/projects/${id}/segments/${sid}`,
    patch,
  );
  return data;
}

/** 미리보기 PNG 를 object URL 로 반환. */
export async function preview(
  id: string,
  sid: string,
  time: number,
  props: ClipProps,
): Promise<string> {
  const { data } = await http.post(
    `/projects/${id}/preview`,
    { sid, time, props },
    { responseType: 'blob' },
  );
  return URL.createObjectURL(data);
}

export async function makeDraft(
  id: string,
  draftFolder: string,
): Promise<string> {
  const { data } = await http.post<{ draft_path: string }>(
    `/projects/${id}/draft`,
    { draft_folder: draftFolder },
  );
  return data.draft_path;
}
