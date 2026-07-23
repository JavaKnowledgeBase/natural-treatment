package app.rootwell.email;

import java.util.Map;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class EmailController {

    private final EmailService emailService;

    public EmailController(EmailService emailService) {
        this.emailService = emailService;
    }

    @GetMapping("/healthz")
    public Map<String, Object> healthz() {
        return Map.of("status", "ok", "mock_mode", emailService.isMockMode());
    }

    @PostMapping("/email/verify")
    public VerifyResponse verify(@RequestBody VerifyRequest req) {
        return emailService.requestVerification(req);
    }

    @PostMapping("/email/send")
    public SendResponse send(@RequestBody SendRequest req) {
        return emailService.send(req);
    }
}
