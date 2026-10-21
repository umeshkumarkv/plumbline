package x.ledger.kafka;

public class PaymentConsumer {
    @KafkaListener(topics = "payment.settled", groupId = "ledger")
    public void on(Map<String, Object> payload) {
        String amount = (String) payload.get("amount");
        book(amount);
    }
}
