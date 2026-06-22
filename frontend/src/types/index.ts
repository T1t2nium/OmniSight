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
}

export interface AgentListPayload {
  agents: AgentInfo[];
}

export interface AgentSelectPayload {
  agent_id: string;
}

// ---- UI State Types ----

export type ConnectionState = 'disconnected' | 'connecting' | 'connected';

export interface MediaStreamState {
  stream: MediaStream | null;
  cameraEnabled: boolean;
  micEnabled: boolean;
  error: string | null;
}
