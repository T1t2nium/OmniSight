"""During-interview engine — coordinates real-time interview using Bailian Realtime WS.

Manages the bidirectional event relay between the Bailian OmniRealtime WebSocket
and the frontend. Builds interview-specific instructions from the question bank,
JD, resume, and match analysis. Applies STAR probing rules in the instructions
so the AI model drives follow-up questions automatically.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Callable, Awaitable

from app.models.interview import (
    InterviewQuestion,
    QuestionBank,
    JDEntities,
    ResumeEntities,
    MatchResult,
)
from app.services.bailian_ws_client import BailianWSClient

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


class DuringInterviewEngine:
    """Orchestrates a real-time interview session.

    Coordinates between BailianWSClient (Bailian Realtime API) and the
    frontend (via WebSocket relay callbacks).

    Usage::

        engine = DuringInterviewEngine(
            ws_client=bailian_ws,
            question_bank=bank,
            jd_entities=jd,
            resume_entities=resume,
            match_result=match,
        )
        instructions = engine.build_instructions()
        await engine.start(instructions)
        await engine.handle_audio_chunk(pcm16_b64)
        async for frontend_msg in engine.receive():
            await send_to_frontend(frontend_msg)
        await engine.stop()
    """

    def __init__(
        self,
        ws_client: BailianWSClient,
        question_bank: QuestionBank,
        jd_entities: JDEntities,
        resume_entities: ResumeEntities,
        match_result: MatchResult,
    ) -> None:
        self._ws = ws_client
        self._bank = question_bank
        self._jd = jd_entities
        self._resume = resume_entities
        self._match = match_result

        # Interview state
        self._current_phase: str = "icebreaker"
        self._transcript: list[dict] = []
        self._started = False

    # ---- Properties ----

    @property
    def transcript(self) -> list[dict]:
        """Complete interview transcript (user + assistant turns)."""
        return self._transcript

    @property
    def is_active(self) -> bool:
        """True while the interview is running."""
        return self._started and self._ws.is_connected

    # ---- Instructions builder ----

    def build_instructions(self) -> str:
        """Build the complete instructions string for Bailian Realtime session.

        Includes:
          1. Interview persona (from InterviewAgent.system_prompt)
          2. Interview structure — phases with question bank
          3. Candidate context — JD + resume + skill gaps
          4. STAR probing rules
          5. Output constraints
        """
        parts: list[str] = []

        # 1. Persona + rules
        parts.append(self._build_persona())

        # 2. Candidate context
        parts.append(self._build_candidate_context())

        # 3. Question bank (truncated if needed)
        parts.append(self._build_question_bank_prompt())

        # 4. STAR probing rules
        parts.append(self._build_star_rules())

        # 5. Output constraints
        parts.append(self._build_constraints())

        instructions = "\n\n".join(parts)

        # Truncate if too long — keep persona + context + constraints,
        # shrink question bank listing (which is the biggest section)
        if len(instructions) > MAX_INSTRUCTIONS_CHARS:
            logger.warning(
                "Instructions too long (%d chars) — truncating question bank",
                len(instructions),
            )
            # Rebuild with fewer questions
            parts[2] = self._build_question_bank_prompt(max_questions=10)
            instructions = "\n\n".join(parts)

        logger.info("Built interview instructions: %d chars", len(instructions))
        return instructions

    def _build_persona(self) -> str:
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

请严格按照以上顺序进行，一个环节完成后再进入下一个。"""

    def _build_candidate_context(self) -> str:
        """Build the candidate + position context section."""
        lines: list[str] = ["# 面试背景信息"]

        # Position
        if self._jd.position_title:
            lines.append(f"**招聘岗位**: {self._jd.position_title}")
        if self._jd.department:
            lines.append(f"**部门**: {self._jd.department}")
        if self._jd.required_skills:
            skills = "、".join(self._jd.required_skills[:10])
            lines.append(f"**岗位核心技能要求**: {skills}")
        if self._jd.responsibilities:
            resp = "；".join(self._jd.responsibilities[:5])
            lines.append(f"**岗位职责**: {resp}")

        # Candidate
        if self._resume.name:
            lines.append(f"**候选人**: {self._resume.name}")
        if self._resume.skills:
            c_skills = "、".join(self._resume.skills[:15])
            lines.append(f"**候选人技能**: {c_skills}")
        if self._resume.total_years > 0:
            lines.append(f"**总工作经验**: {self._resume.total_years:.0f} 年")

        # Skill gaps
        if self._match.missing_skills:
            missing = "、".join(self._match.missing_skills[:8])
            lines.append(f"**⚠️ 技能缺口（需重点考察）**: {missing}")
        if self._match.matched_skills:
            matched = "、".join(self._match.matched_skills[:8])
            lines.append(f"**✅ 已匹配技能**: {matched}")
        if self._match.match_percentage > 0:
            lines.append(f"**综合匹配度**: {self._match.match_percentage:.0f}%")

        return "\n".join(lines)

    def _build_question_bank_prompt(self, max_questions: int = 15) -> str:
        """Build the question bank section — list questions by phase."""
        lines: list[str] = ["# 面试题库（按顺序使用）"]

        if not self._bank.categories:
            lines.append("（无预生成题库，请根据岗位和候选人信息自行提问）")
            return "\n".join(lines)

        question_count = 0
        for phase in PHASES:
            cat = next(
                (c for c in self._bank.categories if c.type == phase), None
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
                    len(c.questions) for c in self._bank.categories
                ) - question_count
                if remaining > 0:
                    lines.append(f"\n*（还有 {remaining} 道题目未列出，可视情况使用）*")
                break

        lines.append(f"\n共计 {self._bank.total_questions} 道题目可供参考。")
        return "\n".join(lines)

    def _build_star_rules(self) -> str:
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

    def _build_constraints(self) -> str:
        """Build output constraints."""
        return """# 输出约束
- 每次只问一个问题，等待候选人回答后再继续
- 回复控制在1-3句话，简洁直接
- 不评价候选人的个人特征（外貌、年龄、性别等）
- 不在对话中使用 Markdown 格式
- 用自然的口语表达，像真人面试官一样说话"""

    # ---- Lifecycle ----

    async def start(self, instructions: str | None = None) -> None:
        """Connect to Bailian Realtime and begin the interview.

        Args:
            instructions: Override instructions. If None, uses self.build_instructions().
        """
        if self._started:
            logger.warning("Interview engine already started")
            return

        prompt = instructions or self.build_instructions()
        await self._ws.connect(instructions=prompt, voice="Cherry")
        self._started = True
        logger.info(
            "Interview started — %d questions in bank, phase=%s",
            self._bank.total_questions, self._current_phase,
        )

    async def handle_audio_chunk(self, pcm16_base64: str) -> None:
        """Relay an audio chunk from the frontend to Bailian."""
        if not self.is_active:
            return
        await self._ws.send_audio(pcm16_base64)

    async def handle_interrupt(self) -> None:
        """Handle user speech start (barge-in) — cancel current AI reply."""
        if not self.is_active:
            return
        await self._ws.cancel_response()
        await self._ws.clear_audio()
        logger.info("Interview: user interrupted AI response")

    async def receive(self) -> AsyncIterator[dict[str, Any]]:
        """Yield events mapped to frontend message format.

        Each yielded dict has keys: ``type`` (frontend message type) and
        ``payload`` (dict to send as-is).
        """
        async for event in self._ws.receive():
            event_type = event.get("type", "")

            mapped = self._map_event(event, event_type)
            if mapped is not None:
                # Track transcript for post-interview scoring
                self._track_transcript(mapped)
                yield mapped

    async def stop(self) -> None:
        """End the interview and close the Bailian connection."""
        self._started = False
        await self._ws.close()
        logger.info(
            "Interview stopped — transcript has %d entries",
            len(self._transcript),
        )

    # ---- Event mapping ----

    def _map_event(
        self, event: dict, event_type: str
    ) -> dict[str, Any] | None:
        """Map a Bailian Realtime event to a frontend message.

        Returns None for events the frontend doesn't need.
        """
        # AI speech text deltas
        if event_type == "response.audio_transcript.delta":
            return {
                "type": "llm_response",
                "payload": {
                    "delta": event.get("delta", ""),
                    "done": False,
                    "total_duration": 0.0,
                },
            }

        # AI speech text complete
        if event_type == "response.audio_transcript.done":
            transcript = event.get("transcript", "")
            return {
                "type": "llm_response",
                "payload": {
                    "delta": "",
                    "done": True,
                    "total_duration": 0.0,
                    "full_text": transcript,
                },
            }

        # AI speech audio deltas
        if event_type == "response.audio.delta":
            return {
                "type": "tts_audio",
                "payload": {
                    "data": event.get("delta", ""),
                    "sample_rate": 24000,
                    "channels": 1,
                    "text": "",
                },
            }

        # User speech recognition
        if event_type == "conversation.item.input_audio_transcription.completed":
            text = event.get("transcript", "")
            if text.strip():
                return {
                    "type": "transcript",
                    "payload": {
                        "text": text,
                        "language": "zh",
                        "duration_ms": 0,
                    },
                }

        # VAD state changes
        if event_type == "input_audio_buffer.speech_started":
            return {
                "type": "ai_status",
                "payload": {"status": "listening"},
            }

        if event_type == "input_audio_buffer.speech_stopped":
            return {
                "type": "ai_status",
                "payload": {"status": "thinking"},
            }

        # AI response complete
        if event_type == "response.done":
            usage = event.get("usage", {})
            if usage:
                logger.info(
                    "Bailian Realtime response done — tokens: in=%d out=%d",
                    usage.get("input_tokens", 0),
                    usage.get("output_tokens", 0),
                )
            return {
                "type": "ai_status",
                "payload": {"status": "idle"},
            }

        # Errors
        if event_type == "error":
            error_msg = event.get("error", "Unknown Bailian error")
            logger.error("Bailian Realtime error: %s", error_msg)
            return {
                "type": "error",
                "payload": {"message": str(error_msg)},
            }

        # Ignored events (no frontend equivalent):
        # session.created, session.updated, response.created,
        # response.output_item.added, conversation.item.created,
        # response.content_part.added, response.content_part.done,
        # response.output_item.done, response.audio.done,
        # input_audio_buffer.committed, response.text.delta,
        # response.text.done, conversation.item.input_audio_transcription.failed
        return None

    # ---- Transcript tracking ----

    def _track_transcript(self, mapped: dict[str, Any]) -> None:
        """Accumulate conversation turns for post-interview analysis."""
        msg_type = mapped.get("type", "")
        payload = mapped.get("payload", {})

        if msg_type == "transcript":
            self._transcript.append({
                "role": "user",
                "content": payload.get("text", ""),
            })
        elif msg_type == "llm_response" and payload.get("done", False):
            full = payload.get("full_text", "") or payload.get("delta", "")
            if full.strip():
                self._transcript.append({
                    "role": "assistant",
                    "content": full,
                })
