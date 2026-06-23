"""Unit tests for interview instructions builder.

Tests the build_interview_instructions() function — the core prompt
assembly logic for interview mode.
"""

from __future__ import annotations

from app.models.interview import (
    InterviewQuestion,
    QuestionBank,
    QuestionCategory,
    JDEntities,
    ResumeEntities,
    MatchResult,
)
from app.services.interview_engine import (
    build_interview_instructions,
    _build_persona,
    _build_candidate_context,
    _build_question_bank_prompt,
    _build_star_rules,
    _build_constraints,
)


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


# ---- Main Function Tests ----


class TestBuildInstructions:
    """Tests for build_interview_instructions() — the core prompt assembly."""

    def test_builds_non_empty_instructions(self):
        """Instructions are a non-empty string."""
        instructions = build_interview_instructions(
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        assert isinstance(instructions, str)
        assert len(instructions) > 100

    def test_includes_persona(self):
        """Instructions contain the interviewer persona."""
        instructions = build_interview_instructions(
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        assert "面试官" in instructions
        assert "STAR" in instructions

    def test_includes_position_title(self):
        """Instructions include the JD position title."""
        instructions = build_interview_instructions(
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        assert "高级Python后端工程师" in instructions

    def test_includes_candidate_name(self):
        """Instructions include the candidate's name."""
        instructions = build_interview_instructions(
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        assert "张三" in instructions

    def test_includes_skill_gaps(self):
        """Instructions include missing skills for follow-up targeting."""
        instructions = build_interview_instructions(
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        assert "FastAPI" in instructions or "PostgreSQL" in instructions

    def test_includes_question_bank(self):
        """Instructions list questions from the bank."""
        instructions = build_interview_instructions(
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        assert "请简单介绍一下您的工作经历" in instructions

    def test_includes_match_percentage(self):
        """Instructions include the match percentage."""
        instructions = build_interview_instructions(
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        assert "65%" in instructions

    def test_includes_star_rules(self):
        """Instructions include STAR probing rules."""
        instructions = build_interview_instructions(
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        assert "具体" in instructions

    def test_empty_question_bank_handled(self):
        """Instructions handle empty question bank gracefully."""
        instructions = build_interview_instructions(
            question_bank=QuestionBank(categories=[], total_questions=0),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        assert isinstance(instructions, str)
        assert len(instructions) > 0

    def test_minimal_input_handled(self):
        """Instructions handle minimal input (empty entities)."""
        instructions = build_interview_instructions(
            question_bank=QuestionBank(categories=[], total_questions=0),
            jd_entities=JDEntities(),
            resume_entities=ResumeEntities(),
            match_result=MatchResult(),
        )
        assert isinstance(instructions, str)
        assert len(instructions) > 50

    def test_instructions_not_too_long(self):
        """Instructions stay within the max character limit."""
        instructions = build_interview_instructions(
            question_bank=_make_question_bank(),
            jd_entities=_make_jd_entities(),
            resume_entities=_make_resume_entities(),
            match_result=_make_match_result(),
        )
        assert len(instructions) <= 2000


# ---- Sub-function Tests ----


class TestPersonaBuilder:
    def test_persona_contains_role(self):
        p = _build_persona()
        assert "面试官" in p
        assert "STAR" in p

    def test_persona_contains_phases(self):
        p = _build_persona()
        assert "破冰" in p
        assert "专业技能" in p
        assert "压力测试" in p


class TestCandidateContext:
    def test_includes_jd_and_resume_info(self):
        ctx = _build_candidate_context(
            _make_jd_entities(), _make_resume_entities(), _make_match_result(),
        )
        assert "高级Python后端工程师" in ctx
        assert "张三" in ctx
        assert "65%" in ctx
        assert "FastAPI" in ctx

    def test_handles_empty_entities(self):
        ctx = _build_candidate_context(
            JDEntities(), ResumeEntities(), MatchResult(),
        )
        assert isinstance(ctx, str)


class TestQuestionBankPrompt:
    def test_lists_all_phases(self):
        prompt = _build_question_bank_prompt(_make_question_bank())
        assert "破冰环节" in prompt
        assert "专业技能考察" in prompt
        assert "STAR 行为面试" in prompt
        assert "压力测试" in prompt

    def test_includes_question_text(self):
        prompt = _build_question_bank_prompt(_make_question_bank())
        assert "请简单介绍一下您的工作经历" in prompt

    def test_handles_empty_bank(self):
        prompt = _build_question_bank_prompt(
            QuestionBank(categories=[], total_questions=0),
        )
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_respects_max_questions(self):
        prompt = _build_question_bank_prompt(_make_question_bank(), max_questions=2)
        # Only 2 questions should be listed
        q_count = prompt.count("[ice-") + prompt.count("[tech-") + prompt.count("[beh-") + prompt.count("[str-")
        assert q_count <= 2


class TestStarRules:
    def test_contains_probing_guidelines(self):
        rules = _build_star_rules()
        assert "追问" in rules
        assert "具体" in rules


class TestConstraints:
    def test_contains_constraints(self):
        c = _build_constraints()
        assert "一句话" in c or "1-3句话" in c or "简洁" in c
