"""流水线内部数据结构：岗位原始信息与解析结果。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Job:
    """一条岗位原始信息（来自列表页/详情页抓取）。"""

    title: str = ""
    company: str = ""
    city: str = ""
    salary: str = ""
    hr_id: str = ""
    platform_job_id: str = ""
    jd_text: str = ""

    @property
    def jd_hash(self) -> str:
        """JD 去重哈希，用于黑名单/去重/caching。"""
        import hashlib

        digest = hashlib.sha1(self.jd_text.encode("utf-8")).hexdigest()
        return digest


@dataclass
class ParsedJd:
    """结构化 JD（由 LLM 解析填充，未接入前为空字段）。"""

    title: str = ""
    skills: list[str] = field(default_factory=list)
    hard_requirements: list[str] = field(default_factory=list)
    soft_requirements: list[str] = field(default_factory=list)
    salary_range: str | None = None
    city: str | None = None
    company_name: str | None = None