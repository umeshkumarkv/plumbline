package com.brokerdealer.orderservice.service;

import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.ZoneId;

@Service
@RequiredArgsConstructor
@Slf4j
public class CleanService {
    private static final ZoneId MARKET = ZoneId.of("America/New_York");

    public BigDecimal notional(BigDecimal price, Integer qty) {
        LocalDate tradeDate = LocalDate.now(MARKET);
        log.debug("notional tradeDate={}", tradeDate);
        BigDecimal v = price.multiply(BigDecimal.valueOf(qty)).setScale(2, RoundingMode.HALF_UP);
        return v.compareTo(BigDecimal.ZERO) > 0 ? v : BigDecimal.ZERO;
    }
}
