// "CapCut 드래프트 생성" (Design 6 / FR-10)
import { useEffect, useState } from 'react';
import { detectDraftFolder, makeDraft } from '../api';

interface Props {
  projectId: string;
  defaultName?: string;   // 기본 저장 이름(보통 원본 파일명)
}

export default function ExportButton({ projectId, defaultName }: Props) {
  const [draftFolder, setDraftFolder] = useState('');
  const [autoDetected, setAutoDetected] = useState(false);
  const [draftName, setDraftName] = useState(defaultName ?? '');
  const [result, setResult] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  // 마운트 시 OS 표준 위치에서 CapCut 草稿 폴더를 자동 탐지해 미리 채움(수동 수정 가능).
  useEffect(() => {
    detectDraftFolder()
      .then((info) => {
        if (info.path) {
          setDraftFolder(info.path);
          setAutoDetected(info.exists);
        }
      })
      .catch(() => {
        /* 탐지 실패 시 수동 입력으로 폴백 */
      });
  }, []);

  // 프로젝트가 바뀌면 기본 이름 갱신
  useEffect(() => {
    setDraftName(defaultName ?? '');
  }, [defaultName]);

  async function exportDraft() {
    if (!draftFolder.trim()) {
      setError('CapCut 草稿 폴더 경로를 입력하세요.');
      return;
    }
    setBusy(true);
    setError(null);
    setResult(null);
    try {
      const path = await makeDraft(projectId, draftFolder.trim(), draftName);
      setResult(path);
    } catch (e) {
      // 서버가 보낸 상세 메시지(detail)를 우선 표시, 없으면 일반 메시지
      const ax = e as { response?: { data?: { detail?: string } }; message?: string };
      setError('드래프트 생성 실패: ' + (ax.response?.data?.detail ?? ax.message ?? '알 수 없는 오류'));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="panel">
      <h3>CapCut 드래프트 생성</h3>
      <label>
        저장 이름
        <input
          type="text"
          placeholder="예: 강의1"
          value={draftName}
          onChange={(e) => setDraftName(e.target.value)}
        />
        <small> — CapCut에 이 이름으로 저장됩니다. 짧게 바꾸면 찾기 쉬워요.</small>
      </label>
      <label>
        草稿(draft) 폴더 경로
        <input
          type="text"
          placeholder="예: C:\\Users\\<id>\\AppData\\Local\\CapCut\\User Data\\Projects\\com.lveditor.draft"
          value={draftFolder}
          onChange={(e) => {
            setDraftFolder(e.target.value);
            setAutoDetected(false);
          }}
        />
      </label>
      {autoDetected && (
        <p className="success">CapCut 설치 경로를 자동으로 찾았습니다. 필요하면 수정하세요.</p>
      )}
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
