package com.example.orderdesk.order;

import com.example.orderdesk.security.CurrentUser;
import jakarta.validation.Valid;
import java.util.List;
import org.springframework.http.HttpStatus;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.security.access.prepost.PreAuthorize;
import org.springframework.web.bind.annotation.*;

@RestController
@RequestMapping("/api/orders")
public class OrderController {
  private final OrderService service;

  public OrderController(OrderService service) {
    this.service = service;
  }

  @GetMapping("/{id}")
  public Order get(@PathVariable long id) {
    Order order = service.get(id);
    checkOwnerOrAdmin(order);
    return order;
  }

  @GetMapping
  public List<Order> list(@RequestParam long customerId, @RequestParam(defaultValue = "20") int limit) {
    if (!CurrentUser.isAdmin() && !CurrentUser.id().equals(String.valueOf(customerId))) {
      throw new AccessDeniedException("Not your orders");
    }
    return service.listForCustomer(customerId, limit);
  }

  @PostMapping
  @ResponseStatus(HttpStatus.CREATED)
  public Order create(@Valid @RequestBody CreateOrderRequest request) {
    if (!CurrentUser.isAdmin() && !CurrentUser.id().equals(String.valueOf(request.customerId()))) {
      throw new AccessDeniedException("Not your account");
    }
    return service.create(request);
  }

  @PostMapping("/{id}/pay")
  @PreAuthorize("hasRole('ADMIN')")
  public Order pay(@PathVariable long id) {
    return service.changeStatus(id, OrderStatus.PAID, CurrentUser.id());
  }

  @PostMapping("/{id}/ship")
  @PreAuthorize("hasRole('ADMIN')")
  public Order ship(@PathVariable long id) {
    return service.changeStatus(id, OrderStatus.SHIPPED, CurrentUser.id());
  }

  @PostMapping("/{id}/cancel")
  public Order cancel(@PathVariable long id) {
    checkOwnerOrAdmin(service.get(id));
    return service.changeStatus(id, OrderStatus.CANCELLED, CurrentUser.id());
  }

  private void checkOwnerOrAdmin(Order order) {
    if (!CurrentUser.isAdmin() && !CurrentUser.id().equals(String.valueOf(order.customerId()))) {
      throw new AccessDeniedException("Not your order");
    }
  }
}
