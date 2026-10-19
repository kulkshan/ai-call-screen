"""Contracts shared by the call-screening components.

Each layer returns its own object so transcript analysis, caller context, risk
combination, and the action policy can be tested independently.
"""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Decision = Literal['ALLOW', 'CONTINUE_SCREENING', 'WARN', 'BLOCK']


class SignalEvidence(BaseModel):
    """One observed transcript signal. It is evidence, never a call decision."""
    type: Literal['urgency', 'impersonation', 'payment_request', 'code_request',
                  'personal_info_request', 'threat', 'suspicious_action']
    present: bool
    confidence: float = Field(ge=0, le=1)
    evidence: str = Field(default='', max_length=240)


class ConversationSignals(BaseModel):
    model_config = ConfigDict(extra='forbid')
    impersonation: bool = False
    urgency: bool = False
    credential_request: bool = False
    payment_or_money_request: bool = False
    threatening_language: bool = False
    suspicious_action_request: bool = False


class CallerContext(BaseModel):
    """Caller-side signals. Values are explicitly simulated until data exists."""
    caller_number: str = ''
    caller_number_masked: str = 'Unknown caller'
    known_contact: bool = False
    caller_reputation_score: float = Field(ge=0, le=1)
    prior_spam_reports: int = Field(ge=0)
    recent_call_frequency: int = Field(ge=0)
    source: Literal['simulated'] = 'simulated'


class TranscriptResult(BaseModel):
    transcript_risk_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    detected_signals: list[str] = Field(default_factory=list, max_length=8)
    conversation_signals: ConversationSignals = Field(default_factory=ConversationSignals)
    signal_evidence: list[SignalEvidence] = Field(default_factory=list, max_length=7)
    explanation: str = ''
    sufficient_information: bool = False
    harmful_request: bool = False
    missing_information: Literal['identity_purpose', 'requested_action', 'clarify_request', 'none'] = 'none'
    latency_ms: int = Field(ge=0)
    provider: str = 'Gemini transcript classifier'


class CombinedRisk(BaseModel):
    final_risk_score: float = Field(ge=0, le=1)
    transcript_risk_score: float = Field(ge=0, le=1)
    caller_context_risk_score: float = Field(ge=0, le=1)
    contributing_signals: list[str] = Field(default_factory=list)
    decision_reason: str


class ScreeningOutcome(BaseModel):
    """The one result stored for a completed caller turn and sent to the UI."""
    final_risk_score: float = Field(ge=0, le=1)
    # Keeps the current UI and legacy local `/analyze` consumer compatible.
    risk_score: float = Field(ge=0, le=1)
    transcript_risk_score: float = Field(ge=0, le=1)
    caller_context_risk_score: float = Field(ge=0, le=1)
    confidence: float = Field(ge=0, le=1)
    detected_signals: list[str] = Field(default_factory=list)
    features: ConversationSignals = Field(default_factory=ConversationSignals)
    signal_evidence: list[SignalEvidence] = Field(default_factory=list)
    caller_context: CallerContext
    contributing_signals: list[str] = Field(default_factory=list)
    decision_reason: str
    explanation: str
    decision: Decision
    follow_up_question: str = ''
    latency_ms: int = Field(ge=0)
    classifier: str = 'Gemini transcript classifier'
