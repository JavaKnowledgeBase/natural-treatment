package app.rootwell.email;

import java.time.Duration;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.HttpStatus;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.HttpServerErrorException;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;
import org.springframework.web.server.ResponseStatusException;

/**
 * Thin Resend wrapper with retry/backoff -- this is the single highest-value
 * place in the whole system to retry a transient failure (see
 * docs/API_REFERENCE.md §2b): the send call fires immediately before the
 * session's Tier 2 data is purged, so losing it to one transient outage is
 * the worst-case failure mode in the app.
 */
@Component
public class ResendClient {

    private static final Logger log = LoggerFactory.getLogger(ResendClient.class);
    private static final int MAX_ATTEMPTS = 3;
    private static final double BACKOFF_BASE_SECONDS = 0.5;

    private final RestClient restClient;
    private final String apiKey;

    public ResendClient(@Value("${resend.api-key}") String apiKey) {
        this.apiKey = apiKey;
        var factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(10));
        factory.setReadTimeout(Duration.ofSeconds(10));
        this.restClient = RestClient.builder()
                .baseUrl("https://api.resend.com")
                .requestFactory(factory)
                .defaultHeader("Authorization", "Bearer " + apiKey)
                .build();
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> send(Map<String, Object> payload) {
        RuntimeException lastError = null;
        for (int attempt = 0; attempt < MAX_ATTEMPTS; attempt++) {
            try {
                Map<String, Object> body = restClient.post()
                        .uri("/emails")
                        .body(payload)
                        .retrieve()
                        .body(Map.class);
                return body != null ? body : Map.of();
            } catch (HttpServerErrorException | ResourceAccessException e) {
                lastError = e;
            } catch (HttpStatusCodeException e) {
                if (e.getStatusCode().value() == 429) {
                    lastError = e;
                } else {
                    throw e; // 4xx other than rate-limit is a real request bug, not worth retrying
                }
            }
            if (attempt < MAX_ATTEMPTS - 1) {
                double delaySeconds = BACKOFF_BASE_SECONDS * Math.pow(2, attempt);
                log.warn("Resend call failed (attempt {}/{}), retrying in {}s: {}",
                        attempt + 1, MAX_ATTEMPTS, delaySeconds, lastError.getMessage());
                sleep(delaySeconds);
            }
        }
        throw new ResponseStatusException(
                HttpStatus.BAD_GATEWAY,
                "Email provider unreachable after " + MAX_ATTEMPTS + " attempts",
                lastError);
    }

    private void sleep(double seconds) {
        try {
            Thread.sleep((long) (seconds * 1000));
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }
    }
}
