// 임계값 슬라이더 + 분석 실행 + WS 진행률 (Design 6 / FR-02,03,04,05,07)
import { useState } from 'react';
import { openAnalyzeWs, startAnalyze } from '../api';
import type { AnalyzeParams, AnalyzeProgress } from '../types';

interface Props {
  projectId: string;
  onDone: () => void;
}

const STAGE_LABEL: Record<string, string> = {
  audio: '오디오 추출',
  silence: '무음 감지',
  freeze: '멈춤 감지',
  transcribe: '자막 생성(Whisper)',
  stutter: '말더듬 감지',
  plan: '컷 통합',
  done: '완료',
  error: '오류',
};

export default function AnalysisControls({ projectId, onDone }: Props) {
  const [params, setParams] = useState<AnalyzeParams>({
    min_silence_ms: 700,
    silence_thresh_db: -40,
    keep_padding_ms: 200,
    ssim_thresh: 0.985,
    min_freeze_ms: 500,
    remove_freeze: false,
    remove_retakes: true,
    model_size: 'medium',
    language: null,
  });
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<AnalyzeProgress | null>(null);

  function set<K extends keyof AnalyzeParams>(key: K, value: AnalyzeParams[K]) {
    setParams((p) => ({ ...p, [key]: value }));
  }

  async function run() {
    setRunning(true);
    setProgress(null);
    // WS 를 먼저 열고(서버가 job 시작을 대기) 분석 시작
    openAnalyzeWs(
      projectId,
      (msg) => {
        setProgress(msg);
        if (msg.stage === 'done') {
          setRunning(false);
          onDone();
        } else if (msg.stage === 'error') {
          setRunning(false);
        }
      },
      () => setRunning(false),
    );
    await startAnalyze(projectId, params);
  }

  return (
    <section className="panel">
      <h3>분석 설정</h3>
      <label>
        최소 무음 길이: {params.min_silence_ms} ms
        <input type="range" min={200} max={2000} step={50}
          value={params.min_silence_ms}
          onChange={(e) => set('min_silence_ms', +e.target.value)} />
      </label>
      <label>
        무음 임계값: {params.silence_thresh_db} dB
        <input type="range" min={-60} max={-20} step={1}
          value={params.silence_thresh_db}
          onChange={(e) => set('silence_thresh_db', +e.target.value)} />
      </label>
      <label>
        컷 사이 여유(숨 쉬는 간격): {params.keep_padding_ms} ms
        <input type="range" min={0} max={500} step={25}
          value={params.keep_padding_ms}
          onChange={(e) => set('keep_padding_ms', +e.target.value)} />
        <small> — 클수록 컷이 덜 급하고 말이 자연스러움</small>
      </label>
      <label className="checkbox">
        <input type="checkbox"
          checked={params.remove_retakes}
          onChange={(e) => set('remove_retakes', e.target.checked)} />
        반복 테이크·말더듬 제거
        <small> — 같은 말을 여러 번 다시 한 경우 마지막 완성본만 남김</small>
      </label>
      <label className="checkbox">
        <input type="checkbox"
          checked={params.remove_freeze}
          onChange={(e) => set('remove_freeze', e.target.checked)} />
        멈춤(정지 화면) 제거
        <small> — 강의·화면녹화 등 정적 영상에선 과도하게 잘릴 수 있어 기본 꺼짐</small>
      </label>
      {params.remove_freeze && (
        <>
          <label>
            멈춤 SSIM 임계값: {params.ssim_thresh}
            <input type="range" min={0.9} max={0.999} step={0.001}
              value={params.ssim_thresh}
              onChange={(e) => set('ssim_thresh', +e.target.value)} />
          </label>
          <label>
            최소 멈춤 길이: {params.min_freeze_ms} ms
            <input type="range" min={200} max={2000} step={50}
              value={params.min_freeze_ms}
              onChange={(e) => set('min_freeze_ms', +e.target.value)} />
          </label>
        </>
      )}
      <label>
        Whisper 모델
        <select value={params.model_size}
          onChange={(e) => set('model_size', e.target.value)}>
          <option value="base">base (빠름·부정확)</option>
          <option value="small">small</option>
          <option value="medium">medium (권장·정확)</option>
          <option value="large-v3">large-v3 (최정확·느림)</option>
        </select>
      </label>

      <button onClick={run} disabled={running}>
        {running ? '분석 중…' : '분석 시작'}
      </button>

      {progress && (
        <div className="progress">
          <div className="bar" style={{ width: `${progress.progress * 100}%` }} />
          <span>
            {STAGE_LABEL[progress.stage] ?? progress.stage}{' '}
            {Math.round(progress.progress * 100)}%
            {progress.detail ? ` — ${progress.detail}` : ''}
          </span>
        </div>
      )}
    </section>
  );
}
