# PRD — Payment receipts

#### 1. Problem Statement
PROBLEM
  Who has this problem: users
  What they cannot do today: download a receipt for a settled payment from the platform
  Business impact if unsolved: compliance gap — traders must request receipts from operations by email

#### 2. Proposed Solution
SOLUTION SUMMARY
  What the system will do: pay-service exposes a receipt for every settled payment.
  User-facing change: a Receipt button on the payment detail page.
  API / data change: new endpoint GET /api/v1/payments/{id}/receipt

#### 3. Success Criteria
SUCCESS CRITERIA
  - GET /api/v1/payments/{id}/receipt returns 200 with receiptNumber for a settled payment

#### 4. Out of Scope
OUT OF SCOPE (this PRD)
  - Refunds (CLAUDE.md Section 18)

#### 5. Dependencies
DEPENDENCIES
  - Blocked by: None

#### 6. Backlog Prioritization
BACKLOG ORDER (recommended)
  P1 — Must have for MVP: receipt endpoint (13 pts), receipt button (8 pts)
  P2 — Should have: refunds (8 pts)
  P3 — Nice to have: email the receipt (2 pts)
  OUT OF SCOPE: refunds

Open question: TBD
