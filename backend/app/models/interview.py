"""Pydantic models for Interview Agent — document parsing and entity extraction.

Used by DocumentParser, EntityExtractor, and later the InterviewAgent pipeline.
"""

from pydantic import BaseModel, Field


# ---- Document Parsing ----


class ParsedDocument(BaseModel):
    """Unified result of parsing a PDF or DOCX file.

    raw_text contains the full extracted text. pages holds per-page text
    for page-level analysis (PDF only — DOCX has one entry).
    """

    raw_text: str = ""
    pages: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)  # file_name, page_count, format


# ---- Work Experience ----


class WorkExperience(BaseModel):
    """A single work experience entry extracted from a resume."""

    company: str = ""
    title: str = ""
    start_date: str = ""
    end_date: str = ""
    description: str = ""
    years: float = 0.0


# ---- JD Entities ----


class JDEntities(BaseModel):
    """Structured entities extracted from a Job Description."""

    position_title: str = ""
    required_skills: list[str] = Field(default_factory=list)
    preferred_skills: list[str] = Field(default_factory=list)
    required_experience_years: float = 0.0
    education_level: str = ""  # "本科", "硕士", "博士", "不限"
    responsibilities: list[str] = Field(default_factory=list)
    department: str = ""
    location: str = ""


# ---- Resume Entities ----


class ResumeEntities(BaseModel):
    """Structured entities extracted from a candidate's resume."""

    name: str = ""
    email: str = ""
    phone: str = ""
    skills: list[str] = Field(default_factory=list)
    work_experiences: list[WorkExperience] = Field(default_factory=list)
    education: list[dict] = Field(default_factory=list)  # {school, degree, major, year}
    total_years: float = 0.0
    summary: str = ""


# ---- Matching ----


class SkillGap(BaseModel):
    """A single skill gap between JD requirements and candidate profile."""

    skill: str
    required: bool = True  # True = JD required skill, False = preferred
    candidate_has: bool = False
    importance: str = "medium"  # "high", "medium", "low"


class MatchResult(BaseModel):
    """Result of matching a resume against a job description."""

    match_percentage: float = 0.0  # 0–100
    matched_skills: list[str] = Field(default_factory=list)
    missing_skills: list[str] = Field(default_factory=list)
    extra_skills: list[str] = Field(default_factory=list)
    skill_gaps: list[SkillGap] = Field(default_factory=list)
    experience_match: bool = False
    education_match: bool = False
    summary: str = ""
