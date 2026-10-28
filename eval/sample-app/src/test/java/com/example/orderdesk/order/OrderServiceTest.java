package com.example.orderdesk.order;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.Mockito.*;

import com.example.orderdesk.common.InvalidStateException;
import com.example.orderdesk.common.NotFoundException;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class OrderServiceTest {
  private OrderRepository repository;
  private OrderService service;

  @BeforeEach
  void setUp() {
    repository = mock(OrderRepository.class);
    service = new OrderService(repository, 100);
  }

  private Order order(OrderStatus status) {
    return new Order(7L, 3L, status, new BigDecimal("25.00"), Instant.parse("2026-01-01T10:00:00Z"));
  }

  @Test
  void createSumsLineTotals() {
    when(repository.insert(any(), any())).thenReturn(7L);
    when(repository.findById(7L)).thenReturn(Optional.of(order(OrderStatus.NEW)));
    service.create(new CreateOrderRequest(3L, List.of(
        new OrderLine("A-1", 2, new BigDecimal("10.00")), new OrderLine("B-2", 1, new BigDecimal("5.00")))));
    verify(repository).insert(argThat(o -> o.totalAmount().compareTo(new BigDecimal("25.00")) == 0), any());
  }

  @Test
  void getUnknownOrderThrowsNotFound() {
    when(repository.findById(99L)).thenReturn(Optional.empty());
    assertThatThrownBy(() -> service.get(99L)).isInstanceOf(NotFoundException.class);
  }

  @Test
  void listCapsLimitAtMaximum() {
    service.listForCustomer(3L, 5000);
    verify(repository).findByCustomer(3L, 100);
  }

  @Test
  void listRejectsLimitBelowOne() {
    assertThatThrownBy(() -> service.listForCustomer(3L, 0)).isInstanceOf(IllegalArgumentException.class);
  }

  @Test
  void cancelPaidOrderIsAllowed() {
    when(repository.findById(7L)).thenReturn(Optional.of(order(OrderStatus.PAID)));
    assertThat(service.changeStatus(7L, OrderStatus.CANCELLED, "admin-1").status()).isEqualTo(OrderStatus.CANCELLED);
    verify(repository).updateStatus(7L, OrderStatus.PAID, OrderStatus.CANCELLED, "admin-1");
  }

  @Test
  void cancelShippedOrderIsRefused() {
    when(repository.findById(7L)).thenReturn(Optional.of(order(OrderStatus.SHIPPED)));
    assertThatThrownBy(() -> service.changeStatus(7L, OrderStatus.CANCELLED, "admin-1"))
        .isInstanceOf(InvalidStateException.class);
    verify(repository, never()).updateStatus(anyLong(), any(), any(), any());
  }
}
