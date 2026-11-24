export type RiskLevel = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface RuleHit {
  rule_id: string;
  description: string;
  points: number;
  evidence_refs: string[];
}

export interface ScoreResult {
  score: number;
  risk_level: RiskLevel;
  rule_hits: RuleHit[];
  total_points_before_clamp: number;
}

export interface InconclusiveCheck {
  agent_name: string;
  reason: string;
}

export interface SupervisorAssessment {
  score_result: ScoreResult;
  rule_trace_explanation: string;
  narrative: string | null;
  inconclusive_checks: InconclusiveCheck[];
}

export interface InvestigationSummary {
  id: string;
  domain: string;
  normalized_domain: string;
  risk_score: number;
  risk_level: RiskLevel;
  created_at: string;
}

export interface InvestigationResponse {
  id: string;
  domain: string;
  normalized_domain: string;
  created_at: string;
  assessment: SupervisorAssessment;
}

export interface ListInvestigationsResponse {
  items: InvestigationSummary[];
  total: number;
  limit: number;
  offset: number;
}
