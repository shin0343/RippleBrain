/**
 * Types crossing the NestJS API / Next.js web boundary for the RippleBrain
 * vertical. The FastAPI analysis engine owns the full result schema; these
 * cover the fields the organization UI renders and the audit trail stores.
 */

export type RippleBrainRunKind = 'ANALYZE' | 'APPROVE' | 'REJECT';

export interface RippleBrainEvidence {
  source_id: string;
  title: string;
  excerpt: string;
  score?: number | null;
}

export interface RippleBrainImpact {
  department: string;
  affected_documents: string[];
  description: string;
  severity: 'High' | 'Medium' | 'Low';
  owner: string;
  evidence: RippleBrainEvidence[];
  recommended_action: string;
  verified: boolean;
}

export interface RippleBrainException {
  title: string;
  customer: string;
  clause: string;
  applies_through: string;
  explanation: string;
  evidence: RippleBrainEvidence[];
}

export interface RippleBrainAction {
  id: string;
  title: string;
  description: string;
  department: string;
  owner: string;
  priority: 'High' | 'Medium' | 'Low';
  evidence: RippleBrainEvidence[];
  status: 'draft' | 'approved' | 'rejected';
  approval_note: string;
}

export interface RippleBrainAnalysis {
  analysis_id: string;
  retrieval_mode: string;
  old_window_days: number | null;
  new_window_days: number | null;
  effective_date: string | null;
  summary: string;
  impacts: RippleBrainImpact[];
  exceptions: RippleBrainException[];
  actions: RippleBrainAction[];
  sources: RippleBrainEvidence[];
  graph: Record<string, unknown>;
  selected_tools: string[];
  execution_log: string[];
  warnings: string[];
}

export interface RippleBrainRun {
  id: string;
  organizationId: string;
  actorId: string;
  kind: RippleBrainRunKind;
  analysisId: string | null;
  summary: string | null;
  createdAt: string;
}
