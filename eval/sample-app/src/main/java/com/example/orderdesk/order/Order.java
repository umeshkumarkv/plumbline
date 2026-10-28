package com.example.orderdesk.order;

import java.math.BigDecimal;
import java.time.Instant;

public record Order(Long id, Long customerId, OrderStatus status, BigDecimal totalAmount, Instant createdAt) {
  public Order withStatus(OrderStatus next) {
    return new Order(id, customerId, next, totalAmount, createdAt);
  }
}
