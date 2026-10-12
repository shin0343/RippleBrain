---
id: workflow_manifest
title: "Organizational Workflow / Relationship Manifest"
document_type: manifest
owner: "Jordan Lee (Operations)"
department: Operations
version: "2026.10"
created_at: "2026-10-09"
updated_at: "2026-10-09"
effective_from: "2026-10-09"
effective_until: null
source_reference: "ops/manifest/workflows"
status: current
---

# Organizational Workflow / Relationship Manifest (Oct 2026)

Structured topology for graph ingestion. Each line is a declared relationship grounded in the source docs above.

- Refund Policy v2 SUPERSEDES Refund Policy v1 (evidence: v2 "Supersedes Refund Policy v1", effective 2026-10-15).
- Refund Policy v2 IMPACTS Customer Support Refund FAQ (evidence: FAQ still quotes 30 days; update due Oct 14, owner Dana Kim).
- Refund Policy v2 IMPACTS Customer Support Response Templates (evidence: templates R-1/R-3 quote 30 days).
- Refund Policy v2 IMPACTS Sales Onboarding Guide (evidence: talk track promises 30 days).
- Refund Policy v2 IMPACTS Finance Refund Processing SOP / workflow WF-FIN-01 (evidence: SOP step 1 verifies 30-day window).
- ACME Corp Enterprise Agreement APPLIES_TO ACME Corp (evidence: Section 7.3).
- ACME Corp Enterprise Agreement OVERRIDES General Refund Policy for ACME through 2026-12-31 (evidence: Section 7.3; meeting notes item 2).
- Standard Customer Agreement FOLLOWS General Refund Policy dynamically (evidence: Section 4).
- Policy Decision DEC-2026-041 APPROVED_BY Jordan Lee / Operations (evidence: meeting notes).
- Refund triage workflow WF-SUP-02 OWNED_BY Customer Support (Dana Kim).
- Quoting workflow WF-SAL-01 OWNED_BY Sales (Marcus Webb).
- Refund approval workflow WF-FIN-01 OWNED_BY Finance (Priya Nair).
- FAQ + Templates OWNED_BY Customer Support; SOP OWNED_BY Finance; Policies + Contracts OWNED_BY Legal.
- Action follow-ups ASSIGNED_TO Dana Kim (Support), Marcus Webb (Sales), Priya Nair (Finance), Amara Osei (Legal review).

*Synthetic demo data for Northstar Cloud (fictional).*
