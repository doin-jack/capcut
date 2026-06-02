// "미리보기" 버튼 → PNG 표시 (Design 6 / FR-09)
import { useState } from 'react';
import { preview } from '../api';
import type { ClipProps, Segment } from '../types';

interface Props {
  projectId: string;
  segment: Segment | null;
  props: ClipProps;
}

export default function PreviewCanvas({ projectId, segment, props }: Props) {
  const [url, setUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function render() {
    if (!segment) return;
    setLoading(true);
    setError(null);
    try {
      // 세그먼트 중앙 시각을 미리보기 기준으로 사용
      const mid = (segment.src_start + segment.src_end) / 2;
      const next = await preview(projectId, segment.id, mid, props);
      if (url) URL.revokeObjectURL(url);
      setUrl(next);
    } catch (e) {
      setError('미리보기 실패: ' + (e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="panel">
      <h3>미리보기 <span className="hint">(근사 — 최종은 CapCut에서 확인)</span></h3>
      <button onClick={render} disabled={!segment || loading}>
        {loading ? '렌더링…' : '미리보기'}
      </button>
      {error && <p className="error">{error}</p>}
      <div className="preview-frame">
        {url ? <img src={url} alt="preview" /> : <p>세그먼트 선택 후 미리보기</p>}
      </div>
    </section>
  );
}
