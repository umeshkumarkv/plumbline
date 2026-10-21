package com.brokerdealer.orderservice.service;

import com.brokerdealer.orderservice.domain.Order;
import com.brokerdealer.orderservice.domain.OrderStatus;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.ZoneOffset;
import java.util.Date;                                          // expect: C1-legacy-date-time

@Service
public class BadService {
    @Autowired                                                   // expect: C4-field-injection
    private Object repo;
    private double orderPrice;                                   // expect: C1-money-floating-point
    private double feeAmount; // nosemgrep                       // expect: C1-money-floating-point

    public BigDecimal value(String p, long cents) {
        BigDecimal a = new BigDecimal(0.1);                      // expect: C1-bigdecimal-from-double, C1-bigdecimal-from-double-var
        BigDecimal b = new BigDecimal(Double.parseDouble(p));   // expect: C1-bigdecimal-from-double-var
        if (a.equals(b)) { throw new RuntimeException("x"); }    // expect: C1-bigdecimal-equals, C9-generic-runtime-exception
        LocalDate d = LocalDate.now(ZoneOffset.UTC);             // expect: DOM-TIME-utc-trading-day
        return a.setScale(2, RoundingMode.DOWN);                 // expect: DOM-MONEY-rounding-mode
    }

    public void sql(Object jdbc, String t) {
        String q = "SELECT * FROM client_schema.holdings WHERE t = '" + t + "'";  // expect: DOM-BOUNDARY-foreign-schema-sql
    }

    void transitionState(Order o, OrderStatus from, OrderStatus to, String by) { }

    @javax.inject.Inject                                         // expect: C4-field-injection
    public void setRepo(Object r) { }

    public void audit(String token) {
        log.debug("token " + token);                             // expect: C8-log-secret
    }

    public void move(Order o) {
        transitionState(o, OrderStatus.FILLED, OrderStatus.SENT_TO_EXECUTION, "x");  // expect: DOM-SM-illegal-transition
        o.setStatus(OrderStatus.EXPIRED);                        // expect: DOM-SM-direct-setstatus
    }
}
