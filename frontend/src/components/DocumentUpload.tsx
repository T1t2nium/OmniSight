import { useRef } from 'react';
import type { WSMessage, DocumentUploadPayload } from '../types';

export type UploadStatus = 'idle' | 'uploading' | 'parsing' | 'done' | 'error';

export interface UploadZoneState {
  status: UploadStatus;
  filename: string;
  error: string;
}

interface DocumentUploadProps {
  send: (msg: WSMessage) => void;
  sessionId: string;
  visible: boolean;
  jdZone: UploadZoneState;
  resumeZone: UploadZoneState;
  onUploadStart: (docType: 'jd' | 'resume', filename: string) => void;
}

/**
 * Dual-zone document upload component for the Interview Agent.
 *
 * Two independent drop zones — one for the JD (job description),
 * one for the candidate's resume. Accepts PDF and DOCX files only.
 * Uses native HTML5 Drag & Drop (no library dependency).
 *
 * State is managed by the parent (App.tsx) which handles
 * document_parsed server responses.
 */
export function DocumentUpload({
  send,
  sessionId,
  visible,
  jdZone,
  resumeZone,
  onUploadStart,
}: DocumentUploadProps) {
  const jdInputRef = useRef<HTMLInputElement>(null);
  const resumeInputRef = useRef<HTMLInputElement>(null);

  const handleFile = (docType: 'jd' | 'resume', file: File) => {
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (ext !== 'pdf' && ext !== 'docx' && ext !== 'doc') {
      // Notify parent of invalid format
      onUploadStart(docType, ''); // empty filename signals error
      return;
    }

    onUploadStart(docType, file.name);

    const reader = new FileReader();
    reader.onload = () => {
      const base64 = (reader.result as string).split(',')[1];
      const payload: DocumentUploadPayload = {
        doc_type: docType,
        filename: file.name,
        data: base64,
      };
      send({
        type: 'document_upload',
        session_id: sessionId,
        timestamp: Date.now() / 1000,
        payload: payload as unknown as Record<string, unknown>,
      });
    };
    reader.readAsDataURL(file);
  };

  const renderZone = (
    label: string,
    icon: string,
    state: UploadZoneState,
    docType: 'jd' | 'resume',
    inputRef: React.RefObject<HTMLInputElement | null>,
  ) => (
    <div className="document-upload__zone">
      <div className="document-upload__zone-header">
        <span className="document-upload__zone-icon">{icon}</span>
        <span className="document-upload__zone-label">{label}</span>
        <span className={`document-upload__zone-status document-upload__zone-status--${state.status}`}>
          {state.status === 'done' ? '✅' : state.status === 'error' ? '❌' : state.status === 'parsing' ? '🔍' : state.status === 'uploading' ? '⏳' : ''}
        </span>
      </div>

      <div
        className="document-upload__drop-area"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => { e.preventDefault(); e.stopPropagation(); }}
        onDragLeave={(e) => { e.preventDefault(); e.stopPropagation(); }}
        onDrop={(e) => {
          e.preventDefault();
          e.stopPropagation();
          const file = e.dataTransfer.files[0];
          if (file) handleFile(docType, file);
        }}
      >
        {state.status === 'idle' ? (
          <p className="document-upload__hint">拖拽 PDF/DOCX 到此处<br />或点击选择文件</p>
        ) : (
          <p className="document-upload__filename">{state.filename}</p>
        )}
      </div>

      <input
        ref={inputRef}
        type="file"
        className="document-upload__input"
        accept=".pdf,.docx,.doc"
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(docType, file);
          if (inputRef.current) inputRef.current.value = '';
        }}
      />

      {state.error && <p className="document-upload__error">{state.error}</p>}
    </div>
  );

  if (!visible) return null;

  return (
    <div className="document-upload">
      {renderZone('上传 JD (职位描述)', '📄', jdZone, 'jd', jdInputRef)}
      {renderZone('上传简历', '👤', resumeZone, 'resume', resumeInputRef)}
    </div>
  );
}
