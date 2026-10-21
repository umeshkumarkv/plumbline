package com.brokerdealer.orderservice.domain;

import jakarta.persistence.*;
import lombok.*;
import java.math.BigDecimal;
import java.util.UUID;

@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
@Entity
public class Order {
    @Id
    private UUID id;

    @Enumerated(EnumType.STRING)
    private OrderStatus status;

    private OrderStatus previousStatus;                        // expect: C1-enum-not-string

    @Column(precision = 19, scale = 4)
    private BigDecimal limitPrice;
}
