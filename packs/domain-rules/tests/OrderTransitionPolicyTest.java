package com.brokerdealer.orderservice.service;

// Executable spec for R-ORDER-1 (CLAUDE.md §5). STATUS: written, NOT compiled here (Maven Central blocked).
// Copy to services/order-service/src/test/java/com/brokerdealer/orderservice/service/.
// Scope, honestly: this pins the documented policy (the §5 table) and the enum. It does NOT exercise
// OrderStateMachineService — production behaviour is guarded by gates/checks/domain_check.py (static) and
// should additionally be covered by service tests that drive each transition and assert the rejection of
// every pair outside LEGAL (next step once the build runs).

import com.brokerdealer.orderservice.domain.OrderStatus;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.EnumSource;

import java.util.EnumSet;
import java.util.Map;
import java.util.Set;

import static com.brokerdealer.orderservice.domain.OrderStatus.*;
import static org.assertj.core.api.Assertions.assertThat;

class OrderTransitionPolicyTest {

    /** CLAUDE.md §5 — valid transitions only (+ NEW→RISK_REJECTED pending §5 reconciliation). */
    static final Map<OrderStatus, Set<OrderStatus>> LEGAL = Map.of(
            NEW, EnumSet.of(VALIDATED, REJECTED, RISK_REJECTED),
            VALIDATED, EnumSet.of(RISK_CHECK_PASSED, RISK_REJECTED),
            RISK_CHECK_PASSED, EnumSet.of(ACCEPTED),
            ACCEPTED, EnumSet.of(SENT_TO_EXECUTION),
            SENT_TO_EXECUTION, EnumSet.of(PARTIALLY_FILLED, FILLED, REJECTED, EXPIRED),
            PARTIALLY_FILLED, EnumSet.of(PARTIALLY_FILLED, FILLED, EXPIRED));

    static final Set<OrderStatus> TERMINAL = EnumSet.of(RISK_REJECTED, FILLED, CANCELLED, REJECTED, EXPIRED);

    @ParameterizedTest
    @EnumSource(OrderStatus.class)
    void terminalStatesHaveNoOutgoingTransitions(OrderStatus s) {
        if (TERMINAL.contains(s)) {
            assertThat(LEGAL.getOrDefault(s, Set.of())).as("terminal %s", s).isEmpty();
        }
    }

    @Test
    void executionIsReachableOnlyThroughRiskCheckPassed() {
        // R-RISK-1: the only way into ACCEPTED (and hence execution) is from RISK_CHECK_PASSED
        LEGAL.forEach((from, tos) -> {
            if (tos.contains(ACCEPTED)) assertThat(from).isEqualTo(RISK_CHECK_PASSED);
        });
    }

    @Test
    void enumHasExactlyTheElevenDocumentedStates() {
        assertThat(EnumSet.allOf(OrderStatus.class)).hasSize(11);
    }
}
