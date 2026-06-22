"""Interview Agent — 企业海面助手

Handles the full interview lifecycle:
- Pre-interview: document upload + question bank generation (PR 13)
- During interview: full-duplex voice + STAR probing (PR 14)
- Post-interview: structured scoring + report generation (PR 15)
"""

from app.agents.interview.agent import InterviewAgent, INTERVIEW_AGENT_ID

__all__ = ["InterviewAgent", "INTERVIEW_AGENT_ID"]
