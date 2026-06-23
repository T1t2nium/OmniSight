"""InterviewAgent — 企业海面助手

A scenario-specific agent that guides structured interviews:
- Pre-interview: analyzes JD + resume, generates tailored question bank
- During interview: applies STAR method, probes skill gaps
- Post-interview: scores responses, generates decision report

Registered in main.py lifespan alongside ChatAgent.
"""

from app.agents.base import BaseAgent

INTERVIEW_AGENT_ID = "interview"

INTERVIEW_SYSTEM_PROMPT = """# 角色：专业面试官

你是一位资深的企业面试官，具备 10 年以上技术岗位面试经验。你的任务是基于岗位描述(JD)和候选人简历，进行结构化面试。

## 核心能力
- 精准评估候选人的技术能力和文化匹配度
- 熟练运用 STAR 法则（情景-任务-行动-结果）设计行为问题
- 根据简历与 JD 的技能缺口进行针对性追问
- 保持专业、客观、公正的面试态度

## 面试原则
1. 从破冰问题开始，营造轻松的面试氛围
2. 基于 JD 要求逐一考察核心技能，优先关注技能缺口
3. 使用 STAR 法则追问项目经历，验证简历真实性
4. 适时施加合理压力，测试候选人的应变能力
5. 每个回答后给出简短反馈，保持对话流畅

## 约束
- 每次只问一个问题，等待候选人回答后再追问
- 回复控制在 1-3 句话，避免长篇大论
- 不评价候选人的个人特征（外貌、年龄、性别等）
- 不透露公司的内部敏感信息

## 输出格式
纯文本对话，一次一个问题。适当使用追问词（"能详细说说吗？""当时的背景是什么？""你具体负责哪些部分？"）
"""


class InterviewAgent(BaseAgent):
    """Enterprise interview assistant agent.

    Provides interview-specific system prompt and UI configuration
    that enables document upload and question bank components.
    """

    @property
    def agent_id(self) -> str:
        return INTERVIEW_AGENT_ID

    @property
    def name(self) -> str:
        return "企业海面助手"

    @property
    def description(self) -> str:
        return "上传JD和简历，AI自动生成结构化面试题库并引导面试"

    @property
    def system_prompt(self) -> str:
        return INTERVIEW_SYSTEM_PROMPT

    def get_ui_config(self) -> dict:
        return {
            "show_document_upload": True,
            "show_question_bank": True,
            "header_color": "#10b981",
        }
