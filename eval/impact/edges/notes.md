# Ground-truth notes (oms)

- **Topics**: all literal (`@KafkaListener(topics="...")`) or `private static final String` constants; none from properties, none dynamic.
- **DLT topics** (`*.DLT`, marked uncertain) are implicit: every listener factory uses `DeadLetterPublishingRecoverer` (default `<topic>.DLT`). No code consumes them. auth/marketdata configure DLT but have no listeners.
- **Untyped consumers**: audit, client, order (`execution.completed`) take `Map<String,Object>`, so no payload class. risk (`RiskEvaluationRequest`) and order (`RiskEvaluationResultEvent`) convert maps via `ObjectMapper.convertValue`. These are listed as consumer classes.
- **Health checks**: `HealthAggregatorService` loops over the `app.health.services` map, building URLs at runtime as `baseUrl + "/actuator/health"`. The order-service self-entry (localhost:8082) is excluded.
- **execution → marketdata** calls `/api/v1/market/{symbol}`, which has no matching endpoint (it should be `/instrument/{symbol}`). The default base URL is localhost:8084, and compose overrides it.
- **api-gateway → notification**: the SSE proxy filter calls `/api/v1/notifications/stream` directly, on top of the gateway route.
- **Frontend**: axios base `/api/v1` goes to the gateway. The WebSocket `/ws/v1` goes directly to marketdata-service through nginx/vite.
- **No shared code**: there is only the parent POM. **No cross-schema DB access.** The Redis key `auth:blacklist:*` is written by auth-service and read by api-gateway (shared datastore, not in the schema).
- Path-variable names are arbitrary. Normalise `{...}` when scoring.
