"""LLM 结构化输出 Schema（Pydantic v2）。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class JdStructured(BaseModel):
    """岗位 JD 结构化结果。"""

    title: str = ""
    skills: list[str] = Field(default_factory=list)
    hard_requirements: list[str] = Field(default_factory=list)  # 学历/年限/行业等硬性
    soft_requirements: list[str] = Field(default_factory=list)
    salary_range: str | None = None
    city: str | None = None
    company_name: str | None = None


class JobEvaluation(BaseModel):
    """岗位匹配评估结果。"""

    match_score: int = Field(ge=0, le=100, description="匹配得分 0-100")
    reasons: list[str] = Field(default_factory=list, description="匹配或不匹配原因")
    should_apply: bool = Field(description="是否建议发起沟通")
    custom_intro: str | None = Field(default=None, description="个性化打招呼话术")


class IntroGeneration(BaseModel):
    """沟通开场话术生成结果。"""

    intro: str