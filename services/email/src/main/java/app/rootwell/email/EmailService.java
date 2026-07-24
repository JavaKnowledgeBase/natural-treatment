package app.rootwell.email;

import java.security.SecureRandom;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;
import java.util.Objects;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;
import org.springframework.web.util.HtmlUtils;

/**
 * Port of services/email/main.py -- verification-gated export via Resend,
 * or mock-logs when RESEND_API_KEY is unset. Implements the anti-abuse flow
 * from application_design_v2 §6.3: a send always requires a prior
 * verification code to have been confirmed, and verification requests are
 * rate-limited per recipient address.
 */
@Service
public class EmailService {

    private static final long VERIFY_TTL_SECONDS = 10 * 60;
    private static final long RATE_LIMIT_WINDOW_SECONDS = 60 * 60;
    private static final long RATE_LIMIT_MAX_PER_WINDOW = 3;

    private final StringRedisTemplate redisTemplate;
    private final ResendClient resendClient;
    private final String fromAddress;
    private final boolean mockMode;
    private final SecureRandom random = new SecureRandom();

    public EmailService(
            StringRedisTemplate redisTemplate,
            ResendClient resendClient,
            @Value("${resend.api-key}") String apiKey,
            @Value("${resend.from-address}") String fromAddress) {
        this.redisTemplate = redisTemplate;
        this.resendClient = resendClient;
        this.fromAddress = fromAddress;
        this.mockMode = apiKey == null || apiKey.isBlank();
    }

    public boolean isMockMode() {
        return mockMode;
    }

    public VerifyResponse requestVerification(VerifyRequest req) {
        String rateLimitKey = "email:ratelimit:" + req.to().toLowerCase();
        Long count = redisTemplate.opsForValue().increment(rateLimitKey);
        if (count != null && count == 1) {
            redisTemplate.expire(rateLimitKey, java.time.Duration.ofSeconds(RATE_LIMIT_WINDOW_SECONDS));
        }
        if (count != null && count > RATE_LIMIT_MAX_PER_WINDOW) {
            throw new ResponseStatusException(
                    HttpStatus.TOO_MANY_REQUESTS,
                    "Too many verification requests for this address. Try again later.");
        }

        String token = generateToken();
        String code = generateCode();
        String verifyKey = verifyKey(token);
        Map<String, Object> fields = new HashMap<>();
        fields.put("to", req.to());
        fields.put("code", code);
        redisTemplate.opsForHash().putAll(verifyKey, fields);
        redisTemplate.expire(verifyKey, java.time.Duration.ofSeconds(VERIFY_TTL_SECONDS));

        if (mockMode) {
            System.out.printf(
                    "[email:mock] verification code for %s: %s (token=%s)%n", req.to(), code, token);
        } else {
            resendClient.send(Map.of(
                    "from", fromAddress,
                    "to", java.util.List.of(req.to()),
                    "subject", verificationSubject(req.language()),
                    "html", verificationHtml(req.language(), code),
                    "text", verificationText(req.language(), code)));
        }

        return new VerifyResponse(token, mockMode);
    }

    public SendResponse send(SendRequest req) {
        String verifyKey = verifyKey(req.verificationToken());
        Map<Object, Object> stored = redisTemplate.opsForHash().entries(verifyKey);
        if (stored.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Verification token expired or not found.");
        }
        if (!Objects.equals(stored.get("code"), req.code())) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Incorrect verification code.");
        }

        String toAddress = String.valueOf(stored.get("to"));
        redisTemplate.delete(verifyKey);

        if (mockMode) {
            System.out.printf("[email:mock] --- SENDING EMAIL to %s ---%n", toAddress);
            System.out.printf("[email:mock] subject: %s%n", req.subject());
            System.out.printf("[email:mock] text:%n%s%n", req.text());
            return new SendResponse("mock_sent", "mock-" + randomHex(8));
        }

        Map<String, Object> result = resendClient.send(Map.of(
                "from", fromAddress,
                "to", java.util.List.of(toAddress),
                "subject", req.subject(),
                "html", req.html(),
                "text", req.text()));
        Object messageId = result.get("id");
        return new SendResponse("sent", messageId == null ? null : String.valueOf(messageId));
    }

    /** Herb-sourcing inquiry, sent to our own inbox with the user's address as
     * reply-to -- no verification token needed since it never sends to an
     * address the caller supplies. All caller-supplied fields are HTML-escaped
     * before interpolation (see ReportingService.java for the same pattern,
     * fixed there after an earlier unescaped-interpolation finding). */
    public SendResponse contact(ContactRequest req) {
        String safeName = HtmlUtils.htmlEscape(blankToPlaceholder(req.name(), "(not provided)"));
        String safeEmail = HtmlUtils.htmlEscape(req.email());
        String safeHerb = HtmlUtils.htmlEscape(req.herbName());
        String safeMessage = HtmlUtils.htmlEscape(req.message());

        String subject = "Remedy sourcing inquiry: " + req.herbName();
        String text = "Herb: " + req.herbName() + "\nFrom: " + blankToPlaceholder(req.name(), "(not provided)")
                + " <" + req.email() + ">\n\n" + req.message();
        String html = "<div style=\"font-family:Arial,sans-serif;color:#1c2b22;\">"
                + "<p><strong>Herb:</strong> " + safeHerb + "</p>"
                + "<p><strong>From:</strong> " + safeName + " (" + safeEmail + ")</p>"
                + "<p><strong>Message:</strong><br/>" + safeMessage.replace("\n", "<br/>") + "</p>"
                + "</div>";

        if (mockMode) {
            System.out.printf("[email:mock] --- CONTACT INQUIRY --- herb=%s from=%s <%s>%n",
                    req.herbName(), req.name(), req.email());
            System.out.printf("[email:mock] message: %s%n", req.message());
            return new SendResponse("mock_sent", "mock-" + randomHex(8));
        }

        Map<String, Object> result = resendClient.send(Map.of(
                "from", fromAddress,
                "to", java.util.List.of(fromAddress),
                "reply_to", req.email(),
                "subject", subject,
                "html", html,
                "text", text));
        Object messageId = result.get("id");
        return new SendResponse("sent", messageId == null ? null : String.valueOf(messageId));
    }

    private String blankToPlaceholder(String value, String placeholder) {
        return (value == null || value.isBlank()) ? placeholder : value;
    }

    private String verificationSubject(String language) {
        return switch (normalizeLanguage(language)) {
            case "es" -> "Tu código de verificación";
            case "fr" -> "Votre code de vérification";
            case "zh" -> "您的验证码";
            case "hi" -> "आपका सत्यापन कोड";
            default -> "Your verification code";
        };
    }

    private String verificationText(String language, String code) {
        return switch (normalizeLanguage(language)) {
            case "es" -> "Tu código de verificación es " + code + ". Caduca en 10 minutos.";
            case "fr" -> "Votre code de vérification est " + code + ". Il expire dans 10 minutes.";
            case "zh" -> "您的验证码是 " + code + "。10 分钟后失效。";
            case "hi" -> "आपका सत्यापन कोड " + code + " है। यह 10 मिनट में समाप्त हो जाएगा।";
            default -> "Your verification code is " + code + ". It expires in 10 minutes.";
        };
    }

    private String verificationHtml(String language, String code) {
        String intro =
                switch (normalizeLanguage(language)) {
                    case "es" -> "Usa este código para confirmar tu correo:";
                    case "fr" -> "Utilisez ce code pour confirmer votre e-mail :";
                    case "zh" -> "请使用此验证码确认您的邮箱：";
                    case "hi" -> "अपना ईमेल पुष्ट करने के लिए इस कोड का उपयोग करें:";
                    default -> "Use this code to confirm your email:";
                };
        String expiry =
                switch (normalizeLanguage(language)) {
                    case "es" -> "Caduca en 10 minutos.";
                    case "fr" -> "Il expire dans 10 minutes.";
                    case "zh" -> "10 分钟后失效。";
                    case "hi" -> "यह 10 मिनट में समाप्त हो जाएगा।";
                    default -> "It expires in 10 minutes.";
                };
        return "<div style=\"font-family:Georgia,serif;color:#1c2b22;padding:16px;\">"
                + "<h2 style=\"color:#2f4f3d;margin-bottom:4px;\">Natural Remedy Research</h2>"
                + "<p style=\"font-family:Arial,sans-serif;color:#44544a;\">" + intro + "</p>"
                + "<p style=\"font-family:Arial,sans-serif;font-size:28px;font-weight:bold;"
                + "letter-spacing:4px;color:#2f4f3d;\">" + code + "</p>"
                + "<p style=\"font-family:Arial,sans-serif;color:#8a8a8a;font-size:13px;\">" + expiry + "</p>"
                + "</div>";
    }

    private String normalizeLanguage(String language) {
        if (language == null) return "en";
        return switch (language) {
            case "es", "fr", "zh", "hi" -> language;
            default -> "en";
        };
    }

    private String verifyKey(String token) {
        return "email:verify:" + token;
    }

    private String generateToken() {
        byte[] bytes = new byte[16];
        random.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    private String generateCode() {
        int value = random.nextInt(1_000_000);
        return String.format("%06d", value);
    }

    private String randomHex(int numBytes) {
        byte[] bytes = new byte[numBytes];
        random.nextBytes(bytes);
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) {
            sb.append(String.format("%02x", b));
        }
        return sb.toString();
    }
}
