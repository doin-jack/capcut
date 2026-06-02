// 드래그&드롭 업로드 (Design 6 / FR-01)
import { useRef, useState } from 'react';
import { createProject } from '../api';
import type { Project } from '../types';

interface Props {
  onCreated: (project: Project) => void;
}

export default function VideoUploader({ onCreated }: Props) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setError(null);
    setUploading(true);
    try {
      const name = file.name.replace(/\.[^.]+$/, '');
      const project = await createProject(file, name);
      onCreated(project);
    } catch (e) {
      setError('업로드 실패: ' + (e as Error).message);
    } finally {
      setUploading(false);
    }
  }

  return (
    <div
      className={`uploader ${dragging ? 'dragging' : ''}`}
      onDragOver={(e) => {
        e.preventDefault();
        setDragging(true);
      }}
      onDragLeave={() => setDragging(false)}
      onDrop={(e) => {
        e.preventDefault();
        setDragging(false);
        const f = e.dataTransfer.files[0];
        if (f) handleFile(f);
      }}
      onClick={() => inputRef.current?.click()}
    >
      <input
        ref={inputRef}
        type="file"
        accept="video/*"
        hidden
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) handleFile(f);
        }}
      />
      {uploading ? (
        <p>업로드 중…</p>
      ) : (
        <p>영상을 드래그하거나 클릭해서 업로드하세요</p>
      )}
      {error && <p className="error">{error}</p>}
    </div>
  );
}
