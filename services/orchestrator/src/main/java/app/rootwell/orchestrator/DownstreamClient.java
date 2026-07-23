package app.rootwell.orchestrator;

import java.time.Duration;
import java.util.Map;
import org.springframework.http.HttpStatus;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.web.client.RestClient;
import org.springframework.web.client.RestClientResponseException;
import org.springframework.web.server.ResponseStatusException;

/**
 * Thin wrapper around RestClient for calling one downstream agent service.
 *
 * <p>Fixes a real bug found while migrating: the original Python
 * orchestrator's {@code _post}/{@code _get} helpers called
 * {@code resp.raise_for_status()} with no handling, so <em>any</em>
 * downstream error status (a 429 from the email service's rate limiter, a
 * 400 from a bad request shape, anything) became an unhandled exception and
 * surfaced as a generic 500 all the way to the gateway -- losing the real
 * status code the caller needed to distinguish "rate limited" from "bad
 * request" from "server error." This client instead catches the downstream
 * error and re-throws it as a {@link ResponseStatusException} carrying the
 * *same* status code and body, matching the gateway's own "propagate the
 * real status" principle (see docs/API_REFERENCE.md §1a).
 */
public class DownstreamClient {

    private final RestClient restClient;

    public DownstreamClient(String baseUrl, Duration timeout) {
        var factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(timeout);
        factory.setReadTimeout(timeout);
        this.restClient = RestClient.builder().baseUrl(baseUrl).requestFactory(factory).build();
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> get(String path) {
        try {
            Map<String, Object> body = restClient.get().uri(path).retrieve().body(Map.class);
            return body != null ? body : Map.of();
        } catch (RestClientResponseException e) {
            throw propagate(e);
        }
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> post(String path, Object requestBody) {
        try {
            Map<String, Object> body = restClient.post().uri(path).body(requestBody).retrieve().body(Map.class);
            return body != null ? body : Map.of();
        } catch (RestClientResponseException e) {
            throw propagate(e);
        }
    }

    public Map<String, Object> post(String path) {
        return post(path, Map.of());
    }

    private ResponseStatusException propagate(RestClientResponseException e) {
        HttpStatus status = HttpStatus.resolve(e.getStatusCode().value());
        return new ResponseStatusException(
                status != null ? status : HttpStatus.BAD_GATEWAY,
                e.getResponseBodyAsString(),
                e);
    }
}
