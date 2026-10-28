package com.example.orderdesk.order;

import java.util.Map;
import java.util.Set;

public enum OrderStatus {
  NEW, PAID, SHIPPED, CANCELLED;

  private static final Map<OrderStatus, Set<OrderStatus>> ALLOWED = Map.of(
      NEW, Set.of(PAID, CANCELLED),
      PAID, Set.of(SHIPPED, CANCELLED),
      SHIPPED, Set.of(),
      CANCELLED, Set.of());

  public boolean canMoveTo(OrderStatus target) {
    return target != null && ALLOWED.get(this).contains(target);
  }
}
