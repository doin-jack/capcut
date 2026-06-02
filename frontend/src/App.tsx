import { useState } from 'react';
import './App.css';
import { getProject, listSegments } from './api';
import AnalysisControls from './components/AnalysisControls';
import ClipList from './components/ClipList';
import ExportButton from './components/ExportButton';
import PreviewCanvas from './components/PreviewCanvas';
import VideoUploader from './components/VideoUploader';
import { defaultClipProps } from './types';
import type { ClipProps, Project, Segment } from './types';

export default function App() {
  const [project, setProject] = useState<Project | null>(null);
  const [segments, setSegments] = useState<Segment[]>([]);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [draftProps, setDraftProps] = useState<ClipProps>(defaultClipProps());

  const selected = segments.find((s) => s.id === selectedId) ?? null;

  function selectSegment(sid: string) {
    setSelectedId(sid);
    const seg = segments.find((s) => s.id === sid);
    setDraftProps(seg ? { ...seg.props } : defaultClipProps());
  }

  async function refreshSegments(id: string) {
    const segs = await listSegments(id);
    setSegments(segs);
    if (segs.length > 0) selectSegment(segs[0].id);
  }

  async function onAnalyzeDone() {
    if (!project) return;
    const updated = await getProject(project.id);
    setProject(updated);
    await refreshSegments(project.id);
  }

  return (
    <div className="app">
      <header>
        <h1>CapCut 자동 편집</h1>
        {project && (
          <span className="meta">
            {project.name} · {project.width}×{project.height} ·{' '}
            {project.duration.toFixed(1)}s · {project.fps}fps
          </span>
        )}
      </header>

      {!project ? (
        <VideoUploader onCreated={setProject} />
      ) : (
        <div className="workspace">
          <div className="col">
            <AnalysisControls projectId={project.id} onDone={onAnalyzeDone} />
            <ClipList
              projectId={project.id}
              segments={segments}
              selectedId={selectedId}
              onSelect={selectSegment}
              onChange={setSegments}
            />
          </div>

          <div className="col">
            <PreviewCanvas
              projectId={project.id}
              segment={selected}
              props={draftProps}
            />
          </div>

          <div className="col">
            <ExportButton projectId={project.id} defaultName={project.name} />
          </div>
        </div>
      )}
    </div>
  );
}
