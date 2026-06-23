"""Integration tests for the full InterviewAgent pipeline.

Covers the end-to-end flow that existing tests don't:
- start_interview validation (no question bank, already active)
- stop_interview on inactive session (no-op)
- Full pipeline: upload → match → start → stop → report
- Report message structure validation
- Fallback report on AI failure

Uses MockAIClient (from conftest.py) so tests run without external services.

Key design note:
  The interview transcript is normally built up by _save_history during
  the AI pipeline (STT → LLM → TTS).  In tests we bypass this and inject
  transcript entries directly via state_manager so the report-generation
  code path is exercised.
"""

from __future__ import annotations

import asyncio
import base64
import io
import json
import uuid
from types import SimpleNamespace

from starlette.testclient import TestClient

from tests.conftest import MockAIClient, mock_report_json

from app.main import app
from app.routes.ws import state_manager


# ---- Helpers ----

def _install_mock_ai(mock: MockAIClient) -> None:
    """Replace the orchestrator on app.state with a mock for tests.

    When using TestClient, the FastAPI lifespan is not executed, so
    app.state.orchestrator is not set.  Create a minimal namespace that
    provides just what _generate_question_bank and _generate_interview_report
    need.
    """
    app.state.orchestrator = SimpleNamespace(_ai_client=mock)


def _make_msg(msg_type: str, session_id: str, payload: dict | None = None) -> dict:
    return {
        "type": msg_type,
        "session_id": session_id,
        "timestamp": 0,
        "payload": payload or {},
    }


def _make_docx_bytes(text_lines: list[str]) -> bytes:
    """Generate a minimal .docx file with given paragraphs."""
    from docx import Document
    doc = Document()
    for line in text_lines:
        doc.add_paragraph(line)
    buf = io.BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.read()


def _valid_question_bank_json() -> str:
    """Return a valid question bank JSON the QuestionGenerator will accept."""
    return json.dumps({
        "categories": [
            {
                "type": "icebreaker",
                "questions": [
                    {"text": "请简单介绍你的工作经历。", "difficulty": "easy", "reference": ""},
                    {"text": "为什么想加入我们公司？", "difficulty": "easy", "reference": ""},
                ],
            },
            {
                "type": "technical",
                "questions": [
                    {"text": "你在项目中用过Python吗？", "difficulty": "medium", "reference": "Python"},
                    {"text": "请解释FastAPI的工作原理。", "difficulty": "medium", "reference": "FastAPI"},
                    {"text": "如何优化PostgreSQL查询？", "difficulty": "hard", "reference": "PostgreSQL"},
                ],
            },
            {
                "type": "behavioral",
                "questions": [
                    {"text": "描述一次你解决技术难题的经历。", "difficulty": "medium", "reference": ""},
                    {"text": "你如何处理与同事的技术分歧？", "difficulty": "medium", "reference": ""},
                ],
            },
            {
                "type": "stress",
                "questions": [
                    {"text": "如果项目上线前发现严重bug怎么办？", "difficulty": "hard", "reference": ""},
                    {"text": "你最大的技术短板是什么？", "difficulty": "hard", "reference": ""},
                ],
            },
        ],
    })


def _register_session(ws, session_id: str) -> None:
    """Send a dummy VAD event to register the session and drain setup msgs."""
    ws.send_json(_make_msg("vad_event", session_id, {"event": "speech_start"}))
    ws.receive_json()  # server_status
    ws.receive_json()  # echo


def _upload_jd(ws, session_id: str) -> None:
    """Upload a JD document."""
    docx = _make_docx_bytes([
        "高级Python后端工程师",
        "岗位职责：负责公司核心系统开发与架构设计",
        "任职要求：本科及以上，3年以上Python开发经验",
        "技能要求：Python, FastAPI, PostgreSQL, Docker",
    ])
    ws.send_json(_make_msg("document_upload", session_id, {
        "doc_type": "jd",
        "filename": "senior-python-dev.docx",
        "data": base64.b64encode(docx).decode("ascii"),
    }))


def _upload_resume(ws, session_id: str) -> None:
    """Upload a resume document."""
    docx = _make_docx_bytes([
        "张三",
        "联系方式：zhangsan@email.com | 13800138000",
        "技能：Python, FastAPI, Docker, MySQL",
        "2020.06 - 至今  某科技公司  Python高级开发工程师",
        "  负责电商核心系统开发，使用Python+FastAPI框架",
        "2018.07 - 2020.05  某互联网公司  Python开发工程师",
        "  参与数据分析平台建设",
    ])
    ws.send_json(_make_msg("document_upload", session_id, {
        "doc_type": "resume",
        "filename": "zhangsan-resume.docx",
        "data": base64.b64encode(docx).decode("ascii"),
    }))


def _inject_transcript(session_id: str) -> None:
    """Populate the session's interview_transcript with synthetic turns.

    This is needed because the normal transcript-building path (STT →
    AI pipeline → _save_history) cannot run without real audio/VAD in
    a test environment.  We bypass it by writing to the session directly.

    Uses asyncio.run() so it works both inside and outside a running loop.
    """
    async def _inject():
        session = await state_manager.get(session_id)
        if session:
            session.interview_transcript = [
                {"role": "assistant", "content": "欢迎参加面试，请简单介绍一下你自己。"},
                {"role": "user", "content": "我是一名Python后端工程师，有4年开发经验，擅长FastAPI和数据库优化。"},
                {"role": "assistant", "content": "请描述一个你处理过的复杂技术问题。"},
                {"role": "user", "content": "在之前项目中遇到数据库慢查询问题，我通过添加索引和优化SQL将响应时间降低了80%。"},
                {"role": "assistant", "content": "如果项目交付前发现严重Bug怎么办？"},
                {"role": "user", "content": "我会先评估影响范围，如果影响核心功能就优先修复，同时和团队沟通协调资源。"},
            ]

    try:
        asyncio.run(_inject())
    except RuntimeError:
        # Already inside a running event loop (e.g. pytest-asyncio)
        loop = asyncio.get_event_loop_policy().get_event_loop()
        loop.run_until_complete(_inject())


def _wait_for_message(ws, msg_type: str, max_attempts: int = 15) -> dict | None:
    """Wait up to max_attempts messages for one of the given type.

    The WS queue may contain intermediate messages (echo, server_status,
    etc.) that we need to drain past.  Returns the matching message or None.
    """
    for _ in range(max_attempts):
        msg = ws.receive_json()
        if msg.get("type") == msg_type:
            return msg
    return None


# ---- Tests ----


class TestStartInterviewValidation:
    """Tests for start_interview error/boundary conditions."""

    def test_start_interview_without_question_bank_returns_error(self):
        """start_interview when no documents were uploaded returns error."""
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            sid = f"test-nobank-{uuid.uuid4().hex[:8]}"
            ws.receive_json()  # agent_list
            _register_session(ws, sid)

            ws.send_json(_make_msg("start_interview", sid))

            err = ws.receive_json()
            assert err["type"] == "error"
            assert "question bank" in err["payload"]["message"].lower()

    def test_start_interview_when_already_active_returns_error(self):
        """start_interview during an active interview returns error."""
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            sid = f"test-double-{uuid.uuid4().hex[:8]}"
            ws.receive_json()  # agent_list

            mock = MockAIClient(_valid_question_bank_json())
            _install_mock_ai(mock)
            _register_session(ws, sid)

            _upload_jd(ws, sid)
            ws.receive_json()  # document_parsed (jd)
            _upload_resume(ws, sid)
            ws.receive_json()  # document_parsed (resume + match)

            qb = _wait_for_message(ws, "question_bank")
            assert qb is not None, "question_bank not received"

            # First start — OK
            ws.send_json(_make_msg("start_interview", sid))
            started = ws.receive_json()
            assert started["type"] == "interview_started"

            # Second start — error
            ws.send_json(_make_msg("start_interview", sid))
            err = ws.receive_json()
            assert err["type"] == "error"
            assert "already" in err["payload"]["message"].lower()

    def test_stop_interview_inactive_is_noop(self):
        """stop_interview without an active interview does not crash."""
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            sid = f"test-noop-{uuid.uuid4().hex[:8]}"
            ws.receive_json()  # agent_list
            _register_session(ws, sid)

            ws.send_json(_make_msg("stop_interview", sid))

            # Connection still alive — verify with a follow-up message
            ws.send_json(_make_msg("vad_event", sid, {"event": "speech_start"}))
            msg = ws.receive_json()
            assert msg is not None


class TestFullPipeline:
    """End-to-end tests: upload → match → start → inject transcript → stop → report."""

    def _setup_pipeline(self, ws, sid: str) -> MockAIClient:
        """Common setup: mock AI, register session, upload docs, get question_bank."""
        ws.receive_json()  # agent_list

        mock = MockAIClient(_valid_question_bank_json())
        _install_mock_ai(mock)
        _register_session(ws, sid)

        _upload_jd(ws, sid)
        ws.receive_json()  # document_parsed (jd)
        _upload_resume(ws, sid)
        ws.receive_json()  # document_parsed (resume + match)

        qb = _wait_for_message(ws, "question_bank")
        assert qb is not None, "question_bank not received"

        return mock

    def test_full_pipeline_upload_start_stop_report(self):
        """Full pipeline: upload → start → inject transcript → stop → report."""
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            sid = f"test-full-{uuid.uuid4().hex[:8]}"
            mock = self._setup_pipeline(ws, sid)

            # Start interview
            ws.send_json(_make_msg("start_interview", sid))
            started = ws.receive_json()
            assert started["type"] == "interview_started"

            # Inject synthetic transcript so report generation is triggered
            _inject_transcript(sid)

            # Switch mock for report generation
            mock._response = mock_report_json()

            # Stop → should fire report generation because transcript is non-empty
            ws.send_json(_make_msg("stop_interview", sid))
            stopped = ws.receive_json()
            assert stopped["type"] == "interview_stopped"
            assert "transcript" in stopped["payload"]

            # The async report generation runs in the background
            report = _wait_for_message(ws, "interview_report", max_attempts=20)
            assert report is not None, "interview_report not received"
            p = report["payload"]
            assert "scores" in p
            assert "overall_score" in p
            assert "strengths" in p
            assert "weaknesses" in p
            assert "recommendation" in p

    def test_interview_report_scores_valid(self):
        """interview_report contains valid 5-dimension scores within 0-100."""
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            sid = f"test-valid-{uuid.uuid4().hex[:8]}"
            mock = self._setup_pipeline(ws, sid)

            ws.send_json(_make_msg("start_interview", sid))
            ws.receive_json()  # interview_started

            _inject_transcript(sid)

            mock._response = mock_report_json()
            ws.send_json(_make_msg("stop_interview", sid))
            ws.receive_json()  # interview_stopped

            p = _wait_for_message(ws, "interview_report", max_attempts=20)
            assert p is not None, "interview_report not received"
            p = p["payload"]

            scores = p["scores"]
            for dim in ("technical", "experience", "communication", "role_fit", "stress"):
                assert dim in scores, f"Missing score dimension: {dim}"
                assert 0 <= scores[dim] <= 100, f"{dim}={scores[dim]} out of range"

            assert 0 <= p["overall_score"] <= 100
            assert len(p["strengths"]) >= 2
            assert len(p["weaknesses"]) >= 2
            assert p["recommendation"] in ("强烈推荐", "推荐", "保留意见", "不推荐")

    def test_interview_report_fallback_on_ai_failure(self):
        """Empty mock response triggers fallback report with valid structure."""
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            sid = f"test-fallback-{uuid.uuid4().hex[:8]}"
            mock = self._setup_pipeline(ws, sid)

            ws.send_json(_make_msg("start_interview", sid))
            ws.receive_json()  # interview_started

            _inject_transcript(sid)

            # Empty response → InterviewScorer uses fallback path
            mock._response = ""
            ws.send_json(_make_msg("stop_interview", sid))
            ws.receive_json()  # interview_stopped

            p = _wait_for_message(ws, "interview_report", max_attempts=20)
            assert p is not None, "fallback report not received"
            p = p["payload"]

            assert "scores" in p
            assert len(p["strengths"]) >= 1
            assert len(p["weaknesses"]) >= 1
            assert p["recommendation"] in ("强烈推荐", "推荐", "保留意见", "不推荐")
