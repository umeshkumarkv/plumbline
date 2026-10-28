# order-desk — reference

<!-- plumbline:begin reference -->
Last updated: VERIFIED_COMMIT (2026-10-28, /pl-onboard, claude-reference v1)

## API
- `GET /api/orders/{id}` — owner or ADMIN.
- `GET /api/orders?customerId=&limit=` — owner or ADMIN; `limit` 1..`orderdesk.list.max-limit` (100), default 20.
- `POST /api/orders` — owner or ADMIN; 201 with the order.
- `POST /api/orders/{id}/pay`, `POST /api/orders/{id}/ship` — ADMIN only (`@PreAuthorize("hasRole('ADMIN')")`).
- `POST /api/orders/{id}/cancel` — owner or ADMIN.
- Errors: always `ApiError {code, message}` from `GlobalExceptionHandler`: 404 `NOT_FOUND`, 409 `INVALID_STATE`,
  400 `VALIDATION_FAILED`, 403 `FORBIDDEN`.

## Data
`customer(id, name, email unique)`, `orders(id, customer_id, status, total_amount DECIMAL(12,2), created_at)`,
`order_line(id, order_id, sku, quantity, unit_price DECIMAL(12,2))`, `order_status_history(order_id, from_status,
to_status, changed_by, changed_at)`. Schema lives in `src/main/resources/schema.sql`.

## Integrations
None besides the gateway headers.

## Configuration
`orderdesk.list.max-limit` (100). No secrets in this service.

## Tech debt
None found (sample).

## Open questions
None.
<!-- plumbline:end reference -->
