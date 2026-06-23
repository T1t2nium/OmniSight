"""Unit tests for InterviewScorer — post-interview AI scoring.

Tests the report generation, JSON parsing, validation, and fallback
logic with a MockAIClient.
"""

from __future__ import annotations

import json

import pytest

from app.services.base_ai_client import BaseAIClient
from app.services.interview_scorer import (
    InterviewScorer,
    _build_scoring_prompt,
    _parse_report_response,
    _build_fallback_report,
)
from app.models.interview import (
    JDEntities,
    ResumeEntities,
    MatchResult,
    InterviewReport,
)


# ---- Test Data ----


def _make_jd() -> JDEntities:
    return JDEntities(
        position_title="Python后端工程师",
        required_skills=["Python", "FastAPI", "PostgreSQL"],
        required_experience_years=3.0,
    )


def _make_resume() -> ResumeEntities:
    return ResumeEntities(
        name="李四",
        skills=["Python", "Django", "MySQL"],
        total_years=4.0,
    )


def _make_match() -> MatchResult:
    return MatchResult(
        match_percentage=60.0,
        matched_skills=["Python"],
        missing_skills=["FastAPI", "PostgreSQL"],
    )


def _make_transcript() -> list[dict]:
    return [
        {"role": "assistant", "content": "请介绍一下你的Python项目经验。"},
        {"role": "user", "content": "我有4年Python开发经验，做过电商后台和数据分析平台。"},
        {"role": "assistant", "content": "你在项目中用过FastAPI吗？"},
        {"role": "user", "content": "了解过但实际项目主要用Django。"},
        {"role": "assistant", "content": "如果线上服务突然变慢，你会从哪些方面排查？"},
        {"role": "user", "content": "我会先看数据库慢查询，然后检查API响应时间，看日志定位瓶颈。"},
    ]


# ---- Mock AI Client ----


class MockAIClient(BaseAIClient):
    """Returns a controlled JSON scoring response."""

    def __init__(self, response_text: str = "", model: str = "mock"):
        self._response = response_text
        self._model = model

    @property
    def model(self) -> str:
        return self._model

    @property
    def provider_name(self) -> str:
        return "mock"

    async def chat(self, transcript, image_base64=None, history=None,
                   system_prompt=None):
        yield {"delta": self._response, "done": True, "total_duration": 0.1}

    async def check_health(self) -> bool:
        return True

    async def close(self) -> None:
        pass


def _valid_report_json() -> str:
    return json.dumps({
        "scores": {
            "technical": 80,
            "experience": 75,
            "communication": 85,
            "role_fit": 70,
            "stress": 65,
        },
        "overall_score": 75,
        "strengths": ["Python经验丰富", "沟通表达清晰"],
        "weaknesses": ["缺少FastAPI经验", "压力测试表现一般"],
        "summary": "候选人技术基础扎实，沟通能力好，但部分核心技能有缺口。",
        "recommendation": "推荐",
    })


# ---- Tests ----


class TestGenerateReport:
    """Tests for the main generate_report() method."""

    async def test_generates_valid_report(self):
        """A valid JSON response produces a complete InterviewReport."""
        client = MockAIClient(_valid_report_json())
        report = await InterviewScorer.generate_report(
            client, _make_transcript(), _make_jd(), _make_resume(), _make_match(),
        )
        assert isinstance(report, InterviewReport)
        assert report.scores.technical == 80
        assert report.scores.communication == 85
        assert report.overall_score == 75
        assert "Python经验丰富" in report.strengths
        assert len(report.strengths) >= 2
        assert len(report.weaknesses) >= 2
        assert report.recommendation == "推荐"
        assert len(report.generated_at) > 0
        assert len(report.summary) > 0

    async def test_clamps_scores_to_0_100(self):
        """Scores outside [0, 100] are clamped."""
        # AI returns out-of-range scores
        raw = json.dumps({
            "scores": {
                "technical": 150,
                "experience": -10,
                "communication": 85,
                "role_fit": 70,
                "stress": 65,
            },
            "overall_score": 75,
            "strengths": ["A", "B"],
            "weaknesses": ["C", "D"],
            "summary": "...",
            "recommendation": "推荐",
        })
        client = MockAIClient(raw)
        report = await InterviewScorer.generate_report(
            client, _make_transcript(), _make_jd(), _make_resume(), _make_match(),
        )
        assert report.scores.technical == 100   # clamped from 150
        assert report.scores.experience == 0     # clamped from -10
        assert report.overall_score == 75

    async def test_fenced_json_parsed(self):
        """JSON inside ```json ... ``` fence is parsed."""
        raw = "```json\n" + _valid_report_json() + "\n```"
        client = MockAIClient(raw)
        report = await InterviewScorer.generate_report(
            client, _make_transcript(), _make_jd(), _make_resume(), _make_match(),
        )
        assert report.overall_score == 75

    async def test_json_with_extra_text_parsed(self):
        """JSON surrounded by extra text is still extracted."""
        raw = "这是评分结果：\n" + _valid_report_json() + "\n评分完毕。"
        client = MockAIClient(raw)
        report = await InterviewScorer.generate_report(
            client, _make_transcript(), _make_jd(), _make_resume(), _make_match(),
        )
        assert report.overall_score == 75

    async def test_fallback_on_empty_response(self):
        """Empty AI response triggers fallback report."""
        client = MockAIClient("")
        report = await InterviewScorer.generate_report(
            client, _make_transcript(), _make_jd(), _make_resume(), _make_match(),
        )
        assert isinstance(report, InterviewReport)
        assert len(report.strengths) >= 1
        assert len(report.weaknesses) >= 1

    async def test_fallback_on_garbage_response(self):
        """Garbage AI response triggers fallback report."""
        client = MockAIClient("这是一段没有 JSON 的随便回复")
        report = await InterviewScorer.generate_report(
            client, _make_transcript(), _make_jd(), _make_resume(), _make_match(),
        )
        assert isinstance(report, InterviewReport)

    async def test_short_transcript_scores_lower(self):
        """Short transcript still produces valid report."""
        client = MockAIClient(_valid_report_json())
        short = [{"role": "assistant", "content": "你好"}, {"role": "user", "content": "你好"}]
        report = await InterviewScorer.generate_report(
            client, short, _make_jd(), _make_resume(), _make_match(),
        )
        assert isinstance(report, InterviewReport)


class TestPromptBuilding:
    """Tests for _build_scoring_prompt()."""

    def test_prompt_includes_transcript(self):
        prompt = _build_scoring_prompt(
            _make_transcript(), _make_jd(), _make_resume(), _make_match(),
        )
        assert "电商后台" in prompt
        assert "Django" in prompt

    def test_prompt_includes_jd_info(self):
        prompt = _build_scoring_prompt(
            _make_transcript(), _make_jd(), _make_resume(), _make_match(),
        )
        assert "Python后端工程师" in prompt
        assert "FastAPI" in prompt

    def test_prompt_includes_match_info(self):
        prompt = _build_scoring_prompt(
            _make_transcript(), _make_jd(), _make_resume(), _make_match(),
        )
        assert "60%" in prompt
        assert "技能缺口" in prompt

    def test_prompt_handles_empty_transcript(self):
        prompt = _build_scoring_prompt(
            [], JDEntities(), ResumeEntities(), MatchResult(),
        )
        assert isinstance(prompt, str)
        assert "无对话记录" in prompt


class TestParseResponse:
    """Tests for _parse_report_response()."""

    def test_parses_valid_json(self):
        raw = _valid_report_json()
        report = _parse_report_response(raw)
        assert report.overall_score == 75
        assert report.scores.technical == 80

    def test_parses_fenced_json(self):
        raw = "```json\n" + _valid_report_json() + "\n```"
        report = _parse_report_response(raw)
        assert report.overall_score == 75

    def test_fallback_on_invalid_json(self):
        report = _parse_report_response("not valid json at all")
        assert isinstance(report, InterviewReport)

    def test_fallback_has_default_strengths(self):
        report = _parse_report_response("garbage")
        assert len(report.strengths) >= 1


class TestFallbackReport:
    """Tests for _build_fallback_report()."""

    def test_fallback_uses_match_percentage(self):
        report = _build_fallback_report(_make_match())
        assert isinstance(report, InterviewReport)
        assert len(report.generated_at) > 0

    def test_fallback_recommendation_reflects_score(self):
        high = _build_fallback_report(MatchResult(match_percentage=85))
        assert high.recommendation in ("推荐", "强烈推荐")
        low = _build_fallback_report(MatchResult(match_percentage=30))
        assert low.recommendation == "不推荐"
