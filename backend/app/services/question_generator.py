"""AI-powered interview question bank generator.

Takes JD requirements + candidate profile + match analysis and produces
a categorized question bank for structured interviews.

Uses the existing AI client (Ollama / Bailian) with a specialized
system prompt. Collects the full streaming response, then parses it
into structured InterviewQuestion objects.

Design: stateless static method — no initialization needed.
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone

from app.models.interview import (
    JDEntities,
    MatchResult,
    QuestionBank,
    QuestionCategory,
    InterviewQuestion,
    ResumeEntities,
    QUESTION_CATEGORIES,
)
from app.services.base_ai_client import BaseAIClient

logger = logging.getLogger(__name__)

# Fallback template questions used when AI generation fails or returns
# unparseable output. These are generic enough to be useful but
# clearly marked as fallback.
_FALLBACK_QUESTIONS: list[dict] = [
    {"text": "请简单介绍一下您的工作经历和主要技术方向。", "category": "icebreaker", "difficulty": "easy", "reference": ""},
    {"text": "您为什么对这个职位感兴趣？", "category": "icebreaker", "difficulty": "easy", "reference": ""},
    {"text": "请描述一个您解决过的复杂技术问题。", "category": "technical", "difficulty": "medium", "reference": ""},
    {"text": "您在项目中使用过哪些技术栈？请详细说明。", "category": "technical", "difficulty": "medium", "reference": ""},
    {"text": "请分享一个您在团队协作中遇到的挑战以及如何解决的。", "category": "behavioral", "difficulty": "medium", "reference": ""},
    {"text": "描述一个您在压力下完成项目的经历。", "category": "stress", "difficulty": "medium", "reference": ""},
]

# System prompt for the AI when generating questions.
# Structured to produce parseable JSON output.
_QUESTION_GEN_SYSTEM_PROMPT = """你是一位资深面试官，需要根据岗位要求和候选人背景，生成一套结构化面试题库。

你必须严格按照以下 JSON 格式输出，不要包含任何其他文字：

```json
{
  "categories": [
    {
      "type": "icebreaker",
      "questions": [
        {"text": "问题内容", "difficulty": "easy", "reference": "关联技能或留空"}
      ]
    },
    {
      "type": "technical",
      "questions": [
        {"text": "问题内容", "difficulty": "medium", "reference": "Python"}
      ]
    },
    {
      "type": "behavioral",
      "questions": [
        {"text": "问题内容", "difficulty": "medium", "reference": ""}
      ]
    },
    {
      "type": "stress",
      "questions": [
        {"text": "问题内容", "difficulty": "hard", "reference": ""}
      ]
    }
  ]
}
```

规则：
- icebreaker: 2-3 题，通用破冰，了解候选人背景和动机
- technical: 4-6 题，针对 JD 要求的技能和候选人的技能缺口出题，优先考察缺口技能
- behavioral: 3-4 题，使用 STAR 法则设计场景问题，评估软技能和项目经验
- stress: 2-3 题，适度的压力测试，考察应变能力
- difficulty 取值为 easy/medium/hard
- reference 填写该题考察的技能名称（来自 JD 要求或候选人技能），没有则留空
- 问题必须具体、有针对性，不要泛泛而谈
- 每题 1-2 句话，清晰明了

只输出 JSON，不要任何解释。"""


class QuestionGenerator:
    """Generate structured interview question banks using AI.

    Uses the existing BaseAIClient (Ollama or Bailian) with a
    specialized system prompt. Collects streaming response tokens
    and parses them into InterviewQuestion objects grouped by category.
    """

    @staticmethod
    def _build_user_prompt(
        jd: JDEntities,
        resume: ResumeEntities,
        match: MatchResult,
    ) -> str:
        """Build the user prompt containing all context for question generation."""
        parts: list[str] = []

        # JD summary
        parts.append("## 岗位描述 (JD)")
        if jd.position_title:
            parts.append(f"- 职位：{jd.position_title}")
        if jd.required_skills:
            parts.append(f"- 必备技能：{', '.join(jd.required_skills)}")
        if jd.preferred_skills:
            parts.append(f"- 加分技能：{', '.join(jd.preferred_skills)}")
        if jd.required_experience_years > 0:
            parts.append(f"- 经验要求：{jd.required_experience_years} 年")
        if jd.education_level:
            parts.append(f"- 学历要求：{jd.education_level}")
        if jd.responsibilities:
            parts.append("- 岗位职责：")
            for r in jd.responsibilities[:5]:
                parts.append(f"  - {r}")

        # Candidate summary
        parts.append("\n## 候选人背景")
        if resume.name:
            parts.append(f"- 姓名：{resume.name}")
        if resume.summary:
            parts.append(f"- 自我描述：{resume.summary[:300]}")
        if resume.skills:
            parts.append(f"- 技能：{', '.join(resume.skills[:15])}")
        if resume.total_years > 0:
            parts.append(f"- 工作年限：{resume.total_years:.1f} 年")
        if resume.education:
            schools = [e.get("school", "") for e in resume.education[:3] if e.get("school")]
            if schools:
                parts.append(f"- 教育背景：{', '.join(schools)}")

        # Work experience details — critical for targeted questions
        if resume.work_experiences:
            parts.append("\n### 工作经历详情")
            for exp in resume.work_experiences[:4]:
                exp_parts = []
                if exp.title:
                    exp_parts.append(exp.title)
                if exp.company:
                    exp_parts.append(f"@{exp.company}")
                if exp.start_date:
                    period = f"{exp.start_date} – {exp.end_date or '至今'}"
                    exp_parts.append(f"({period})")
                parts.append("- " + " ".join(exp_parts))
                if exp.description:
                    parts.append(f"  描述: {exp.description[:200]}")

        # Match analysis
        parts.append("\n## 匹配分析")
        parts.append(f"- 匹配度：{match.match_percentage:.0f}%")
        if match.matched_skills:
            parts.append(f"- 已匹配技能：{', '.join(match.matched_skills[:10])}")
        if match.missing_skills:
            parts.append(f"- 技能缺口（需要重点考察）：{', '.join(match.missing_skills[:10])}")
        if match.extra_skills:
            parts.append(f"- 候选人额外技能：{', '.join(match.extra_skills[:10])}")
        parts.append(f"- 经验匹配：{'是' if match.experience_match else '否'}")
        parts.append(f"- 学历匹配：{'是' if match.education_match else '否'}")
        if match.summary:
            parts.append(f"\n{match.summary}")

        parts.append("\n请根据以上信息生成结构化面试题库。优先考察技能缺口中的技能。")
        return "\n".join(parts)

    @staticmethod
    def _parse_json_response(raw: str) -> QuestionBank | None:
        """Extract and parse the JSON block from the AI response.

        Handles cases where the model wraps JSON in ```json fences
        or includes extra text before/after the JSON.
        """
        # Try extracting from ```json ... ``` fence
        fence_start = raw.find("```json")
        if fence_start != -1:
            fence_start = raw.find("\n", fence_start) + 1
            fence_end = raw.find("```", fence_start)
            if fence_end != -1:
                raw = raw[fence_start:fence_end]

        # Try extracting from { to } (outermost JSON object)
        brace_start = raw.find("{")
        if brace_start == -1:
            return None
        # Find matching closing brace
        depth = 0
        brace_end = -1
        for i in range(brace_start, len(raw)):
            if raw[i] == "{":
                depth += 1
            elif raw[i] == "}":
                depth -= 1
                if depth == 0:
                    brace_end = i + 1
                    break
        if brace_end == -1:
            return None

        try:
            data = json.loads(raw[brace_start:brace_end])
        except json.JSONDecodeError:
            logger.debug("Failed to parse question generator JSON response")
            return None

        # Validate and build QuestionBank
        categories: list[QuestionCategory] = []
        total = 0

        for cat_data in data.get("categories", []):
            cat_type = cat_data.get("type", "")
            cat_meta = QUESTION_CATEGORIES.get(cat_type, {})
            questions: list[InterviewQuestion] = []

            for i, q in enumerate(cat_data.get("questions", [])):
                q_id = f"{cat_type}-{i + 1}"
                questions.append(InterviewQuestion(
                    id=q_id,
                    text=q.get("text", ""),
                    category=cat_type,
                    difficulty=q.get("difficulty", "medium"),
                    reference=q.get("reference", ""),
                ))

            total += len(questions)
            categories.append(QuestionCategory(
                name=cat_meta.get("name", cat_type),
                type=cat_type,
                icon=cat_meta.get("icon", ""),
                questions=questions,
                expanded=(cat_type == "icebreaker"),  # Expand first category by default
            ))

        if not categories:
            return None

        return QuestionBank(
            categories=categories,
            total_questions=total,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    def _build_fallback() -> QuestionBank:
        """Build a fallback question bank with generic questions.

        Used when AI generation fails or returns unparseable output.
        """
        categories: list[QuestionCategory] = []
        by_type: dict[str, list[InterviewQuestion]] = {}

        for i, q in enumerate(_FALLBACK_QUESTIONS):
            cat = q["category"]
            if cat not in by_type:
                by_type[cat] = []
            q_id = f"{cat}-{len(by_type[cat]) + 1}"
            by_type[cat].append(InterviewQuestion(
                id=q_id,
                text=q["text"],
                category=cat,
                difficulty=q["difficulty"],
                reference=q["reference"],
            ))

        for cat_type, questions in by_type.items():
            meta = QUESTION_CATEGORIES.get(cat_type, {})
            categories.append(QuestionCategory(
                name=meta.get("name", cat_type),
                type=cat_type,
                icon=meta.get("icon", ""),
                questions=questions,
                expanded=(cat_type == "icebreaker"),
            ))

        total = sum(len(c.questions) for c in categories)
        return QuestionBank(
            categories=categories,
            total_questions=total,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    @staticmethod
    async def generate(
        ai_client: BaseAIClient,
        jd: JDEntities,
        resume: ResumeEntities,
        match: MatchResult,
    ) -> QuestionBank:
        """Generate a categorized question bank using the AI client.

        Args:
            ai_client: The active AI provider (Ollama or Bailian).
            jd: Extracted job description entities.
            resume: Extracted candidate resume entities.
            match: JD-resume matching result with skill gaps.

        Returns:
            QuestionBank with 4 categories (icebreaker, technical,
            behavioral, stress) and 10-16 questions total.
        """
        user_prompt = QuestionGenerator._build_user_prompt(jd, resume, match)

        try:
            # Collect full streaming response
            chunks: list[str] = []
            async for chunk in ai_client.chat(
                transcript=user_prompt,
                image_base64=None,
                history=None,
                system_prompt=_QUESTION_GEN_SYSTEM_PROMPT,
            ):
                if chunk.get("delta"):
                    chunks.append(chunk["delta"])

            raw = "".join(chunks).strip()
            if not raw:
                logger.warning("Question generator: empty AI response, using fallback")
                return QuestionGenerator._build_fallback()

            result = QuestionGenerator._parse_json_response(raw)
            if result is None:
                logger.warning("Question generator: failed to parse AI response, using fallback")
                return QuestionGenerator._build_fallback()

            logger.info(
                "Generated question bank: %d questions across %d categories",
                result.total_questions,
                len(result.categories),
            )
            return result

        except Exception as exc:
            logger.error("Question generator: AI call failed: %s", exc)
            return QuestionGenerator._build_fallback()
