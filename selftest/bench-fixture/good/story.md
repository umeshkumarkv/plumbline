Implement GET /api/v1/payments/{id}/receipt — receipt for a settled payment via API Gateway

#### User Story
As a trader
I want to fetch the receipt of a settled payment
So that I can keep proof of settlement

#### AI Context
- Service: pay-service, port 8091; skeleton exists
- Seed data: table payments (3 rows, status SETTLED)
- Call path: Frontend → API Gateway (8080) → pay-service (8091)
- Response fields and their source columns: receiptNumber from payments.id, amount from payments.amount
- External calls: none

#### Acceptance Criteria
- [ ] GET http://localhost:8080/api/v1/payments/{id}/receipt returns 200 with data.receiptNumber=R-{id}
- [ ] GET http://localhost:8080/api/v1/payments/{unknown}/receipt returns 404 with error code PAYMENT_NOT_FOUND
- [ ] GET http://localhost:8080/api/v1/payments/not-a-uuid/receipt returns 400 with error code VALIDATION_ERROR

#### Out of Scope
- Refunds (CLAUDE.md Section 18)

#### Tech Constraints
```
- Service: pay-service (port 8091) — exposed via API Gateway port 8080
- Read CLAUDE.md and services/pay-service/CLAUDE.md before writing any code
- Follow openapi.yaml exactly for response shape
- Branch: ai/SCRUM-42-payment-receipt from develop
- PR target: develop
- Blocked by: None
```

#### Story Points
Estimate: 3
