// 클립 속성 조정 (Design 6 / FR-08)
import type { ClipProps, CropBox } from '../types';

interface Props {
  props: ClipProps;
  onChange: (props: ClipProps) => void;
  onSave: () => void;
  saving?: boolean;
}

// 밝기/채도 근사 필터 프리셋 (백엔드 filter_meta.SUGGESTED_FILTERS)
const FILTER_OPTIONS = ['', 'Enhance', 'Vivid', 'Vivid_2'];

const emptyCrop = (): CropBox => ({ x: 0, y: 0, w: 1, h: 1 });

export default function PropertyPanel({ props, onChange, onSave, saving }: Props) {
  function set<K extends keyof ClipProps>(key: K, value: ClipProps[K]) {
    onChange({ ...props, [key]: value });
  }

  function setCrop<K extends keyof CropBox>(key: K, value: number) {
    const crop = props.crop ?? emptyCrop();
    set('crop', { ...crop, [key]: value });
  }

  return (
    <section className="panel">
      <h3>속성</h3>

      <label>
        회전: {props.rotation}°
        <input type="range" min={-180} max={180} step={1}
          value={props.rotation}
          onChange={(e) => set('rotation', +e.target.value)} />
      </label>

      <label>
        줌(배율): {props.scale.toFixed(2)}×
        <input type="range" min={0.5} max={3} step={0.05}
          value={props.scale}
          onChange={(e) => set('scale', +e.target.value)} />
      </label>

      <label>
        투명도: {Math.round(props.opacity * 100)}%
        <input type="range" min={0} max={1} step={0.01}
          value={props.opacity}
          onChange={(e) => set('opacity', +e.target.value)} />
      </label>

      <div className="row">
        <label className="inline">
          <input type="checkbox" checked={props.flip_h}
            onChange={(e) => set('flip_h', e.target.checked)} />
          좌우 뒤집기
        </label>
        <label className="inline">
          <input type="checkbox" checked={props.flip_v}
            onChange={(e) => set('flip_v', e.target.checked)} />
          상하 뒤집기
        </label>
      </div>

      <fieldset>
        <legend>
          <label className="inline">
            <input type="checkbox" checked={props.crop !== null}
              onChange={(e) => set('crop', e.target.checked ? emptyCrop() : null)} />
            크롭
          </label>
        </legend>
        {props.crop && (
          <div className="crop-grid">
            {(['x', 'y', 'w', 'h'] as const).map((k) => (
              <label key={k}>
                {k.toUpperCase()}: {props.crop![k].toFixed(2)}
                <input type="range" min={k === 'w' || k === 'h' ? 0.05 : 0}
                  max={1} step={0.01} value={props.crop![k]}
                  onChange={(e) => setCrop(k, +e.target.value)} />
              </label>
            ))}
          </div>
        )}
      </fieldset>

      <label>
        필터 (밝기/채도 근사)
        <select value={props.filter_type ?? ''}
          onChange={(e) => set('filter_type', e.target.value || null)}>
          {FILTER_OPTIONS.map((f) => (
            <option key={f} value={f}>{f || '없음'}</option>
          ))}
        </select>
      </label>
      {props.filter_type && (
        <label>
          필터 강도: {props.filter_intensity}
          <input type="range" min={0} max={100} step={1}
            value={props.filter_intensity}
            onChange={(e) => set('filter_intensity', +e.target.value)} />
        </label>
      )}
      <p className="hint">필터는 CapCut 프리셋 근사입니다.</p>

      <button onClick={onSave} disabled={saving}>
        {saving ? '저장 중…' : '속성 저장'}
      </button>
    </section>
  );
}
