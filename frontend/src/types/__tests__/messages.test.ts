/**
 * Runtime validation tests for WebSocket message contracts.
 *
 * TypeScript interfaces vanish at compile time, so these tests validate
 * that messages constructed at runtime have the expected shape.  They
 * serve as executable documentation of the WS message protocol.
 */
import { describe, it, expect } from 'vitest';

import type {
  WSMessage,
  AgentListPayload,
  InterviewReportPayload,
  InterviewScoresPayload,
  DocumentUploadPayload,
  QuestionBankPayload,
  InterviewStoppedPayload,
} from '../index';

// ---- Helpers ----

/** Build a minimal WSMessage envelope. */
function envelope(type: string, payload: Record<string, unknown> = {}): WSMessage {
  return {
    type,
    session_id: `test-${Math.random().toString(36).slice(2, 8)}`,
    timestamp: Date.now(),
    payload,
  };
}

/** Check that a value is a plain non-null object. */
function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v);
}

// ---- WSMessage Envelope ----

describe('WSMessage envelope', () => {
  it('has required top-level fields', () => {
    const msg = envelope('echo', { text: 'hello' });
    expect(typeof msg.type).toBe('string');
    expect(typeof msg.session_id).toBe('string');
    expect(typeof msg.timestamp).toBe('number');
    expect(isRecord(msg.payload)).toBe(true);
  });

  it('session_id is non-empty', () => {
    const msg = envelope('echo');
    expect(msg.session_id.length).toBeGreaterThan(0);
  });

  it('payload can be empty object', () => {
    const msg = envelope('server_status');
    expect(isRecord(msg.payload)).toBe(true);
    expect(Object.keys(msg.payload).length).toBe(0);
  });
});

// ---- AgentListPayload ----

describe('AgentListPayload', () => {
  it('agents array contains agent_id, name, and ui_config', () => {
    const payload: AgentListPayload = {
      agents: [
        {
          agent_id: 'chat',
          name: '视觉聊天伴侣',
          description: 'AI 视觉对话助手',
          ui_config: {
            show_document_upload: false,
            show_question_bank: false,
            header_color: '#58a6ff',
          },
        },
        {
          agent_id: 'interview',
          name: '企业海面助手',
          description: 'AI 面试官',
          ui_config: {
            show_document_upload: true,
            show_question_bank: true,
            header_color: '#10b981',
          },
        },
      ],
    };

    expect(payload.agents.length).toBe(2);
    for (const a of payload.agents) {
      expect(typeof a.agent_id).toBe('string');
      expect(typeof a.name).toBe('string');
      expect(typeof a.description).toBe('string');
      expect(isRecord(a.ui_config)).toBe(true);
      expect(typeof a.ui_config.show_document_upload).toBe('boolean');
      expect(typeof a.ui_config.show_question_bank).toBe('boolean');
      expect(typeof a.ui_config.header_color).toBe('string');
    }
  });

  it('empty agents array is valid', () => {
    const payload: AgentListPayload = { agents: [] };
    expect(payload.agents).toHaveLength(0);
  });
});

// ---- InterviewScoresPayload ----

describe('InterviewScoresPayload', () => {
  it('has all five dimensions with numeric values', () => {
    const scores: InterviewScoresPayload = {
      technical: 85,
      experience: 78,
      communication: 90,
      role_fit: 72,
      stress: 65,
    };

    const dims = ['technical', 'experience', 'communication', 'role_fit', 'stress'] as const;
    for (const d of dims) {
      expect(typeof scores[d]).toBe('number');
      expect(scores[d]).toBeGreaterThanOrEqual(0);
      expect(scores[d]).toBeLessThanOrEqual(100);
    }
  });

  it('allows zero scores', () => {
    const scores: InterviewScoresPayload = {
      technical: 0,
      experience: 0,
      communication: 0,
      role_fit: 0,
      stress: 0,
    };
    expect(scores.technical).toBe(0);
    expect(scores.stress).toBe(0);
  });
});

// ---- InterviewReportPayload ----

describe('InterviewReportPayload', () => {
  it('contains scores, lists, summary, and recommendation', () => {
    const report: InterviewReportPayload = {
      scores: { technical: 80, experience: 75, communication: 85, role_fit: 70, stress: 65 },
      overall_score: 75,
      strengths: ['Python经验丰富', '沟通表达清晰'],
      weaknesses: ['缺少FastAPI经验'],
      summary: '技术基础扎实，但部分核心技能有缺口。',
      recommendation: '推荐',
      generated_at: new Date().toISOString(),
    };

    expect(report.scores.technical).toBe(80);
    expect(report.overall_score).toBe(75);
    expect(report.strengths.length).toBeGreaterThanOrEqual(1);
    expect(report.weaknesses.length).toBeGreaterThanOrEqual(1);
    expect(typeof report.summary).toBe('string');
    expect(report.recommendation).toBeTruthy();
    expect(typeof report.generated_at).toBe('string');
  });

  it('recommendation is one of the known levels', () => {
    const valid = ['强烈推荐', '推荐', '保留意见', '不推荐'];
    for (const rec of valid) {
      const report: InterviewReportPayload = {
        scores: { technical: 80, experience: 80, communication: 80, role_fit: 80, stress: 80 },
        overall_score: 80,
        strengths: ['经验丰富'],
        weaknesses: ['待提升'],
        summary: 'summary',
        recommendation: rec,
        generated_at: '',
      };
      expect(valid).toContain(report.recommendation);
    }
  });
});

// ---- DocumentUploadPayload ----

describe('DocumentUploadPayload', () => {
  it('doc_type is jd or resume', () => {
    const jd: DocumentUploadPayload = {
      doc_type: 'jd',
      filename: 'job.pdf',
      data: 'AAAA',
    };
    expect(jd.doc_type).toBe('jd');

    const cv: DocumentUploadPayload = {
      doc_type: 'resume',
      filename: 'cv.docx',
      data: 'BBBB',
    };
    expect(cv.doc_type).toBe('resume');
  });

  it('filename is a non-empty string', () => {
    const payload: DocumentUploadPayload = {
      doc_type: 'jd',
      filename: 'senior-dev.pdf',
      data: '',
    };
    expect(payload.filename.length).toBeGreaterThan(0);
    // data can be empty (error case tested elsewhere)
  });
});

// ---- QuestionBankPayload ----

describe('QuestionBankPayload', () => {
  it('categories have name, type, icon, and questions array', () => {
    const bank: QuestionBankPayload = {
      categories: [
        {
          name: '破冰问题',
          type: 'icebreaker',
          icon: '🧊',
          questions: [
            { id: 'icebreaker-1', text: '介绍一下自己', category: 'icebreaker', difficulty: 'easy', reference: '' },
          ],
          expanded: true,
        },
        {
          name: '专业技能',
          type: 'technical',
          icon: '💻',
          questions: [
            { id: 'tech-1', text: 'Python相关问题', category: 'technical', difficulty: 'medium', reference: 'Python' },
          ],
          expanded: false,
        },
      ],
      total_questions: 2,
      generated_at: '',
    };

    expect(bank.categories.length).toBe(2);
    expect(bank.total_questions).toBe(2);

    for (const cat of bank.categories) {
      expect(typeof cat.name).toBe('string');
      expect(typeof cat.type).toBe('string');
      expect(typeof cat.icon).toBe('string');
      expect(Array.isArray(cat.questions)).toBe(true);
      expect(typeof cat.expanded).toBe('boolean');

      for (const q of cat.questions) {
        expect(typeof q.id).toBe('string');
        expect(typeof q.text).toBe('string');
        expect(typeof q.category).toBe('string');
        expect(['easy', 'medium', 'hard']).toContain(q.difficulty);
      }
    }
  });

  it('question difficulty is one of easy/medium/hard', () => {
    const validDiffs = ['easy', 'medium', 'hard'];
    const bank: QuestionBankPayload = {
      categories: [{
        name: 'Test',
        type: 'test',
        icon: '',
        questions: [
          { id: 'test-1', text: 'Easy Q', category: 'test', difficulty: 'easy', reference: '' },
          { id: 'test-2', text: 'Medium Q', category: 'test', difficulty: 'medium', reference: '' },
          { id: 'test-3', text: 'Hard Q', category: 'test', difficulty: 'hard', reference: '' },
        ],
        expanded: true,
      }],
      total_questions: 3,
      generated_at: '',
    };
    for (const q of bank.categories[0].questions) {
      expect(validDiffs).toContain(q.difficulty);
    }
  });
});

// ---- InterviewStoppedPayload ----

describe('InterviewStoppedPayload', () => {
  it('transcript is an array of turn records', () => {
    const payload: InterviewStoppedPayload = {
      transcript: [
        { role: 'assistant', content: '欢迎参加面试。' },
        { role: 'user', content: '你好！' },
      ],
      message: 'Interview complete — 2 turns recorded',
    };

    expect(Array.isArray(payload.transcript)).toBe(true);
    expect(payload.transcript.length).toBe(2);
    for (const turn of payload.transcript) {
      expect(typeof turn).toBe('object');
      expect(turn).not.toBeNull();
    }
    expect(typeof payload.message).toBe('string');
  });
});
