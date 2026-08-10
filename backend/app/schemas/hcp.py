"""Pydantic schemas for API requests and responses."""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PipelineStage(str, Enum):
    INIT = "init"
    FETCHING_NPI = "fetching_npi"
    COLLECTING_DATA = "collecting_data"
    NORMALIZING = "normalizing"
    FEATURE_ENGINEERING = "feature_engineering"
    ML_PREDICTION = "ml_prediction"
    GENERATING_SUMMARY = "generating_summary"
    JUDGING_SUMMARY = "judging_summary"
    GENERATING_PDF = "generating_pdf"
    COMPLETE = "complete"
    FAILED = "failed"


class HCPProfileRequest(BaseModel):
    npi: str = Field(..., min_length=10, max_length=10, description="10-digit NPI number")

    @field_validator("npi")
    @classmethod
    def validate_npi(cls, v: str) -> str:
        cleaned = v.strip()
        if not cleaned.isdigit():
            raise ValueError("NPI must contain only digits")
        if len(cleaned) != 10:
            raise ValueError("NPI must be exactly 10 digits")
        return cleaned


class Address(BaseModel):
    line1: str = ""
    line2: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    country: str = "US"


class NPIData(BaseModel):
    npi: str
    entity_type: str = ""
    first_name: str = ""
    last_name: str = ""
    organization_name: str = ""
    credential: str = ""
    taxonomy_code: str = ""
    taxonomy_description: str = ""
    primary_specialty: str = ""
    address: Address = Field(default_factory=Address)
    phone: str = ""
    enumeration_date: str = ""
    last_updated: str = ""
    status: str = ""


class Publication(BaseModel):
    pmid: str = ""
    title: str = ""
    journal: str = ""
    pub_date: str = ""
    authors: list[str] = Field(default_factory=list)


class ClinicalTrial(BaseModel):
    nct_id: str = ""
    title: str = ""
    status: str = ""
    phase: str = ""
    role: str = ""
    start_date: str = ""


class AdverseEventSummary(BaseModel):
    drug_name: str = ""
    event_count: int = 0
    serious_count: int = 0


class SourceResult(BaseModel):
    source: str
    success: bool
    record_count: int = 0
    error: str | None = None
    fetched_at: datetime = Field(default_factory=datetime.utcnow)


class MLFeatures(BaseModel):
    publication_count: int = 0
    first_author_count: int = 0
    clinical_trial_count: int = 0
    pi_trial_count: int = 0
    collaborator_count: int = 0
    unique_collaborator_count: int = 0
    strongest_collaboration_count: int = 0
    average_collaboration_strength: float = 0.0
    collaboration_network_density: float = 0.0
    recurring_collaborator_ratio: float = 0.0
    years_active: int = 0
    adverse_event_reports: int = 0


class MLPrediction(BaseModel):
    model_name: str
    influence_score: float = Field(ge=0.0, le=100.0)
    kol_tier: str = ""
    confidence: float = Field(ge=0.0, le=1.0, default=0.0)
    feature_importance: dict[str, float] = Field(default_factory=dict)


class CollaborationNode(BaseModel):
    id: str
    label: str
    type: str
    npi: str | None = None
    publication_count: int = 0
    shared_publications: int = 0
    publications: list[Publication] = Field(default_factory=list)


class CollaborationEdge(BaseModel):
    source: str
    target: str
    weight: int


class CollaborationMetrics(BaseModel):
    total_publications: int = 0
    total_collaborators: int = 0
    unique_collaborators: int = 0
    strongest_collaborator: str = ""
    max_shared_publications: int = 0
    average_collaborations_per_author: float = 0.0
    collaboration_network_density: float = 0.0


class CollaborationNetwork(BaseModel):
    hcp: dict[str, str]
    metrics: CollaborationMetrics = Field(default_factory=CollaborationMetrics)
    nodes: list[CollaborationNode] = Field(default_factory=list)
    edges: list[CollaborationEdge] = Field(default_factory=list)


class JudgeEvaluation(BaseModel):
    overall_score: float = Field(ge=0.0, le=10.0)
    groundedness: float = Field(ge=0.0, le=10.0)
    completeness: float = Field(ge=0.0, le=10.0)
    clarity: float = Field(ge=0.0, le=10.0)
    feedback: str = ""
    passed: bool = False
    judge_model: str = ""
    evaluation_scope: str = "Final HCP profile"


class HCPProfile(BaseModel):
    npi: str
    identity: NPIData = Field(default_factory=NPIData)
    publications: list[Publication] = Field(default_factory=list)
    clinical_trials: list[ClinicalTrial] = Field(default_factory=list)
    collaboration_network: CollaborationNetwork | None = None
    adverse_events: list[AdverseEventSummary] = Field(default_factory=list)
    features: MLFeatures = Field(default_factory=MLFeatures)
    ml_predictions: list[MLPrediction] = Field(default_factory=list)
    ai_summary: str = ""
    judge_evaluation: JudgeEvaluation | None = None
    source_results: list[SourceResult] = Field(default_factory=list)
    pdf_path: str | None = None
    generated_at: datetime = Field(default_factory=datetime.utcnow)


class PipelineProgress(BaseModel):
    npi: str
    stage: PipelineStage
    progress_pct: int = Field(ge=0, le=100)
    message: str = ""
    sources_completed: list[str] = Field(default_factory=list)


class HCPProfileResponse(BaseModel):
    success: bool
    profile: HCPProfile | None = None
    progress: PipelineProgress | None = None
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    version: str
    azure_configured: bool
    gemini_configured: bool
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class ErrorResponse(BaseModel):
    detail: str
    error_code: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
