package x.ledger.client;

public class PayClient {
    @Value("${pay.url:http://pay-service:8091}")
    private String base;

    public PayStatus status(String id) {
        return restTemplate.getForObject(base + "/api/v1/payments/" + id, PayStatus.class);
    }
}
