"""Unit tests for DuringInterviewEngine — interview flow + event mapping.

Tests instructions building, event mapping, and lifecycle with a mocked
BailianWSClient (no live API connection required).
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.interview import (
    InterviewQuestion,
    QuestionBank,
    QuestionCategory,
    JDEntities,
    ResumeEntities,
    MatchResult,
)
from app.services.bailian_ws_client import BailianWSClient
from app.services.interview_engine import DuringInterviewEngine


# ---- Test Data Fixtures ----


def _make_question_bank() -> QuestionBank:
    """Build a realistic question bank with all 4 categories."""
    return QuestionBank(
        categories=[
            QuestionCategory(
                name="破冰问题", type="icebreaker", icon="🧊",
                questions=[
                    InterviewQuestion(id="ice-1", text="请简单介绍一下您的工作经历。",
                                      category="icebreaker", difficulty="easy"),
                    InterviewQuestion(id="ice-2", text="为什么选择应聘这个岗位？",
                                      category="icebreaker", difficulty="easy"),
                ],
            ),
            QuestionCategory(
                name="专业技能", type="technical", icon="💻",
                questions=[
                    InterviewQuestion(id="tech-1", text="请介绍您在Python方面的项目经验。",
                                      category="technical", difficulty="medium",
                                      reference="Python"),
                    InterviewQuestion(id="tech-2", text="如何处理数据库性能优化？",
                                      category="technical", difficulty="hard",
                                      reference="Database"),
                ],
            ),
            QuestionCategory(
                name="STAR 行为", type="behavioral", icon="🎯",
                questions=[
                    InterviewQuestion(id="beh-1", text="请描述一次您解决技术难题的经历。",
                                      category="behavioral", difficulty="medium"),
                ],
            ),
            QuestionCategory(
                name="压力测试", type="stress", icon="⚡",
                questions=[
                    InterviewQuestion(id="str-1", text="如果deadline临近但项目有风险，你怎么办？",
                                      category="stress", difficulty="hard"),
                ],
            ),
        ],
        total_questions=6,
        generated_at="2026-06-23T10:00:00",
    )


def _make_jd_entities() -> JDEntities:
    return JDEntities(
        position_title="高级Python后端工程师",
        required_skills=["Python", "FastAPI", "PostgreSQL", "Redis"],
        preferred_skills=["Docker", "Kubernetes"],
        required_experience_years=5.0,
        education_level="本科",
        responsibilities=["设计RESTful API", "数据库建模", "性能优化"],
        department="技术部",
    )


def _make_resume_entities() -> ResumeEntities:
    return ResumeEntities(
        name="张三",
        skills=["Python", "Django", "MySQL", "Docker"],
        total_years=6.0,
        summary="6年Python后端开发经验",
    )


def _make_match_result() -> MatchResult:
    return MatchResult(
        match_percentage=65.0,
        matched_skills=["Python", "Docker"],
        missing_skills=["FastAPI", "PostgreSQL", "Redis"],
        extra_skills=["Django"],
        skill_gaps=[],
        experience_match=True,
        education_match=True,
        summary="候选人Python经验丰富，但缺少FastAPI和Redis经验",
    )


def _make_mock_ws_client() -> BailianWSClient:
    """Create a BailianWSClient with a mock WebSocket connection.

    Patches the internal websockets connection so we can test
    without a live Bailian Realtime API.
    """
    client = BailianWSClient(api_key="sk-test-mock")
    return client


# ---- Instructions Building Tests ----


class TestBuildInstructions:
    """Tests for build_instructions() — the core prompt assembly logic."""

    def test_builds_non_empty_instructions(self):
        """Instructions are a non-empty string."""
        engine = DuringInterviewEngine(
            ws_client=_make_mock_ws_client(),
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        instructions = engine.build_instructions()
        assert isinstance(instructions, str)
        assert len(instructions) > 100

    def test_includes_persona(self):
        """Instructions contain the interviewer persona."""
        engine = DuringInterviewEngine(
            ws_client=_make_mock_ws_client(),
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        instructions = engine.build_instructions()
        assert "面试官" in instructions
        assert "STAR" in instructions

    def test_includes_position_title(self):
        """Instructions include the JD position title."""
        engine = DuringInterviewEngine(
            ws_client=_make_mock_ws_client(),
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        instructions = engine.build_instructions()
        assert "高级Python后端工程师" in instructions

    def test_includes_candidate_name(self):
        """Instructions include the candidate's name."""
        engine = DuringInterviewEngine(
            ws_client=_make_mock_ws_client(),
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        instructions = engine.build_instructions()
        assert "张三" in instructions

    def test_includes_skill_gaps(self):
        """Instructions include missing skills for follow-up targeting."""
        engine = DuringInterviewEngine(
            ws_client=_make_mock_ws_client(),
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        instructions = engine.build_instructions()
        assert "FastAPI" in instructions or "PostgreSQL" in instructions

    def test_includes_question_bank(self):
        """Instructions list questions from the bank."""
        engine = DuringInterviewEngine(
            ws_client=_make_mock_ws_client(),
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        instructions = engine.build_instructions()
        assert "请简单介绍一下您的工作经历" in instructions

    def test_includes_match_percentage(self):
        """Instructions include the match percentage."""
        engine = DuringInterviewEngine(
            ws_client=_make_mock_ws_client(),
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        instructions = engine.build_instructions()
        assert "65%" in instructions

    def test_includes_star_rules(self):
        """Instructions include STAR probing rules."""
        engine = DuringInterviewEngine(
            ws_client=_make_mock_ws_client(),
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        instructions = engine.build_instructions()
        assert "具体" in instructions  # STAR rule: ask for specifics

    def test_empty_question_bank_handled(self):
        """Instructions handle empty question bank gracefully."""
        engine = DuringInterviewEngine(
            ws_client=_make_mock_ws_client(),
            question_bank=QuestionBank(categories=[], total_questions=0),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        instructions = engine.build_instructions()
        assert isinstance(instructions, str)
        assert len(instructions) > 0

    def test_minimal_input_handled(self):
        """Instructions handle minimal input (empty entities)."""
        engine = DuringInterviewEngine(
            ws_client=_make_mock_ws_client(),
            question_bank=QuestionBank(categories=[], total_questions=0),
            jd_entities=JDEntities(),
            resume_entities=ResumeEntities(),
            match_result=MatchResult(),
        )
        instructions = engine.build_instructions()
        assert isinstance(instructions, str)
        assert len(instructions) > 50


# ---- Event Mapping Tests ----


class TestEventMapping:
    """Tests for _map_event — Bailian Realtime → frontend message format."""

    def _make_engine(self) -> DuringInterviewEngine:
        return DuringInterviewEngine(
            ws_client=_make_mock_ws_client(),
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )

    def test_maps_audio_transcript_delta(self):
        """response.audio_transcript.delta → llm_response (not done)."""
        engine = self._make_engine()
        result = engine._map_event(
            {"type": "response.audio_transcript.delta", "delta": "你好"},
            "response.audio_transcript.delta",
        )
        assert result is not None
        assert result["type"] == "llm_response"
        assert result["payload"]["delta"] == "你好"
        assert result["payload"]["done"] is False

    def test_maps_audio_transcript_done(self):
        """response.audio_transcript.done → llm_response (done=true)."""
        engine = self._make_engine()
        result = engine._map_event(
            {"type": "response.audio_transcript.done", "transcript": "你好，请坐"},
            "response.audio_transcript.done",
        )
        assert result is not None
        assert result["type"] == "llm_response"
        assert result["payload"]["done"] is True
        assert result["payload"]["full_text"] == "你好，请坐"

    def test_maps_audio_delta(self):
        """response.audio.delta → tts_audio."""
        engine = self._make_engine()
        result = engine._map_event(
            {"type": "response.audio.delta", "delta": "base64pcm=="},
            "response.audio.delta",
        )
        assert result is not None
        assert result["type"] == "tts_audio"
        assert result["payload"]["sample_rate"] == 24000
        assert "data" in result["payload"]

    def test_maps_user_transcription(self):
        """conversation.item.input_audio_transcription.completed → transcript."""
        engine = self._make_engine()
        result = engine._map_event(
            {"type": "conversation.item.input_audio_transcription.completed",
             "transcript": "我毕业于清华大学"},
            "conversation.item.input_audio_transcription.completed",
        )
        assert result is not None
        assert result["type"] == "transcript"
        assert result["payload"]["text"] == "我毕业于清华大学"

    def test_maps_speech_started(self):
        """input_audio_buffer.speech_started → ai_status (listening)."""
        engine = self._make_engine()
        result = engine._map_event(
            {"type": "input_audio_buffer.speech_started"},
            "input_audio_buffer.speech_started",
        )
        assert result is not None
        assert result["type"] == "ai_status"
        assert result["payload"]["status"] == "listening"

    def test_maps_speech_stopped(self):
        """input_audio_buffer.speech_stopped → ai_status (thinking)."""
        engine = self._make_engine()
        result = engine._map_event(
            {"type": "input_audio_buffer.speech_stopped"},
            "input_audio_buffer.speech_stopped",
        )
        assert result is not None
        assert result["type"] == "ai_status"
        assert result["payload"]["status"] == "thinking"

    def test_maps_response_done(self):
        """response.done → ai_status (idle)."""
        engine = self._make_engine()
        result = engine._map_event(
            {"type": "response.done", "usage": {"input_tokens": 100, "output_tokens": 50}},
            "response.done",
        )
        assert result is not None
        assert result["type"] == "ai_status"
        assert result["payload"]["status"] == "idle"

    def test_maps_error(self):
        """error → error message for frontend."""
        engine = self._make_engine()
        result = engine._map_event(
            {"type": "error", "error": "Rate limit exceeded"},
            "error",
        )
        assert result is not None
        assert result["type"] == "error"
        assert "Rate limit exceeded" in result["payload"]["message"]

    def test_ignores_session_events(self):
        """Session lifecycle events are ignored (no frontend need)."""
        engine = self._make_engine()
        for event_type in ["session.created", "session.updated",
                           "response.created", "response.output_item.added"]:
            result = engine._map_event({"type": event_type}, event_type)
            assert result is None, f"{event_type} should be ignored"

    def test_empty_transcript_ignored(self):
        """Empty user transcription is not forwarded."""
        engine = self._make_engine()
        result = engine._map_event(
            {"type": "conversation.item.input_audio_transcription.completed",
             "transcript": "  "},
            "conversation.item.input_audio_transcription.completed",
        )
        assert result is None


# ---- Transcript Tracking Tests ----


class TestTranscriptTracking:
    """Tests for transcript accumulation during interview."""

    def test_tracks_user_transcript(self):
        """User transcript events are added to the transcript list."""
        engine = DuringInterviewEngine(
            ws_client=_make_mock_ws_client(),
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        engine._track_transcript({
            "type": "transcript",
            "payload": {"text": "我熟悉Python和Django"},
        })
        assert len(engine.transcript) == 1
        assert engine.transcript[0]["role"] == "user"
        assert "Python" in engine.transcript[0]["content"]

    def test_tracks_assistant_complete(self):
        """Assistant done messages are added to transcript."""
        engine = DuringInterviewEngine(
            ws_client=_make_mock_ws_client(),
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        engine._track_transcript({
            "type": "llm_response",
            "payload": {"delta": "", "done": True, "full_text": "请介绍一下您的项目经验"},
        })
        assert len(engine.transcript) == 1
        assert engine.transcript[0]["role"] == "assistant"

    def test_does_not_track_incomplete_assistant(self):
        """Incomplete (delta) assistant messages are NOT added to transcript."""
        engine = DuringInterviewEngine(
            ws_client=_make_mock_ws_client(),
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        engine._track_transcript({
            "type": "llm_response",
            "payload": {"delta": "请介绍", "done": False},
        })
        assert len(engine.transcript) == 0


# ---- Properties Tests ----


class TestProperties:
    """Tests for engine properties."""

    def test_is_active_false_before_start(self):
        """is_active is False before start() is called."""
        engine = DuringInterviewEngine(
            ws_client=_make_mock_ws_client(),
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        assert engine.is_active is False

    def test_transcript_empty_initially(self):
        """transcript starts empty."""
        engine = DuringInterviewEngine(
            ws_client=_make_mock_ws_client(),
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        assert engine.transcript == []
