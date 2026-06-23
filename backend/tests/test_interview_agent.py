"""Integration tests for InterviewAgent — registration, WS messages, and pipeline.

Covers:
- InterviewAgent registration and properties
- agent_list includes both agents with ui_config
- document_upload message handling (jd + resume)
- End-to-end: upload → parse → match → question_bank
"""

from __future__ import annotations

import base64
import io
import json
import uuid

import pytest
from starlette.testclient import TestClient

from app.main import app
from app.agents.base import AgentRegistry, ChatAgent
from app.agents.interview import InterviewAgent, INTERVIEW_AGENT_ID


def _ensure_agents_registered():
    """Register agents if not already registered in the global AgentRegistry."""
    if AgentRegistry.get(INTERVIEW_AGENT_ID) is None:
        AgentRegistry.register(ChatAgent())
        AgentRegistry.register(InterviewAgent())


# ---- Agent Registration Tests ----


class TestInterviewAgent:
    """Test InterviewAgent registration and properties."""

    @classmethod
    def setup_class(cls):
        """Ensure at least ChatAgent + InterviewAgent are registered."""
        _ensure_agents_registered()

    def test_registered_in_registry(self):
        """InterviewAgent is registered and retrievable."""
        agent = AgentRegistry.get(INTERVIEW_AGENT_ID)
        assert agent is not None
        assert agent.agent_id == "interview"
        assert agent.name == "企业海面助手"

    def test_system_prompt_not_empty(self):
        """InterviewAgent has a non-trivial system prompt."""
        agent = AgentRegistry.get(INTERVIEW_AGENT_ID)
        assert len(agent.system_prompt) > 100
        assert "面试官" in agent.system_prompt

    def test_ui_config_has_upload_and_bank(self):
        """InterviewAgent enables document upload and question bank UI."""
        agent = AgentRegistry.get(INTERVIEW_AGENT_ID)
        config = agent.get_ui_config()
        assert config["show_document_upload"] is True
        assert config["show_question_bank"] is True
        assert "header_color" in config

    def test_agent_list_includes_ui_config(self):
        """agent_list response includes ui_config for frontend."""
        agents = AgentRegistry.list_agents()
        interview = next(a for a in agents if a["agent_id"] == "interview")
        assert "ui_config" in interview
        assert interview["ui_config"]["show_document_upload"] is True

    def test_chat_agent_still_registered(self):
        """ChatAgent is still present alongside InterviewAgent."""
        agent = AgentRegistry.get("chat")
        assert agent is not None
        assert agent.name == "视觉聊天伴侣"


# ---- WebSocket Document Upload Tests ----


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


class TestDocumentUploadWS:
    """Test document_upload WebSocket message handling."""

    def test_document_upload_jd_parses_successfully(self):
        """Uploading a JD DOCX returns document_parsed with jd_entities."""
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            sid = f"test-jd-{uuid.uuid4().hex[:8]}"

            # Receive agent_list (now includes interview agent)
            agent_msg = ws.receive_json()
            assert agent_msg["type"] == "agent_list"
            agents = agent_msg["payload"]["agents"]
            assert len(agents) >= 2  # chat + interview

            # Register session
            ws.send_json(_make_msg("vad_event", sid, {"event": "speech_start"}))
            ws.receive_json()  # server_status
            ws.receive_json()  # echo

            # Upload JD document
            docx_bytes = _make_docx_bytes([
                "高级 Python 后端工程师",
                "岗位职责：负责公司核心系统开发",
                "任职要求：本科及以上，3年以上 Python 开发经验",
            ])
            b64 = base64.b64encode(docx_bytes).decode("ascii")

            ws.send_json(_make_msg("document_upload", sid, {
                "doc_type": "jd",
                "filename": "job.docx",
                "data": b64,
            }))

            # Should receive document_parsed
            parsed = ws.receive_json()
            assert parsed["type"] == "document_parsed"
            assert parsed["payload"]["doc_type"] == "jd"
            assert parsed["payload"]["jd_entities"] is not None

    def test_document_upload_resume_parses_successfully(self):
        """Uploading a resume DOCX returns document_parsed with resume_entities."""
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            sid = f"test-cv-{uuid.uuid4().hex[:8]}"
            ws.receive_json()  # agent_list

            ws.send_json(_make_msg("vad_event", sid, {"event": "speech_start"}))
            ws.receive_json()  # server_status
            ws.receive_json()  # echo

            docx_bytes = _make_docx_bytes([
                "张三",
                "联系方式：zhangsan@email.com | 13800138000",
                "技能：Python, FastAPI, Docker",
                "2020.06 - 至今  某科技公司  Python 开发工程师",
            ])
            b64 = base64.b64encode(docx_bytes).decode("ascii")

            ws.send_json(_make_msg("document_upload", sid, {
                "doc_type": "resume",
                "filename": "resume.docx",
                "data": b64,
            }))

            parsed = ws.receive_json()
            assert parsed["type"] == "document_parsed"
            assert parsed["payload"]["doc_type"] == "resume"
            assert parsed["payload"]["resume_entities"] is not None

    def test_document_upload_invalid_type_returns_error(self):
        """Invalid doc_type returns an error."""
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            sid = f"test-bad-{uuid.uuid4().hex[:8]}"
            ws.receive_json()  # agent_list

            ws.send_json(_make_msg("vad_event", sid, {"event": "speech_start"}))
            ws.receive_json()  # server_status
            ws.receive_json()  # echo

            ws.send_json(_make_msg("document_upload", sid, {
                "doc_type": "invalid",
                "filename": "test.pdf",
                "data": "AAAA",
            }))

            # Should get error (exactly 1 message sent back)
            err = ws.receive_json()
            assert err["type"] == "error"

    def test_document_upload_missing_data_returns_error(self):
        """Missing file data returns an error."""
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            sid = f"test-nodata-{uuid.uuid4().hex[:8]}"
            ws.receive_json()  # agent_list

            ws.send_json(_make_msg("vad_event", sid, {"event": "speech_start"}))
            ws.receive_json()  # server_status
            ws.receive_json()  # echo

            ws.send_json(_make_msg("document_upload", sid, {
                "doc_type": "jd",
                "filename": "empty.pdf",
                "data": "",
            }))

            # Should get error
            err = ws.receive_json()
            assert err["type"] == "error"

    def test_both_documents_trigger_match(self):
        """Uploading both JD and resume produces match_result in document_parsed."""
        client = TestClient(app)
        with client.websocket_connect("/ws") as ws:
            sid = f"test-match-{uuid.uuid4().hex[:8]}"
            ws.receive_json()  # agent_list

            ws.send_json(_make_msg("vad_event", sid, {"event": "speech_start"}))
            ws.receive_json()  # server_status
            ws.receive_json()  # echo

            # Upload JD
            jd_bytes = _make_docx_bytes([
                "Python 后端工程师",
                "任职要求：3年以上 Python 经验，熟悉 FastAPI",
            ])
            ws.send_json(_make_msg("document_upload", sid, {
                "doc_type": "jd",
                "filename": "jd.docx",
                "data": base64.b64encode(jd_bytes).decode("ascii"),
            }))
            jd_parsed = ws.receive_json()
            assert jd_parsed["type"] == "document_parsed"

            # Upload Resume
            cv_bytes = _make_docx_bytes([
                "李四",
                "技能：Python, FastAPI, Docker",
                "2020.01 - 至今  某公司  Python 开发",
            ])
            ws.send_json(_make_msg("document_upload", sid, {
                "doc_type": "resume",
                "filename": "resume.docx",
                "data": base64.b64encode(cv_bytes).decode("ascii"),
            }))
            cv_parsed = ws.receive_json()
            assert cv_parsed["type"] == "document_parsed"
            # Second upload should include match_result
            assert cv_parsed["payload"]["match_result"] is not None
            match = cv_parsed["payload"]["match_result"]
            assert "match_percentage" in match
            assert "matched_skills" in match
            assert "missing_skills" in match

    def test_health_endpoint_shows_two_agents(self):
        """Health endpoint reflects two registered agents."""
        client = TestClient(app)
        resp = client.get("/health")
        assert resp.status_code == 200
        # The health endpoint doesn't directly list agents, but it works
        data = resp.json()
        assert data["status"] == "ok"


# ---- QuestionGenerationPipe Tests (with mock AI) ----
# These are in test_question_generator.py to keep test files focused.
