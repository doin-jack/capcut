// "CapCut 드래프트 생성" (Design 6 / FR-10)
import { useState } from 'react';
import { makeDraft } from '../api';

interface Props {
  projectId: string;
}

export default function ExportButton({ projectId }: Props) {
  const [draftFolder, setDraftFolder] = useState('');
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function exportDraft() {
    if (!draftFolder.trim()) {
      setError('CapCut 草稿 폴더 경로를 입력하세요.');
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const path = await makeDraft(projectId, draftFolder.trim());
      setResult(path);
    } catch (e) {
      setError('드래프트 생성 실패: ' + (e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h3>CapCut 드래프트 생성</h3>
      <label>
        草稿(draft) 폴더 경로
        <input
          type="text"
          placeholder="예: C:\\Users\\<id>\\AppData\\Local\\CapCut\\User Data\\Projects\\com.lveditor.draft"
          value={draftFolder}
          onChange={(e) => setDraftFolder(e.target.value)}
        />
      </label>
      <button onClick={exportDraft} disabled={busy}>
        {busy ? '생성 중…' : 'CapCut 드래프트 생성'}
      </button>
      {result && (
        <p className="success">
          생성 완료: <code>{result}</code><br />
          CapCut을 열어 확인하세요.
        </p>
      )}
      {error && <p className="error">{error}</p>}
    </section>
  );
}
