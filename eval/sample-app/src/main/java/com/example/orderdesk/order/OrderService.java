package com.example.orderdesk.order;

import com.example.orderdesk.common.InvalidStateException;
import com.example.orderdesk.common.NotFoundException;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OrderService {
  private static final Logger log = LoggerFactory.getLogger(OrderService.class);
  private final OrderRepository repository;
  private final int maxLimit;

  public OrderService(OrderRepository repository, @Value("${orderdesk.list.max-limit}") int maxLimit) {
    this.repository = repository;
    this.maxLimit = maxLimit;
  }

  public Order get(long id) {
    return repository.findById(id).orElseThrow(() -> new NotFoundException("Order " + id + " not found"));
  }

  public List<Order> listForCustomer(long customerId, int limit) {
    if (limit < 1) throw new IllegalArgumentException("limit must be at least 1");
    return repository.findByCustomer(customerId, Math.min(limit, maxLimit));
  }

  @Transactional
  public Order create(CreateOrderRequest request) {
    BigDecimal total = request.lines().stream().map(OrderLine::lineTotal).reduce(BigDecimal.ZERO, BigDecimal::add);
    Order order = new Order(null, request.customerId(), OrderStatus.NEW, total, Instant.now());
    long id = repository.insert(order, request.lines());
    log.info("Order created: orderId={} customerId={} lines={}", id, request.customerId(), request.lines().size());
    return get(id);
  }

  @Transactional
  public Order changeStatus(long id, OrderStatus target, String changedBy) {
    Order order = get(id);
    if (!order.status().canMoveTo(target)) {
      throw new InvalidStateException("Order " + id + " cannot move from " + order.status() + " to " + target);
    }
    repository.updateStatus(id, order.status(), target, changedBy);
    log.info("Order status changed: orderId={} {} -> {}", id, order.status(), target);
    return order.withStatus(target);
  }
}
