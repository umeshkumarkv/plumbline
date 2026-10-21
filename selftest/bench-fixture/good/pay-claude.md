# CLAUDE.md — pay-service

## 1. Service Purpose
Records payments and announces settlement.

## 2. Port
8091

## 3. Database Schema
pay_schema — table `payments`. Env: DB_PASSWORD.

## 4. Kafka Topics Produced
| Topic | Payload |
|---|---|
| payment.settled | PaymentSettledEvent |

## 5. Kafka Topics Consumed
None.

## 6. Redis Cache Keys Owned
None.

## 7. REST Endpoints Exposed
| Method | Path | Role |
|---|---|---|
| GET | /api/v1/payments/{id} | TRADER |

## 8. REST Endpoints Called (Downstream Dependencies)
None.

## 9. Entities Owned
None (payments table is written by a script in this fixture).

## 10. What This Service Must NEVER Do
- Call ledger-service synchronously.

## 11. Key Business Rules
- A settled payment is immutable.
