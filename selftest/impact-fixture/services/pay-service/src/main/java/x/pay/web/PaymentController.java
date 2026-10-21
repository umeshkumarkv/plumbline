package x.pay.web;

@RestController
@RequestMapping("/api/v1/payments")
public class PaymentController {
    @GetMapping("/{id}")
    public ResponseEntity<PaymentView> get(@PathVariable String id) {
        PaymentView view = service.find(id);
        return ResponseEntity.ok(view);
    }
}
