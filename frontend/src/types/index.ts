/** Shared TypeScript type definitions — mirror of backend Pydantic models. */

// ---- Message Envelope ----

export interface WSMessage {
  type: string;
  session_id: string;
  timestamp: number;
  payload: Record<string, unknown>;
}

// ---- Client → Server Payloads ----

export interface AudioChunkPayload {
  data: string; // base64 WAV (PCM16)
  sample_rate: number;
  channels: number;
  duration_ms: number;
}

export interface VideoFramePayload {
  data: string; // base64 JPEG
  width: number;
  height: number;
}

export interface VADEventPayload {
  event: 'speech_start' | 'speech_end';
}

// ---- Server → Client Payloads ----

export interface ServerStatusPayload {
  status: 'connected' | 'disconnected';
  message: string;
}

export interface EchoPayload {
  received_type: string;
  duration_ms?: number;
  frame_count?: number;
  total_audio_ms?: number;
  total_frames?: number;
}

export interface ErrorPayload {
  message: string;
}

// ---- PR 3: AI Pipeline Payloads (Server → Client) ----

export interface TranscriptPayload {
  text: string;
  language: string;
  duration_ms: number;
}

export interface LLMResponsePayload {
  delta: string;
  done: boolean;
  total_duration: number;
}

export interface AIStatusPayload {
  status: 'listening' | 'thinking' | 'speaking' | 'idle';
}

// ---- PR 4: TTS Audio + Interrupt Payloads (Server → Client) ----

export interface TTSInfoPayload {
  provider: 'sherpa' | 'piper' | 'browser';
}

export interface TTSAudioPayload {
  data: string; // base64 PCM16 audio
  sample_rate: number;
  channels: number;
  text: string; // The sentence being spoken
}

export interface InterruptPayload {
  reason: string;
}

// ---- PR 11: Agent Payloads (Server → Client & Client → Server) ----

export interface AgentInfo {
  agent_id: string;
  name: string;
  description: string;
  ui_config: AgentUIConfig;
}

export interface AgentUIConfig {
  show_document_upload: boolean;
  show_question_bank: boolean;
  header_color: string;
}

export interface AgentListPayload {
  agents: AgentInfo[];
}

export interface AgentSelectPayload {
  agent_id: string;
}

// ---- PR 13: Document Upload & Question Bank Payloads ----

export interface DocumentUploadPayload {
  doc_type: 'jd' | 'resume';
  filename: string;
  data: string; // base64-encoded file bytes
}

export interface DocumentParsedPayload {
  doc_type: 'jd' | 'resume';
  filename: string;
  jd_entities?: Record<string, unknown>;
  resume_entities?: Record<string, unknown>;
  match_result?: MatchResultPayload;
}

export interface MatchResultPayload {
  match_percentage: number;
  matched_skills: string[];
  missing_skills: string[];
  extra_skills: string[];
  skill_gaps: SkillGapPayload[];
  experience_match: boolean;
  education_match: boolean;
  summary: string;
}

export interface SkillGapPayload {
  skill: string;
  required: boolean;
  candidate_has: boolean;
  importance: string;
}

export interface InterviewQuestion {
  id: string;
  text: string;
  category: string;
  difficulty: string;
  reference: string;
}

export interface QuestionCategory {
  name: string;
  type: string;
  icon: string;
  questions: InterviewQuestion[];
  expanded: boolean;
}

export interface QuestionBankPayload {
  categories: QuestionCategory[];
  total_questions: number;
  generated_at: string;
}

// ---- PR 14: Interview During Payloads ----

export interface InterviewStartedPayload {
  phase: string;
}

export interface InterviewStoppedPayload {
  transcript: Record<string, unknown>[];
  message: string;
}

// ---- UI State Types ----

export type ConnectionState = 'disconnected' | 'connecting' | 'connected';

export interface MediaStreamState {
  stream: MediaStream | null;
  cameraEnabled: boolean;
  micEnabled: boolean;
  error: string | null;
}
