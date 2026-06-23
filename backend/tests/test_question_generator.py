"""Unit tests for QuestionGenerator — AI-based question bank generation.

Uses a mock AI client that returns controlled responses to test
parsing, fallback behavior, and error handling.
"""

from __future__ import annotations

import json
import pytest

from app.models.interview import (
    JDEntities,
    ResumeEntities,
    MatchResult,
    SkillGap,
    QuestionBank,
    InterviewQuestion,
    QuestionCategory,
)
from app.services.question_generator import QuestionGenerator
from app.services.base_ai_client import BaseAIClient


# ---- Mock AI Client ----


class MockAIClient(BaseAIClient):
    """Returns a pre-configured JSON response for question generation."""

    def __init__(self, response_text: str):
        self._response = response_text

    @property
    def model(self) -> str:
        return "mock"

    @property
    def provider_name(self) -> str:
        return "mock"

    async def chat(
        self,
        transcript: str,
        image_base64: str | None = None,
        history: list[dict] | None = None,
        system_prompt: str | None = None,
    ):
        """Simulate streaming by yielding the full text then a done marker."""
        yield {"delta": self._response, "done": False}
        yield {"delta": "", "done": True, "total_duration": 0.5}

    async def check_health(self) -> bool:
        return True

    async def close(self) -> None:
        pass


# ---- Fixtures ----

VALID_AI_RESPONSE = json.dumps({
    "categories": [
        {
            "type": "icebreaker",
            "questions": [
                {"text": "请介绍一下您的工作经历。", "difficulty": "easy", "reference": ""},
                {"text": "您为什么离开上一家公司？", "difficulty": "easy", "reference": ""},
            ],
        },
        {
            "type": "technical",
            "questions": [
                {"text": "请解释 Python 装饰器的原理。", "difficulty": "medium", "reference": "Python"},
                {"text": "FastAPI 的依赖注入是如何工作的？", "difficulty": "medium", "reference": "FastAPI"},
                {"text": "Docker 镜像优化有哪些最佳实践？", "difficulty": "hard", "reference": "Docker"},
            ],
        },
        {
            "type": "behavioral",
            "questions": [
                {"text": "请分享一个您解决团队冲突的例子。", "difficulty": "medium", "reference": ""},
            ],
        },
        {
            "type": "stress",
            "questions": [
                {"text": "如果您加入后发现技术栈与预期不符，怎么办？", "difficulty": "hard", "reference": ""},
            ],
        },
    ]
})

# JSON wrapped in markdown fence (common LLM behavior)
VALID_AI_RESPONSE_FENCED = "```json\n" + VALID_AI_RESPONSE + "\n```\n"

# JSON with extra text before
VALID_AI_RESPONSE_EXTRA = "Here's the question bank:\n" + VALID_AI_RESPONSE


@pytest.fixture
def sample_jd() -> JDEntities:
    return JDEntities(
        position_title="高级 Python 后端工程师",
        required_skills=["Python", "FastAPI", "Docker"],
        preferred_skills=["Kubernetes"],
        required_experience_years=3.0,
        education_level="本科",
        responsibilities=["负责后端架构设计", "参与代码审查"],
    )


@pytest.fixture
def sample_resume() -> ResumeEntities:
    return ResumeEntities(
        name="张三",
        skills=["Python", "FastAPI", "Docker", "JavaScript"],
        total_years=4.0,
        education=[{"school": "某某大学", "degree": "本科", "major": "CS", "year": "2020"}],
    )


@pytest.fixture
def sample_match(sample_jd, sample_resume) -> MatchResult:
    return MatchResult(
        match_percentage=78.0,
        matched_skills=["python", "fastapi", "docker"],
        missing_skills=["kubernetes"],
        extra_skills=["javascript"],
        skill_gaps=[
            SkillGap(skill="Python", required=True, candidate_has=True, importance="high"),
            SkillGap(skill="Kubernetes", required=False, candidate_has=False, importance="medium"),
        ],
        experience_match=True,
        education_match=True,
        summary="候选人与岗位匹配度较高，主要技能缺口为 Kubernetes。",
    )


# ---- Tests ----


class TestQuestionGenerator:
    """Test QuestionGenerator with various AI responses."""

    @pytest.mark.asyncio
    async def test_generates_valid_bank(self, sample_jd, sample_resume, sample_match):
        """With valid AI JSON response, returns complete QuestionBank."""
        client = MockAIClient(VALID_AI_RESPONSE)
        result = await QuestionGenerator.generate(client, sample_jd, sample_resume, sample_match)

        assert isinstance(result, QuestionBank)
        assert result.total_questions == 7  # 2+3+1+1
        assert len(result.categories) == 4
        assert result.generated_at != ""

        # Check category structure
        types = [c.type for c in result.categories]
        assert "icebreaker" in types
        assert "technical" in types
        assert "behavioral" in types
        assert "stress" in types

        # Check icebreaker category
        ice = next(c for c in result.categories if c.type == "icebreaker")
        assert ice.name == "破冰问题"
        assert ice.icon == "🧊"
        assert ice.expanded is True  # first category expanded
        assert len(ice.questions) == 2

        # Check question structure
        q = ice.questions[0]
        assert isinstance(q, InterviewQuestion)
        assert q.id.startswith("icebreaker-")
        assert q.text != ""
        assert q.difficulty in ("easy", "medium", "hard")

    @pytest.mark.asyncio
    async def test_parses_fenced_json(self, sample_jd, sample_resume, sample_match):
        """JSON wrapped in ```json fence is parsed correctly."""
        client = MockAIClient(VALID_AI_RESPONSE_FENCED)
        result = await QuestionGenerator.generate(client, sample_jd, sample_resume, sample_match)
        assert result.total_questions == 7

    @pytest.mark.asyncio
    async def test_parses_json_with_extra_text(self, sample_jd, sample_resume, sample_match):
        """JSON preceded by extra text is parsed correctly."""
        client = MockAIClient(VALID_AI_RESPONSE_EXTRA)
        result = await QuestionGenerator.generate(client, sample_jd, sample_resume, sample_match)
        assert result.total_questions == 7

    @pytest.mark.asyncio
    async def test_fallback_on_empty_response(self, sample_jd, sample_resume, sample_match):
        """Empty AI response returns fallback questions."""
        client = MockAIClient("")
        result = await QuestionGenerator.generate(client, sample_jd, sample_resume, sample_match)
        assert result.total_questions > 0
        assert len(result.categories) > 0
        # Fallback should still be well-structured
        for cat in result.categories:
            assert cat.name != ""
            for q in cat.questions:
                assert q.text != ""

    @pytest.mark.asyncio
    async def test_fallback_on_garbage_response(self, sample_jd, sample_resume, sample_match):
        """Garbage AI response returns fallback questions."""
        client = MockAIClient("This is not JSON at all, just some random text.")
        result = await QuestionGenerator.generate(client, sample_jd, sample_resume, sample_match)
        assert isinstance(result, QuestionBank)
        assert result.total_questions > 0

    @pytest.mark.asyncio
    async def test_fallback_on_malformed_json(self, sample_jd, sample_resume, sample_match):
        """Malformed JSON (missing braces) returns fallback."""
        client = MockAIClient('{"categories": [{"type": "icebreaker", "questions": [')
        result = await QuestionGenerator.generate(client, sample_jd, sample_resume, sample_match)
        assert isinstance(result, QuestionBank)
        assert result.total_questions > 0

    @pytest.mark.asyncio
    async def test_build_user_prompt_includes_context(self, sample_jd, sample_resume, sample_match):
        """User prompt includes JD, resume, and match context."""
        prompt = QuestionGenerator._build_user_prompt(sample_jd, sample_resume, sample_match)
        assert "Python 后端工程师" in prompt
        assert "张三" in prompt
        assert "78%" in prompt
        assert "Kubernetes" in prompt
        assert "FastAPI" in prompt

    @pytest.mark.asyncio
    async def test_parse_json_response_handles_valid(self):
        """_parse_json_response returns QuestionBank for valid JSON."""
        result = QuestionGenerator._parse_json_response(VALID_AI_RESPONSE)
        assert result is not None
        assert result.total_questions == 7

    @pytest.mark.asyncio
    async def test_parse_json_response_rejects_garbage(self):
        """_parse_json_response returns None for non-JSON text."""
        result = QuestionGenerator._parse_json_response("Not JSON")
        assert result is None

    @pytest.mark.asyncio
    async def test_fallback_has_all_categories(self):
        """Fallback bank includes all four categories."""
        bank = QuestionGenerator._build_fallback()
        types = {c.type for c in bank.categories}
        assert "icebreaker" in types
        assert "technical" in types
        assert "behavioral" in types
        assert "stress" in types

    @pytest.mark.asyncio
    async def test_question_ids_are_unique(self, sample_jd, sample_resume, sample_match):
        """All generated question IDs are unique."""
        client = MockAIClient(VALID_AI_RESPONSE)
        result = await QuestionGenerator.generate(client, sample_jd, sample_resume, sample_match)

        ids: list[str] = []
        for cat in result.categories:
            for q in cat.questions:
                ids.append(q.id)
        assert len(ids) == len(set(ids))  # All unique
