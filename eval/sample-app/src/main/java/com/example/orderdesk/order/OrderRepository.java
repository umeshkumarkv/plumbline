package com.example.orderdesk.order;

import java.sql.ResultSet;
import java.sql.SQLException;
import java.sql.Timestamp;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.support.GeneratedKeyHolder;
import org.springframework.stereotype.Repository;

@Repository
public class OrderRepository {
  private final JdbcTemplate jdbc;

  public OrderRepository(JdbcTemplate jdbc) {
    this.jdbc = jdbc;
  }

  public Optional<Order> findById(long id) {
    return jdbc.query("SELECT * FROM orders WHERE id = ?", this::map, id).stream().findFirst();
  }

  public List<Order> findByCustomer(long customerId, int limit) {
    return jdbc.query("SELECT * FROM orders WHERE customer_id = ? ORDER BY created_at DESC LIMIT ?",
        this::map, customerId, limit);
  }

  public List<OrderLine> findLines(long orderId) {
    return jdbc.query("SELECT sku, quantity, unit_price FROM order_line WHERE order_id = ? ORDER BY id",
        (rs, n) -> new OrderLine(rs.getString("sku"), rs.getInt("quantity"), rs.getBigDecimal("unit_price")),
        orderId);
  }

  public long insert(Order order, List<OrderLine> lines) {
    var keys = new GeneratedKeyHolder();
    jdbc.update(con -> {
      var ps = con.prepareStatement(
          "INSERT INTO orders(customer_id, status, total_amount, created_at) VALUES (?,?,?,?)", new String[] {"id"});
      ps.setLong(1, order.customerId());
      ps.setString(2, order.status().name());
      ps.setBigDecimal(3, order.totalAmount());
      ps.setTimestamp(4, Timestamp.from(order.createdAt()));
      return ps;
    }, keys);
    long id = keys.getKey().longValue();
    for (OrderLine line : lines) {
      jdbc.update("INSERT INTO order_line(order_id, sku, quantity, unit_price) VALUES (?,?,?,?)",
          id, line.sku(), line.quantity(), line.unitPrice());
    }
    return id;
  }

  /** Only OrderService may call this: it checks the transition first. */
  public void updateStatus(long id, OrderStatus from, OrderStatus to, String changedBy) {
    jdbc.update("UPDATE orders SET status = ? WHERE id = ? AND status = ?", to.name(), id, from.name());
    jdbc.update("INSERT INTO order_status_history(order_id, from_status, to_status, changed_by, changed_at) VALUES (?,?,?,?,?)",
        id, from.name(), to.name(), changedBy, Timestamp.from(Instant.now()));
  }

  private Order map(ResultSet rs, int n) throws SQLException {
    return new Order(rs.getLong("id"), rs.getLong("customer_id"), OrderStatus.valueOf(rs.getString("status")),
        rs.getBigDecimal("total_amount"), rs.getTimestamp("created_at").toInstant());
  }
}
