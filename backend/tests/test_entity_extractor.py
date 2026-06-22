"""Unit tests for EntityExtractor — JD and resume entity extraction."""

from __future__ import annotations

import pytest

from app.models.interview import (
    ParsedDocument,
    JDEntities,
    ResumeEntities,
    WorkExperience,
    MatchResult,
)
from app.services.entity_extractor import EntityExtractor


# ---- Fixtures ----


@pytest.fixture
def sample_jd_doc() -> ParsedDocument:
    """A realistic Chinese JD."""
    text = """高级 Python 后端工程师

岗位职责：
1. 负责公司核心业务系统的后端架构设计与开发
2. 参与系统性能优化、代码审查和技术方案评审
3. 协助团队完成技术难点攻关

任职要求：
- 本科及以上学历，计算机相关专业
- 3年以上 Python 后端开发经验
- 熟练掌握 Django 或 FastAPI 框架
- 熟悉 MySQL、Redis、MongoDB 等数据库
- 熟悉 Docker 容器化部署
- 优先：熟悉 Kubernetes、AWS
- 优先：有微服务架构经验

我们提供：
- 有竞争力的薪资
- 弹性工作制
"""
    return ParsedDocument(raw_text=text, metadata={"file_name": "jd.pdf"})


@pytest.fixture
def sample_resume_doc() -> ParsedDocument:
    """A realistic Chinese resume."""
    text = """李明

联系方式：liming@example.com | 13800138000

技能：Python, FastAPI, MySQL, Redis, Docker, JavaScript

工作经历：

2020.06 - 至今  某科技有限公司  Python 开发工程师
负责后端 API 开发，使用 FastAPI 构建微服务
参与数据库设计，优化慢查询

2018.07 - 2020.05  某某网络公司  初级 Python 开发
负责 Web 后台管理系统开发

教育背景：

2014.09 - 2018.06  某某大学  计算机科学与技术  本科
"""
    return ParsedDocument(raw_text=text, metadata={"file_name": "resume.pdf"})


@pytest.fixture
def sample_resume_doc_english() -> ParsedDocument:
    """A realistic English resume."""
    text = """John Smith
Email: john.smith@email.com
Phone: +86 138 0000 1111

Skills: Python, React, TypeScript, AWS, Docker, PostgreSQL

Work Experience:

2021.03 - Present  Tech Corp Inc.  Senior Software Engineer
Led backend team, designed microservice architecture

2019.01 - 2021.02  Startup XYZ Ltd.  Full Stack Developer
Built web apps with React and Django

Education:

2015.09 - 2019.06  MIT  Computer Science  Bachelor
"""
    return ParsedDocument(raw_text=text, metadata={"file_name": "resume_en.pdf"})


# ---- JD Extraction Tests ----


class TestJDExtraction:
    """Test entity extraction from Job Descriptions."""

    def test_extract_skills(self, sample_jd_doc):
        """JD required and preferred skills are extracted."""
        jd = EntityExtractor.extract_jd(sample_jd_doc)

        assert "python" in [s.lower() for s in jd.required_skills]
        assert "fastapi" in [s.lower() for s in jd.required_skills]
        assert "docker" in [s.lower() for s in jd.required_skills]

        # Preferred skills should be separate
        preferred_lower = [s.lower() for s in jd.preferred_skills]
        assert "kubernetes" in preferred_lower or "aws" in preferred_lower

    def test_extract_experience_years(self, sample_jd_doc):
        """Required years of experience is extracted."""
        jd = EntityExtractor.extract_jd(sample_jd_doc)
        assert jd.required_experience_years == 3.0

    def test_extract_education(self, sample_jd_doc):
        """Education requirement is extracted."""
        jd = EntityExtractor.extract_jd(sample_jd_doc)
        assert jd.education_level == "本科"

    def test_extract_responsibilities(self, sample_jd_doc):
        """Job responsibilities are extracted."""
        jd = EntityExtractor.extract_jd(sample_jd_doc)
        assert len(jd.responsibilities) >= 2
        assert any("后端" in r for r in jd.responsibilities)

    def test_extract_empty_doc(self):
        """Empty document returns empty entities."""
        empty = ParsedDocument(raw_text="")
        jd = EntityExtractor.extract_jd(empty)
        assert jd.required_skills == []
        assert jd.required_experience_years == 0.0
        assert jd.education_level == ""

    def test_experience_years_multiple_formats(self):
        """Various experience year formats are handled."""
        cases = [
            ("3年以上开发经验", 3.0),
            ("5年以上相关工作经验", 5.0),
            ("工作经验要求 2年", 2.0),
            ("10+ years experience", 10.0),
            ("8-10年经验", 8.0),
        ]
        for text, expected in cases:
            doc = ParsedDocument(raw_text=text)
            jd = EntityExtractor.extract_jd(doc)
            assert jd.required_experience_years == expected, f"Failed for: {text}"


# ---- Resume Extraction Tests ----


class TestResumeExtraction:
    """Test entity extraction from resumes."""

    def test_extract_name_chinese(self, sample_resume_doc):
        """Chinese name is extracted from first line."""
        resume = EntityExtractor.extract_resume(sample_resume_doc)
        assert resume.name == "李明"

    def test_extract_name_english(self, sample_resume_doc_english):
        """English name is extracted."""
        resume = EntityExtractor.extract_resume(sample_resume_doc_english)
        assert "John" in resume.name

    def test_extract_email(self, sample_resume_doc):
        """Email is extracted."""
        resume = EntityExtractor.extract_resume(sample_resume_doc)
        assert resume.email == "liming@example.com"

    def test_extract_phone(self, sample_resume_doc):
        """Phone number is extracted."""
        resume = EntityExtractor.extract_resume(sample_resume_doc)
        assert "13800138000" in resume.phone

    def test_extract_skills(self, sample_resume_doc):
        """Skills are extracted from skills section."""
        resume = EntityExtractor.extract_resume(sample_resume_doc)
        skills_lower = [s.lower() for s in resume.skills]
        assert "python" in skills_lower
        assert "fastapi" in skills_lower
        assert "docker" in skills_lower

    def test_extract_work_experiences(self, sample_resume_doc):
        """Work experiences are extracted with dates."""
        resume = EntityExtractor.extract_resume(sample_resume_doc)
        assert len(resume.work_experiences) >= 1
        exp = resume.work_experiences[0]
        assert exp.title != "" or exp.company != ""
        assert resume.total_years > 0

    def test_extract_education(self, sample_resume_doc):
        """Education entries are extracted."""
        resume = EntityExtractor.extract_resume(sample_resume_doc)
        assert len(resume.education) >= 1
        assert any("大学" in str(e) for e in resume.education)

    def test_empty_resume(self):
        """Empty resume returns empty entities."""
        empty = ParsedDocument(raw_text="")
        resume = EntityExtractor.extract_resume(empty)
        assert resume.name == ""
        assert resume.skills == []
        assert resume.total_years == 0.0


# ---- Match Tests ----


class TestMatch:
    """Test JD-resume matching logic."""

    def test_match_result_structure(self, sample_jd_doc, sample_resume_doc):
        """Match returns a complete MatchResult."""
        jd = EntityExtractor.extract_jd(sample_jd_doc)
        resume = EntityExtractor.extract_resume(sample_resume_doc)
        result = EntityExtractor.match(jd, resume)

        assert isinstance(result, MatchResult)
        assert 0 <= result.match_percentage <= 100
        assert isinstance(result.matched_skills, list)
        assert isinstance(result.missing_skills, list)
        assert isinstance(result.summary, str)

    def test_match_with_skill_overlap(self):
        """When skills overlap, match percentage is > 0."""
        jd = JDEntities(required_skills=["Python", "FastAPI", "Docker"])
        resume = ResumeEntities(skills=["Python", "FastAPI", "JavaScript"])
        result = EntityExtractor.match(jd, resume)

        assert result.match_percentage > 0
        assert "python" in result.matched_skills
        assert "fastapi" in result.matched_skills
        assert "docker" in result.missing_skills

    def test_match_perfect(self):
        """All skills match yields 100%."""
        jd = JDEntities(required_skills=["Python", "FastAPI"])
        resume = ResumeEntities(skills=["Python", "FastAPI", "Extra"])
        result = EntityExtractor.match(jd, resume)

        assert result.match_percentage == 100.0
        assert len(result.missing_skills) == 0

    def test_match_no_skills(self):
        """No skill requirements yields full match."""
        jd = JDEntities(required_skills=[], preferred_skills=[])
        resume = ResumeEntities(skills=["Python"])
        result = EntityExtractor.match(jd, resume)

        assert result.match_percentage == 100.0

    def test_match_experience_check(self):
        """Experience match flag works."""
        jd = JDEntities(required_experience_years=5.0)
        resume = ResumeEntities(total_years=4.0)
        result = EntityExtractor.match(jd, resume)

        assert result.experience_match is False

        resume2 = ResumeEntities(total_years=6.0)
        result2 = EntityExtractor.match(jd, resume2)
        assert result2.experience_match is True

    def test_match_education_check(self):
        """Education match flag works."""
        jd = JDEntities(education_level="硕士")
        resume = ResumeEntities(education=[
            {"school": "某大学", "degree": "本科", "major": "CS", "year": "2018"}
        ])
        result = EntityExtractor.match(jd, resume)

        assert result.education_match is False

        resume2 = ResumeEntities(education=[
            {"school": "某大学", "degree": "硕士", "major": "CS", "year": "2020"}
        ])
        result2 = EntityExtractor.match(jd, resume2)
        assert result2.education_match is True
