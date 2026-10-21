package x.pay.kafka;

import org.springframework.kafka.core.KafkaTemplate;
import x.pay.event.PaymentSettledEvent;

public class PaymentProducer {
    private static final String TOPIC = "payment.settled";
    private final KafkaTemplate<String, Object> kafkaTemplate;

    public void publish(PaymentSettledEvent event) {
        log.info("publishing payment {}", event);
        kafkaTemplate.send(TOPIC, "k", event);
    }
}
