"""Interview instructions builder — assembles enhanced system prompt for interview mode.

Does NOT use Bailian Realtime WS. Instead, the instructions are injected as
system_prompt into the existing AI pipeline (faster-whisper + BailianHTTP + Piper TTS).
This preserves the user's local TTS/STT pipeline unchanged.
"""

from __future__ import annotations

import logging

from app.models.interview import (
    QuestionBank,
    JDEntities,
    ResumeEntities,
    MatchResult,
)

logger = logging.getLogger(__name__)

# Maximum characters for instructions to keep within model context limits
MAX_INSTRUCTIONS_CHARS = 2000

# Interview phases in order
PHASES = ["icebreaker", "technical", "behavioral", "stress"]

PHASE_LABELS = {
    "icebreaker": "破冰环节",
    "technical": "专业技能考察",
    "behavioral": "STAR 行为面试",
    "stress": "压力测试",
}


def build_interview_instructions(
    question_bank: QuestionBank,
    jd_entities: JDEntities,
    resume_entities: ResumeEntities,
    match_result: MatchResult,
) -> str:
    """Build the complete instructions string for interview mode.

    Combines interview persona, candidate context, question bank,
    STAR probing rules, and output constraints into a single
    system prompt for the AI pipeline.

    Args:
        question_bank: AI-generated question bank.
        jd_entities: Extracted job description entities.
        resume_entities: Extracted resume entities.
        match_result: JD-resume match analysis.

    Returns:
        Instructions string (≤ 2000 chars).
    """
    parts: list[str] = [
        _build_persona(),
        _build_candidate_context(jd_entities, resume_entities, match_result),
        _build_question_bank_prompt(question_bank),
        _build_star_rules(),
        _build_constraints(),
    ]

    instructions = "\n\n".join(parts)

    # Truncate if too long — shrink question bank listing
    if len(instructions) > MAX_INSTRUCTIONS_CHARS:
        old_len = len(instructions)
        parts[2] = _build_question_bank_prompt(question_bank, max_questions=10)
        instructions = "\n\n".join(parts)
        logger.warning(
            "Instructions truncated: %d → %d chars", old_len, len(instructions),
        )

    logger.info("Built interview instructions: %d chars", len(instructions))
    return instructions


def _build_persona() -> str:
    """Build the interviewer persona section."""
    return """# 角色：专业面试官

你是一位资深的企业面试官，具备 10 年以上技术岗位面试经验。你的任务是基于岗位描述(JD)和候选人简历，进行结构化面试。

## 核心能力
- 精准评估候选人的技术能力和文化匹配度
- 熟练运用 STAR 法则（情景-任务-行动-结果）设计行为问题
- 根据简历与 JD 的技能缺口进行针对性追问
- 保持专业、客观、公正的面试态度

## 面试流程
本次面试分为四个环节：
1. **破冰环节** — 1-2个轻松的自我介绍/职业经历问题，营造良好氛围
2. **专业技能考察** — 针对JD要求的核心技术栈和技能缺口，逐一考察
3. **STAR 行为面试** — 用 STAR 法则深入追问项目经历和解决问题的能力
4. **压力测试** — 1-2个具有挑战性的场景问题

请严格按照以上顺序进行，一个环节完成后再进入下一个。
当前应从破冰环节开始，向候选人问第一个问题。"""


def _build_candidate_context(
    jd: JDEntities, resume: ResumeEntities, match: MatchResult,
) -> str:
    """Build the candidate + position context section."""
    lines: list[str] = ["# 面试背景信息"]

    # Position
    if jd.position_title:
        lines.append(f"**招聘岗位**: {jd.position_title}")
    if jd.department:
        lines.append(f"**部门**: {jd.department}")
    if jd.required_skills:
        skills = "、".join(jd.required_skills[:10])
        lines.append(f"**岗位核心技能要求**: {skills}")
    if jd.responsibilities:
        resp = "；".join(jd.responsibilities[:5])
        lines.append(f"**岗位职责**: {resp}")

    # Candidate
    if resume.name:
        lines.append(f"**候选人**: {resume.name}")
    if resume.skills:
        c_skills = "、".join(resume.skills[:15])
        lines.append(f"**候选人技能**: {c_skills}")
    if resume.total_years > 0:
        lines.append(f"**总工作经验**: {resume.total_years:.0f} 年")

    # Skill gaps
    if match.missing_skills:
        missing = "、".join(match.missing_skills[:8])
        lines.append(f"**⚠️ 技能缺口（需重点考察）**: {missing}")
    if match.matched_skills:
        matched = "、".join(match.matched_skills[:8])
        lines.append(f"**✅ 已匹配技能**: {matched}")
    if match.match_percentage > 0:
        lines.append(f"**综合匹配度**: {match.match_percentage:.0f}%")

    return "\n".join(lines)


def _build_question_bank_prompt(
    bank: QuestionBank, max_questions: int = 15,
) -> str:
    """Build the question bank section — list questions by phase."""
    lines: list[str] = ["# 面试题库（按顺序使用）"]

    if not bank.categories:
        lines.append("（无预生成题库，请根据岗位和候选人信息自行提问）")
        return "\n".join(lines)

    question_count = 0
    for phase in PHASES:
        cat = next(
            (c for c in bank.categories if c.type == phase), None
        )
        if not cat or not cat.questions:
            continue

        label = PHASE_LABELS.get(phase, phase)
        phase_questions = cat.questions[:max_questions - question_count]
        if not phase_questions:
            break

        lines.append(f"\n## {cat.icon} {label}")
        for q in phase_questions:
            ref = f" [参考: {q.reference}]" if q.reference else ""
            lines.append(f"- [{q.id}] {q.text}{ref}")
            question_count += 1

        if question_count >= max_questions:
            remaining = sum(
                len(c.questions) for c in bank.categories
            ) - question_count
            if remaining > 0:
                lines.append(f"\n*（还有 {remaining} 道题目未列出，可视情况使用）*")
            break

    lines.append(f"\n共计 {bank.total_questions} 道题目可供参考。")
    return "\n".join(lines)


def _build_star_rules() -> str:
    """Build STAR probing rules."""
    return """# STAR 追问规则

当候选人回答问题时，如果出现以下情况，请立即追问：
1. **回答过于笼统** — 追问具体细节："能举个具体的例子吗？""当时的具体情况是什么样的？"
2. **缺少行动描述** — 追问行为："你具体做了什么？""你在其中负责哪些部分？"
3. **缺少结果** — 追问成果："最终结果如何？""有什么可量化的成果？"
4. **技能缺口相关** — 若候选人声称具备缺口技能，请深入验证："能详细说说你使用XX技术的经验吗？"

追问时注意：
- 一次只问一个追问点
- 追问控制在2-3轮以内，不要无限追问
- 若候选人明确表示不了解，礼貌转移话题"""


def _build_constraints() -> str:
    """Build output constraints."""
    return """# 输出约束
- 每次只问一个问题，等待候选人回答后再继续
- 回复控制在1-3句话，简洁直接
- 不评价候选人的个人特征（外貌、年龄、性别等）
- 不在对话中使用 Markdown 格式
- 用自然的口语表达，像真人面试官一样说话"""
