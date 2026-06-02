// keep/감지 구간 목록 + 개별 해제 (Design 6 / FR-06)
import { patchSegment } from '../api';
import type { Segment } from '../types';

interface Props {
  projectId: string;
  segments: Segment[];
  selectedId: string | null;
  onSelect: (sid: string) => void;
  onChange: (segments: Segment[]) => void;
}

function fmt(t: number): string {
  const m = Math.floor(t / 60);
  const s = (t % 60).toFixed(1);
  return `${m}:${s.padStart(4, '0')}`;
}

export default function ClipList({
  projectId,
  segments,
  selectedId,
  onSelect,
  onChange,
}: Props) {
  async function toggle(seg: Segment) {
    const updated = await patchSegment(projectId, seg.id, {
      enabled: !seg.enabled,
    });
    onChange(segments.map((s) => (s.id === seg.id ? updated : s)));
  }

  if (segments.length === 0) {
    return <section className="panel"><h3>클립</h3><p>분석을 실행하면 유지 구간이 표시됩니다.</p></section>;
  }

  return (
    <section className="panel">
      <h3>클립 ({segments.filter((s) => s.enabled).length}/{segments.length})</h3>
      <ul className="cliplist">
        {segments.map((seg, i) => (
          <li
            key={seg.id}
            className={`clip ${seg.id === selectedId ? 'selected' : ''} ${seg.enabled ? '' : 'disabled'}`}
            onClick={() => onSelect(seg.id)}
          >
            <input
              type="checkbox"
              checked={seg.enabled}
              onChange={() => toggle(seg)}
              onClick={(e) => e.stopPropagation()}
            />
            <span className="clip-idx">#{i + 1}</span>
            <span className="clip-time">
              {fmt(seg.src_start)} – {fmt(seg.src_end)}
            </span>
            <span className="clip-dur">
              {(seg.src_end - seg.src_start).toFixed(1)}s
            </span>
          </li>
        ))}
      </ul>
    </section>
  );
}
