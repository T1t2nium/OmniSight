"""AI-powered post-interview scorer and report generator.

Analyzes the full interview transcript together with JD requirements,
candidate profile, and skill-match data. Produces a structured report
with 5-dimension radar scores, strengths/weaknesses, and hiring
recommendation.

Same stateless pattern as QuestionGenerator — static method, uses
existing BaseAIClient, parses structured JSON from LLM output.
"""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from app.models.interview import (
    JDEntities,
    MatchResult,
    ResumeEntities,
    InterviewReport,
    InterviewScores,
)
from app.services.base_ai_client import BaseAIClient

logger = logging.getLogger(__name__)

# Scoring system prompt — instructs the AI to act as an expert evaluator
_SCORING_SYSTEM_PROMPT = """\
# 角色：资深面试评估专家

你是一位拥有 15 年经验的 HR 面试评估专家。你的任务是分析面试对话记录，对候选人进行多维度评分。

## 评分维度（每项 0-100 分）
- **technical（技术能力）**：对岗位所需技术的掌握程度、技术问题的回答深度
- **experience（项目经验）**：过往项目的复杂度、角色重要性、成果量化程度
- **communication（沟通表达）**：回答的逻辑性、条理性、是否清晰准确
- **role_fit（岗位匹配）**：候选人背景与 JD 要求的整体匹配度
- **stress（抗压/应变）**：面对追问和压力问题时的表现

## 输出格式
请严格输出 JSON，不要附带任何其他文字：
```json
{
  "scores": {
    "technical": 85,
    "experience": 80,
    "communication": 75,
    "role_fit": 78,
    "stress": 72
  },
  "overall_score": 78,
  "strengths": ["Python经验丰富", "项目案例具体"],
  "weaknesses": ["缺少FastAPI实际经验", "压力问题回答较笼统"],
  "summary": "候选人技术基础扎实，但缺少部分岗位核心技能的实际经验。",
  "recommendation": "推荐"
}
```

## 评分标准
- 90-100: 卓越，远超岗位要求
- 75-89: 良好，符合或略超要求
- 60-74: 一般，基本满足但有差距
- 40-59: 较差，多项不满足要求
- 0-39: 很差，完全不符合

## 录用建议
- **强烈推荐**：overall >= 85
- **推荐**：overall >= 70
- **保留意见**：overall >= 50
- **不推荐**：overall < 50

## 注意
- strengths 和 weaknesses 各至少提供 2 条，最多 5 条
- summary 控制在 2-3 句话
- 如果对话内容较少（不足 3 轮），请适当降低各项评分并说明原因
"""


class InterviewScorer:
    """Stateless scorer — generates interview reports from transcripts."""

    @staticmethod
    async def generate_report(
        ai_client: BaseAIClient,
        transcript: list[dict],
        jd: JDEntities,
        resume: ResumeEntities,
        match: MatchResult,
    ) -> InterviewReport:
        """Analyze interview transcript and generate structured report.

        Args:
            ai_client: AI provider (BailianHTTP or Ollama).
            transcript: List of {role, content} conversation turns.
            jd: Extracted job description entities.
            resume: Extracted resume entities.
            match: JD-resume match analysis.

        Returns:
            InterviewReport with scores, strengths, weaknesses, recommendation.
        """
        user_prompt = _build_scoring_prompt(transcript, jd, resume, match)

        try:
            # Collect full AI response (not streaming)
            full_response = ""
            async for chunk in ai_client.chat(
                transcript=user_prompt,
                image_base64=None,
                history=None,
                system_prompt=_SCORING_SYSTEM_PROMPT,
            ):
                full_response += chunk["delta"]
                if chunk.get("done"):
                    break

            report = _parse_report_response(full_response)
            return report

        except Exception as exc:
            logger.warning(
                "AI scoring failed (%s) — using fallback report", exc,
            )
            return _build_fallback_report(match)

    @staticmethod
    async def generate_report_sync(
        ai_client: BaseAIClient,
        transcript: list[dict],
        jd: JDEntities,
        resume: ResumeEntities,
        match: MatchResult,
    ) -> InterviewReport:
        """Alias for generate_report (same static method, explicit naming)."""
        return await InterviewScorer.generate_report(
            ai_client, transcript, jd, resume, match,
        )


def _build_scoring_prompt(
    transcript: list[dict],
    jd: JDEntities,
    resume: ResumeEntities,
    match: MatchResult,
) -> str:
    """Build the scoring prompt — transcript + context."""
    lines: list[str] = [
        "# 面试评估任务",
        "",
        "请根据以下面试对话记录、岗位要求和候选人背景，对候选人进行全面评估。",
        "",
    ]

    # JD summary
    lines.append("## 岗位要求")
    lines.append(f"- 岗位: {jd.position_title or '未知'}")
    if jd.required_skills:
        lines.append(f"- 核心技能: {', '.join(jd.required_skills[:10])}")
    if jd.required_experience_years > 0:
        lines.append(f"- 经验要求: {jd.required_experience_years:.0f} 年")
    lines.append("")

    # Resume summary
    lines.append("## 候选人背景")
    if resume.name:
        lines.append(f"- 姓名: {resume.name}")
    if resume.skills:
        lines.append(f"- 技能: {', '.join(resume.skills[:15])}")
    if resume.total_years > 0:
        lines.append(f"- 总经验: {resume.total_years:.0f} 年")
    lines.append("")

    # Match summary
    lines.append("## 简历匹配分析")
    lines.append(f"- 匹配度: {match.match_percentage:.0f}%")
    if match.matched_skills:
        lines.append(f"- 匹配技能: {', '.join(match.matched_skills[:8])}")
    if match.missing_skills:
        lines.append(f"- 技能缺口: {', '.join(match.missing_skills[:8])}")
    lines.append("")

    # Transcript
    lines.append("## 面试对话记录")
    if not transcript:
        lines.append("（无对话记录）")
    else:
        # Truncate to last 30 turns if very long
        recent = transcript[-30:] if len(transcript) > 30 else transcript
        for turn in recent:
            role = "面试官" if turn.get("role") == "assistant" else "候选人"
            content = turn.get("content", "")[:500]  # Truncate long responses
            lines.append(f"**{role}**: {content}")
        lines.append("")

    lines.append("请根据以上信息进行评分并输出 JSON。")
    return "\n".join(lines)


def _parse_report_response(raw: str) -> InterviewReport:
    """Parse the AI's JSON response into an InterviewReport.

    Handles ```json fences, extra text, and malformed output.
    Returns a fallback report on failure.
    """
    # Try to extract JSON from the response
    json_str = ""
    try:
        # Try direct parse first
        data = json.loads(raw.strip())
        return _validate_and_build(data)
    except json.JSONDecodeError:
        pass

    # Try extracting from ```json ... ``` fence
    m = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", raw, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(1))
            return _validate_and_build(data)
        except (json.JSONDecodeError, ValueError):
            pass

    # Try finding the first { ... } block
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        try:
            data = json.loads(m.group(0))
            return _validate_and_build(data)
        except (json.JSONDecodeError, ValueError):
            pass

    logger.warning("Could not parse AI scoring response: %s", raw[:200])
    return _build_fallback_report(MatchResult())


def _validate_and_build(data: dict) -> InterviewReport:
    """Validate parsed JSON and build InterviewReport, applying bounds."""
    scores_raw = data.get("scores", {})
    scores = InterviewScores(
        technical=min(max(float(scores_raw.get("technical", 0)), 0), 100),
        experience=min(max(float(scores_raw.get("experience", 0)), 0), 100),
        communication=min(max(float(scores_raw.get("communication", 0)), 0), 100),
        role_fit=min(max(float(scores_raw.get("role_fit", 0)), 0), 100),
        stress=min(max(float(scores_raw.get("stress", 0)), 0), 100),
    )

    overall = min(max(float(data.get("overall_score", 50)), 0), 100)

    strengths = data.get("strengths", [])
    if not isinstance(strengths, list) or len(strengths) < 2:
        strengths = ["候选人有相关工作经验", "沟通表达基本清晰"]

    weaknesses = data.get("weaknesses", [])
    if not isinstance(weaknesses, list) or len(weaknesses) < 2:
        weaknesses = ["未能充分展示技术深度", "部分回答缺乏具体细节"]

    return InterviewReport(
        scores=scores,
        overall_score=round(overall, 1),
        strengths=strengths[:5],
        weaknesses=weaknesses[:5],
        summary=str(data.get("summary", ""))[:500],
        recommendation=str(data.get("recommendation", "保留意见"))[:20],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )


def _build_fallback_report(match: MatchResult) -> InterviewReport:
    """Build a basic report from match percentage when AI scoring fails."""
    mp = match.match_percentage or 50

    # Derive scores from match percentage as a rough baseline
    base = min(mp, 100)
    scores = InterviewScores(
        technical=min(base, 100),
        experience=min(base * 0.9, 100),
        communication=60.0,
        role_fit=min(base, 100),
        stress=55.0,
    )

    # Use match percentage directly as overall score baseline
    overall = round(base, 1)

    if overall >= 80:
        recommendation = "推荐"
    elif overall >= 55:
        recommendation = "保留意见"
    else:
        recommendation = "不推荐"

    return InterviewReport(
        scores=scores,
        overall_score=overall,
        strengths=["简历与JD匹配度为 {:.0f}%".format(mp)],
        weaknesses=["AI 评分未完成，请查看对话记录手动评估"],
        summary="AI 评分暂时不可用，以下数据基于简历匹配度估算，仅供参考。",
        recommendation=recommendation,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
