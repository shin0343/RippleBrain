---
id: finance_sop
title: "Finance Refund Processing SOP"
document_type: sop
owner: "Priya Nair (Finance Operations)"
department: Finance
version: "3.2"
created_at: "2026-06-01"
updated_at: "2026-09-15"
effective_from: "2026-06-01"
effective_until: null
source_reference: "finance/sop/refund-processing"
status: needs_review
---

# Finance Refund Processing SOP v3.2 (NEEDS REVIEW for 14-day window)

## Workflow WF-FIN-01: Refund approval and settlement

1. Verify purchase date is within the eligibility window. Current SOP text says **30 days** — update to **14 days** effective Oct 15, 2026.
2. Verify requester identity and original payment method.
3. If refund > $5,000, route to Finance approver (Priya Nair).
4. If customer = ACME Corp and purchase before 2027-01-01, apply **30-day** contract terms, not the general policy.
5. Settle via Stripe within 5 business days; log to the refund ledger.

## Controls

- Dual approval for refunds > $25,000.
- Monthly reconciliation against the Standard Customer Agreement terms.

*Synthetic demo data for Northstar Cloud (fictional).*
