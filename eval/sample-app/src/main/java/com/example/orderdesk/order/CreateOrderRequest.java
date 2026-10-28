package com.example.orderdesk.order;

import jakarta.validation.Valid;
import jakarta.validation.constraints.NotEmpty;
import jakarta.validation.constraints.NotNull;
import java.util.List;

public record CreateOrderRequest(@NotNull Long customerId, @NotEmpty List<@Valid OrderLine> lines) {}
