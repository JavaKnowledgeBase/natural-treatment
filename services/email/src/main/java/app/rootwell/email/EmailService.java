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
                    "subject", "Your verification code",
                    "text", "Your verification code is " + code + ". It expires in 10 minutes."));
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
