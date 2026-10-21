# Design — SCRUM-42

#### 1. Service and Endpoint Design
```
ENDPOINT DESIGN
  Method  : GET
  Path    : /api/v1/payments/{id}/receipt
  Auth    : Bearer JWT — role: TRADER
  Service : pay-service port 8091
  Gateway : routed via api-gateway port 8080
  Headers : X-User-Id (gateway-forwarded), X-User-Role

RESPONSE (200)
  data:
    receiptNumber: string — payments.id
  meta:
    timestamp: ISO 8601 UTC string
    requestId: UUID string

ERROR RESPONSES
  404: PAYMENT_NOT_FOUND — no payment with that id
  400: VALIDATION_ERROR — id is not a UUID
```

#### 2. Database Schema Changes
```
SCHEMA CHANGES
  Service schema: pay_schema
  Migration file: V2__add_receipt_number.sql
  NEW COLUMNS: ALTER TABLE pay_schema.payments ADD COLUMN receipt_number VARCHAR(30);
```

#### 3. Domain Layer
```
ENTITY CHANGES
  No entity change
```

#### 4. Service Layer Logic
```
SERVICE LOGIC
  Class  : ReceiptService.java
  Method : receipt(UUID id): ReceiptResponse
```

#### 5. External Service Calls
```
EXTERNAL CALLS
  NONE
```

#### 6. Kafka Events
```
KAFKA
  NONE
```

#### 7. Redis Cache
```
REDIS
  NONE
```

#### 8. Test Strategy
```
TEST PLAN
  Unit — ServiceTest:
    - shouldReturnReceiptWhenSettled
    - shouldThrowNotFoundWhenUnknown
    - shouldThrowWhenNotSettled
  Unit — ControllerTest (@WebMvcTest):
    - returns 200 with envelope
    - returns 404 for unknown id
    - returns 400 for bad id
```

#### 9. OpenAPI Delta
```
OPENAPI DELTA
  ADD path: /api/v1/payments/{id}/receipt
```
