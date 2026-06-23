"""Entity extractor — structured information extraction from JD and resume text.

Rule-based extraction using keyword matching, regex patterns, and section
detection. AI-based deep extraction comes in PR 13 via the InterviewAgent.

Usage:
    from app.services.entity_extractor import EntityExtractor

    jd = EntityExtractor.extract_jd(parsed_doc)
    resume = EntityExtractor.extract_resume(parsed_doc)
    match = EntityExtractor.match(jd, resume)
"""

import re
import logging
from collections import Counter

from app.models.interview import (
    ParsedDocument,
    WorkExperience,
    JDEntities,
    ResumeEntities,
    SkillGap,
    MatchResult,
)

logger = logging.getLogger(__name__)

# ============================================================
# Skill keyword database — common programming, data, design,
# management, and soft skills (Chinese + English)
# ============================================================

_SKILL_KEYWORDS: set[str] = {
    # Programming languages
    "python", "java", "javascript", "typescript", "c++", "c#", "go", "golang",
    "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab",
    "typescript", "js", "ts", "cpp",
    # Web / frameworks
    "react", "vue", "angular", "next.js", "nuxt", "django", "flask",
    "fastapi", "spring", "express", "node.js", "nodejs", ".net",
    "html", "css", "sass", "less", "tailwind",
    # Data / ML
    "sql", "mysql", "postgresql", "mongodb", "redis", "elasticsearch",
    "pytorch", "tensorflow", "pandas", "numpy", "scikit-learn", "spark",
    "hadoop", "kafka", "airflow", "databricks", "snowflake",
    # Cloud / DevOps
    "aws", "azure", "gcp", "docker", "kubernetes", "k8s", "terraform",
    "jenkins", "gitlab", "github", "ci/cd", "linux", "bash",
    # Design
    "figma", "sketch", "adobe xd", "photoshop", "illustrator",
    # Soft skills (Chinese)
    "沟通能力", "团队协作", "领导力", "项目管理", "数据分析",
    "问题解决", "逻辑思维", "创新能力", "抗压能力", "执行力",
    "学习能力", "时间管理", "跨部门", "谈判", "演讲",
    # Soft skills (English)
    "leadership", "communication", "teamwork", "problem solving",
    "agile", "scrum", "product management", "stakeholder management",
    # Business / Management
    "产品设计", "用户研究", "市场分析", "竞品分析", "需求分析",
    "战略规划", "运营管理", "客户关系", "供应链",
    "财务分析", "风险控制", "合规",
    # Languages
    "中文", "英文", "英语", "日语", "韩语", "普通话", "mandarin",
    # Tools
    "excel", "word", "powerpoint", "ppt", "visio", "jira", "confluence",
    "notion", "slack", "teams", "飞书", "钉钉",
}

# Degree level keywords
_EDUCATION_KEYWORDS: dict[str, list[str]] = {
    "博士": ["博士", "phd", "ph.d", "博士研究生", "doctorate"],
    "硕士": ["硕士", "master", "mba", "emba", "硕士研究生", "msc", "ma "],
    "本科": ["本科", "学士", "bachelor", "bs ", "ba ", "b.s.", "b.a.", "大学本科"],
    "大专": ["大专", "专科", "associate", "高职"],
}

# Chinese job title indicators
_TITLE_INDICATORS = [
    "工程师", "经理", "主管", "总监", "架构师", "设计师", "分析师",
    "开发", "前端", "后端", "全栈", "算法", "数据", "产品",
    "运营", "市场", "销售", "人力", "财务", "行政", "实习",
    "engineer", "manager", "director", "lead", "architect", "developer",
    "designer", "analyst", "scientist", "consultant", "specialist",
    "intern", "senior", "junior", "staff", "principal",
]

# Company name indicators
_COMPANY_INDICATORS = [
    "公司", "集团", "科技", "网络", "软件", "信息", "数据",
    "银行", "保险", "证券", "基金", "投资",
    "inc", "ltd", "corp", "corporation", "limited", "co.", "llc",
]


class EntityExtractor:
    """Rule-based entity extraction for JD and resume documents."""

    # ---- Public API ----

    @staticmethod
    def extract_jd(doc: ParsedDocument) -> JDEntities:
        """Extract job requirements from a parsed Job Description."""
        text = doc.raw_text

        position_title = EntityExtractor._extract_position_title(text)
        required_skills, preferred_skills = EntityExtractor._extract_jd_skills(text)
        exp_years = EntityExtractor._extract_experience_years(text)
        education = EntityExtractor._extract_education_level(text)
        responsibilities = EntityExtractor._extract_responsibilities(text)

        return JDEntities(
            position_title=position_title,
            required_skills=required_skills,
            preferred_skills=preferred_skills,
            required_experience_years=exp_years,
            education_level=education,
            responsibilities=responsibilities,
        )

    @staticmethod
    def extract_resume(doc: ParsedDocument) -> ResumeEntities:
        """Extract candidate profile from a parsed resume."""
        text = doc.raw_text

        name = EntityExtractor._extract_name(text)
        email = EntityExtractor._extract_email(text)
        phone = EntityExtractor._extract_phone(text)
        skills = EntityExtractor._extract_resume_skills(text)
        work_experiences = EntityExtractor._extract_work_experiences(text)
        education = EntityExtractor._extract_education(text)
        total_years = sum(exp.years for exp in work_experiences)
        summary = EntityExtractor._extract_resume_summary(text)

        return ResumeEntities(
            name=name,
            email=email,
            phone=phone,
            skills=skills,
            work_experiences=work_experiences,
            education=education,
            total_years=round(total_years, 1),
            summary=summary,
        )

    @staticmethod
    def match(jd: JDEntities, resume: ResumeEntities) -> MatchResult:
        """Compare JD requirements with candidate profile and compute match."""
        # Normalize all skills through alias mapping for accurate comparison
        jd_skills_norm = {_normalize_skill(s) for s in jd.required_skills}
        pref_skills_norm = {_normalize_skill(s) for s in jd.preferred_skills}
        resume_skills_norm = {_normalize_skill(s) for s in resume.skills}

        # Skill matching with normalized comparison
        matched = sorted(jd_skills_norm & resume_skills_norm)
        missing = sorted(jd_skills_norm - resume_skills_norm)
        extra = sorted(resume_skills_norm - jd_skills_norm - pref_skills_norm)

        # Skill gaps (detailed)
        skill_gaps: list[SkillGap] = []
        for skill in jd.required_skills:
            norm = _normalize_skill(skill)
            skill_gaps.append(SkillGap(
                skill=skill,
                required=True,
                candidate_has=norm in resume_skills_norm,
                importance="high",
            ))
        for skill in jd.preferred_skills:
            norm = _normalize_skill(skill)
            skill_gaps.append(SkillGap(
                skill=skill,
                required=False,
                candidate_has=norm in resume_skills_norm,
                importance="medium",
            ))

        # Match percentage: weighted by required vs preferred
        total_required = len(jd.required_skills) + len(jd.preferred_skills)
        if total_required == 0:
            match_pct = 100.0
        else:
            matched_required = len(matched)
            matched_preferred = len(pref_skills_norm & resume_skills_norm)
            match_pct = round(
                (matched_required * 1.5 + matched_preferred * 0.5)
                / (len(jd.required_skills) * 1.5 + len(jd.preferred_skills) * 0.5)
                * 100
                if (len(jd.required_skills) * 1.5 + len(jd.preferred_skills) * 0.5) > 0
                else 100,
                1,
            )

        # Experience match
        experience_match = resume.total_years >= jd.required_experience_years

        # Education match (simple level comparison)
        ed_levels = {"博士": 4, "硕士": 3, "本科": 2, "大专": 1, "": 0}
        req_level = ed_levels.get(jd.education_level, 0)
        candidate_level = max(
            (ed_levels.get(e.get("degree", ""), 0) for e in resume.education),
            default=0,
        )
        education_match = candidate_level >= req_level if req_level > 0 else True

        # Summary
        parts: list[str] = []
        if match_pct >= 80:
            parts.append("候选人技能匹配度高")
        elif match_pct >= 50:
            parts.append("候选人技能匹配度中等")
        else:
            parts.append("候选人技能匹配度较低")
        if experience_match:
            parts.append("工作经验满足要求")
        else:
            parts.append(f"工作经验不足（需{jd.required_experience_years}年）")
        if not education_match:
            parts.append(f"学历不满足要求（需{jd.education_level}）")
        if missing:
            parts.append(f"缺失关键技能：{'、'.join(missing[:5])}")

        return MatchResult(
            match_percentage=match_pct,
            matched_skills=matched,
            missing_skills=missing,
            extra_skills=extra,
            skill_gaps=skill_gaps,
            experience_match=experience_match,
            education_match=education_match,
            summary="。".join(parts) + "。",
        )

    # ---- Private: JD Extraction ----

    @staticmethod
    def _extract_position_title(text: str) -> str:
        """Extract position title from first few lines of JD."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        # Position title is usually in the first 5 lines and contains title indicators
        for line in lines[:5]:
            line_lower = line.lower()
            for indicator in _TITLE_INDICATORS:
                if indicator in line_lower and len(line) < 80:
                    return line
        return ""

    @staticmethod
    def _extract_jd_skills(text: str) -> tuple[list[str], list[str]]:
        """Extract required and preferred skills from JD text."""
        # Find "requirements" / "qualifications" sections
        req_section = EntityExtractor._find_requirements_section(text)

        found_skills: set[str] = set()
        for skill in _SKILL_KEYWORDS:
            if _fuzzy_match_skill(req_section, skill):
                normalized = _normalize_skill(skill)
                found_skills.add(normalized)

        # Split into required vs preferred based on surrounding keywords
        required: list[str] = []
        preferred: list[str] = []

        for skill in sorted(found_skills):
            # Find context around this skill mention
            idx = req_section.lower().find(skill.lower())
            if idx < 0:
                idx = text.lower().find(skill.lower())
            context_start = max(0, idx - 100)
            context = text[context_start:idx + len(skill) + 50].lower()

            if any(kw in context for kw in ["优先", "prefer", "plus", "bonus", "nice to have",
                                              "加分", "熟悉"]):
                preferred.append(skill)
            else:
                required.append(skill)

        return required, preferred

    @staticmethod
    def _find_requirements_section(text: str) -> str:
        """Heuristically locate the requirements/qualifications section of a JD."""
        # Common section headers
        section_markers = [
            "任职要求", "岗位要求", "职位要求", "能力要求", "技能要求",
            "qualifications", "requirements", "skills required",
            "我们需要", "希望你", "你需要具备",
        ]

        lines = text.split("\n")
        start_idx = 0
        for i, line in enumerate(lines):
            line_lower = line.strip().lower()
            for marker in section_markers:
                if marker in line_lower:
                    start_idx = i
                    break
            if start_idx > 0:
                break

        # Take ~30 lines from the section start (covers most JD requirement blocks)
        section = "\n".join(lines[start_idx:start_idx + 30])
        return section if section.strip() else text  # Fallback: use full text

    @staticmethod
    def _extract_experience_years(text: str) -> float:
        """Extract required years of experience from JD text."""
        # First, try range patterns like "3-5年" → take lower bound
        range_pattern = re.compile(
            r"(\d+)\s*[\-–—至到~]\s*(\d+)\s*年",
        )
        match = range_pattern.search(text)
        if match:
            try:
                years = float(match.group(1))
                if 0 < years <= 50:
                    return years
            except (ValueError, IndexError):
                pass

        patterns = [
            r"(\d+)[\s\-]*年.*?(?:以上|经验|工作)",
            r"(\d+)[\s\-]*(\d+)?\s*(?:years|yrs).*?(?:experience|work)",
            r"(?:experience|经验).*?(\d+)[\s\-]*年",
            r"(\d+)[\s\-]*年以上.*?(?:相关)?(?:工作|行业)?经验",
            r"(\d+)\+?\s*(?:years|年)",
            r"(?:工作经验|工作年限).*?(\d+)[\s\-]*年",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    years = float(match.group(1))
                    if 0 < years <= 50:
                        return years
                except (ValueError, IndexError):
                    continue
        return 0.0

    @staticmethod
    def _extract_education_level(text: str) -> str:
        """Extract minimum education requirement from JD."""
        text_lower = text.lower()
        # Check in order of highest degree (JD usually states minimum)
        for level, keywords in _EDUCATION_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    return level
        return ""

    @staticmethod
    def _extract_responsibilities(text: str) -> list[str]:
        """Extract job responsibilities from JD (list items)."""
        lines = text.split("\n")
        duties: list[str] = []

        # Find the responsibilities section
        duty_markers = [
            "岗位职责", "工作职责", "职责描述", "工作内容",
            "responsibilities", "duties", "你将负责", "工作包括",
        ]
        in_section = False
        section_start = 0
        for i, line in enumerate(lines):
            line_lower = line.strip().lower()
            if not in_section:
                for marker in duty_markers:
                    if marker in line_lower:
                        in_section = True
                        section_start = i
                        break
            if in_section:
                # Stop at next section header
                if i > section_start + 1 and (
                    line.strip().endswith("：")
                    or line.strip().endswith(":")
                    or any(
                        m in line_lower
                        for m in ["任职要求", "岗位要求", "qualification", "requirement"]
                    )
                ):
                    break

        if in_section:
            section_lines = lines[section_start + 1 : i + 1]
        else:
            # Fallback: scan all lines for list items
            section_lines = lines

        for line in section_lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Detect list items
            if (
                re.match(r"^[\d]+[\.\)、]", stripped)
                or re.match(r"^[-\•\*●►✓]", stripped)
                or stripped.startswith("负责")
                or stripped.startswith("参与")
                or stripped.startswith("协助")
            ):
                # Clean the prefix
                cleaned = re.sub(r"^[\d]+[\.\)、]\s*", "", stripped)
                cleaned = re.sub(r"^[-\•\*●►✓]\s*", "", cleaned)
                if len(cleaned) > 5:
                    duties.append(cleaned)

        return duties[:15]  # Cap at 15 duties

    # ---- Private: Resume Extraction ----

    @staticmethod
    def _extract_name(text: str) -> str:
        """Extract candidate name from resume — usually first line."""
        lines = [l.strip() for l in text.split("\n") if l.strip()]
        if not lines:
            return ""

        # First line is often the name (especially in Chinese resumes)
        first = lines[0]
        # Check if it looks like a name — Chinese (2-4 chars) or English (two words)
        chinese_name = re.match(r"^([一-鿿]{2,4})$", first)
        if chinese_name:
            return chinese_name.group(1)

        # English name: two words, no digits, no @
        english_name = re.match(r"^([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})$", first)
        if english_name:
            return english_name.group(1)

        return first[:30]

    @staticmethod
    def _extract_email(text: str) -> str:
        """Extract email address from resume text."""
        match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
        return match.group(0) if match else ""

    @staticmethod
    def _extract_phone(text: str) -> str:
        """Extract phone number from resume text."""
        # Chinese mobile: 1[3-9]XXXXXXXXX
        match = re.search(r"1[3-9]\d{9}", text)
        if match:
            return match.group(0)
        # International or formatted
        match = re.search(r"(?:\+86[\s-]?)?1[3-9]\d[\s-]?\d{4}[\s-]?\d{4}", text)
        if match:
            return re.sub(r"[\s-]", "", match.group(0))
        return ""

    @staticmethod
    def _extract_resume_skills(text: str) -> list[str]:
        """Extract skills from resume using fuzzy keyword matching."""
        found: set[str] = set()
        for skill in _SKILL_KEYWORDS:
            if _fuzzy_match_skill(text, skill):
                # Normalize through alias to avoid duplicates
                normalized = _normalize_skill(skill)
                found.add(normalized)
        return sorted(found)

    @staticmethod
    def _extract_work_experiences(text: str) -> list[WorkExperience]:
        """Extract work experience entries from resume text."""
        # Detect the experience section
        exp_markers = [
            "工作经历", "工作经验", "工作履历", "实习经历", "项目经历",
            "work experience", "professional experience", "employment",
        ]

        lines = text.split("\n")
        exp_section_start = -1
        exp_section_end = len(lines)

        for i, line in enumerate(lines):
            line_lower = line.strip().lower()
            for marker in exp_markers:
                if marker in line_lower:
                    exp_section_start = i
                    break
            if exp_section_start >= 0:
                break

        # If no section found, scan the whole document
        section = (
            lines[exp_section_start:]
            if exp_section_start >= 0
            else lines
        )

        # Stop at education section if present
        ed_markers = ["教育", "education", "academic"]
        for i, line in enumerate(section):
            line_lower = line.strip().lower()
            if any(m in line_lower for m in ed_markers):
                exp_section_end = i
                break

        section = section[:exp_section_end]

        # Parse individual experience entries
        experiences: list[WorkExperience] = []
        # Date range pattern
        date_pattern = re.compile(
            r"(\d{4}[./年-]\d{1,2})[至\s\-~到—]+(\d{4}[./年-]\d{1,2}|至今|现在|present|now)",
        )

        # Collect blocks: each entry starts with a date or company/title line
        current_block: list[str] = []
        for line in section:
            stripped = line.strip()
            if not stripped:
                if current_block:
                    exp = EntityExtractor._parse_experience_block(
                        "\n".join(current_block), date_pattern
                    )
                    if exp.company or exp.title:
                        experiences.append(exp)
                    current_block = []
                continue
            current_block.append(stripped)

        # Don't forget the last block
        if current_block:
            exp = EntityExtractor._parse_experience_block(
                "\n".join(current_block), date_pattern
            )
            if exp.company or exp.title:
                experiences.append(exp)

        return experiences

    @staticmethod
    def _parse_experience_block(
        block: str, date_pattern: re.Pattern
    ) -> WorkExperience:
        """Parse a single work experience block (company + title + dates)."""
        lines = [l.strip() for l in block.split("\n") if l.strip()]
        if not lines:
            return WorkExperience()

        exp = WorkExperience()

        # Find date range
        for line in lines:
            date_match = date_pattern.search(line)
            if date_match:
                exp.start_date = date_match.group(1)
                exp.end_date = date_match.group(2)
                exp.years = EntityExtractor._compute_years(
                    exp.start_date, exp.end_date
                )
                break

        # Find company and title
        for line in lines:
            line_lower = line.lower()
            # Company
            if not exp.company:
                for indicator in _COMPANY_INDICATORS:
                    if indicator in line_lower:
                        exp.company = line
                        break
            # Title
            if not exp.title:
                for indicator in _TITLE_INDICATORS:
                    if indicator in line_lower:
                        exp.title = line
                        break

        # Description = remaining lines
        desc_parts = [
            l for l in lines
            if l not in (exp.company, exp.title)
            and not date_pattern.search(l)
        ]
        if desc_parts:
            exp.description = " ".join(desc_parts)

        return exp

    @staticmethod
    def _compute_years(start: str, end: str) -> float:
        """Compute years from date strings like '2020.06' to '2023.12'."""
        if not start:
            return 0.0

        def _parse_date(s: str) -> float:
            """Parse date string to fractional year."""
            s = s.replace(".", "-").replace("/", "-").replace("年", "-").replace("月", "")
            parts = s.split("-")
            year = float(parts[0]) if parts[0] else 0
            month = float(parts[1]) / 12 if len(parts) > 1 and parts[1] else 0
            return year + month

        try:
            start_val = _parse_date(start)
            if end in ("至今", "现在", "present", "now", ""):
                import datetime
                now = datetime.datetime.now()
                end_val = now.year + now.month / 12.0
            else:
                end_val = _parse_date(end)
            return round(end_val - start_val, 1)
        except (ValueError, IndexError):
            return 0.0

    @staticmethod
    def _extract_education(text: str) -> list[dict]:
        """Extract education entries from resume."""
        education: list[dict] = []

        # Find education section
        ed_markers = ["教育背景", "教育经历", "教育", "education", "academic"]
        lines = text.split("\n")
        ed_start = -1

        for i, line in enumerate(lines):
            line_lower = line.strip().lower()
            for marker in ed_markers:
                if marker in line_lower:
                    ed_start = i
                    break
            if ed_start >= 0:
                break

        section = lines[ed_start:] if ed_start >= 0 else lines
        section = section[:15]  # Education sections are usually short

        # Extract degree, school, major, year
        for line in section:
            stripped = line.strip()
            if not stripped or len(stripped) < 4:
                continue

            entry: dict = {"school": "", "degree": "", "major": "", "year": ""}

            # Detect degree
            for degree, keywords in _EDUCATION_KEYWORDS.items():
                for kw in keywords:
                    if kw in stripped.lower():
                        entry["degree"] = degree
                        break
                if entry["degree"]:
                    break

            # Detect school (contains 大学/学院/university)
            if any(kw in stripped for kw in ["大学", "学院", "university", "college"]):
                entry["school"] = stripped

            # Detect year
            year_match = re.search(r"(\d{4})", stripped)
            if year_match:
                entry["year"] = year_match.group(1)

            if entry["degree"] or entry["school"]:
                education.append(entry)

        return education

    @staticmethod
    def _extract_resume_summary(text: str) -> str:
        """Extract candidate self-assessment / summary section from resume."""
        # Common section headers for self-assessment in Chinese & English resumes
        summary_markers = [
            "自我评价", "个人总结", "个人简介", "自我介绍", "求职意向",
            "自我描述", "关于我", "个人评价", "专业总结",
            "summary", "profile", "objective", "about me",
            "professional summary", "career objective",
        ]

        lines = text.split("\n")
        summary_start = -1

        for i, line in enumerate(lines):
            line_lower = line.strip().lower()
            for marker in summary_markers:
                if marker in line_lower:
                    summary_start = i
                    break
            if summary_start >= 0:
                break

        if summary_start < 0:
            # Fallback: use first 3 substantive lines after name/contact
            for i, line in enumerate(lines):
                stripped = line.strip()
                if not stripped:
                    continue
                # Skip name/contact lines
                if (re.match(r"^[一-鿿]{2,4}$", stripped)
                        or "@" in stripped
                        or re.search(r"1[3-9]\d{9}", stripped)
                        or len(stripped) < 8):
                    continue
                # Take the next few substantive text blocks
                summary_lines = [
                    l.strip() for l in lines[i:i + 8]
                    if l.strip()
                    and "工作" not in l
                    and "教育" not in l
                    and "项目" not in l
                    and "skill" not in l.lower()
                    and not re.search(r"1[3-9]\d{9}", l)
                    and "@" not in l
                ]
                if summary_lines:
                    return " ".join(summary_lines[:4])
                break
            return ""

        # Collect text from the summary section until next section
        summary_lines: list[str] = []
        section_markers = [
            "工作", "教育", "技能", "项目", "联系方式", "语言",
            "experience", "education", "skill", "project", "contact", "language",
        ]
        for line in lines[summary_start + 1:]:
            stripped = line.strip()
            if not stripped:
                if summary_lines:
                    break  # blank line ends a paragraph
                continue
            # Stop at next section
            line_lower = stripped.lower()
            if any(m in line_lower for m in section_markers):
                break
            if len(stripped) > 5:
                summary_lines.append(stripped)
            if len(summary_lines) >= 6:  # Max 6 lines
                break

        return " ".join(summary_lines) if summary_lines else ""


# ---- Skill alias mapping (normalize common variations) ----

_SKILL_ALIASES: dict[str, str] = {
    "js": "javascript",
    "ts": "typescript",
    "cpp": "c++",
    "k8s": "kubernetes",
    "nodejs": "node.js",
    "golang": "go",
    "react.js": "react",
    "vue.js": "vue",
    "next": "next.js",
    ".net core": ".net",
    "asp.net": ".net",
    "express.js": "express",
    "postgres": "postgresql",
    "mongo": "mongodb",
    "elastic": "elasticsearch",
    "tensorflow": "tensorflow",
    "pytorch": "pytorch",
    "scikit": "scikit-learn",
    "sklearn": "scikit-learn",
    "tf": "tensorflow",
    "cicd": "ci/cd",
    "github actions": "ci/cd",
    "gitlab ci": "ci/cd",
    "aws": "aws",
    "azure": "azure",
    "gcp": "gcp",
    "ecs": "docker",
    "容器": "docker",
    "容器化": "docker",
    "微服务": "microservices",
    "分布式": "分布式系统",
    "高并发": "高并发",
    "ddd": "领域驱动设计",
    "tdd": "测试驱动开发",
    "restful": "rest api",
    "rest": "rest api",
    "graphql": "graphql",
    "grpc": "grpc",
    "消息队列": "kafka",
    "rabbitmq": "kafka",
    "redis": "redis",
    "缓存": "redis",
    "nginx": "nginx",
    "linux": "linux",
    "shell": "bash",
}


def _normalize_skill(name: str) -> str:
    """Normalize a skill name through alias mapping."""
    return _SKILL_ALIASES.get(name.lower(), name.lower())


def _fuzzy_match_skill(text: str, skill: str) -> bool:
    """Check if a skill appears in text, with fuzzy matching.

    Handles:
    - Exact match (case-insensitive)
    - Spacing differences (e.g., "node js" ↔ "node.js")
    - Alias normalization (e.g., "k8s" ↔ "kubernetes")
    """
    text_norm = text.lower().replace(" ", "").replace(".", "").replace("-", "").replace("_", "")
    skill_norm = skill.lower().replace(" ", "").replace(".", "").replace("-", "").replace("_", "")

    # Direct match
    if skill_norm in text_norm:
        return True

    # Check alias
    alias = _SKILL_ALIASES.get(skill.lower(), "")
    if alias:
        alias_norm = alias.replace(" ", "").replace(".", "").replace("-", "").replace("_", "")
        if alias_norm in text_norm:
            return True

    return False


def _fuzzy_contains(text: str, term: str) -> bool:
    """Check if term appears in text, ignoring spacing differences."""
    return term.replace(" ", "") in text.replace(" ", "").lower()
