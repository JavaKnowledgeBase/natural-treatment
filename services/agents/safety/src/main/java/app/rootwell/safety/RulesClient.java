package app.rootwell.safety;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class RulesClient {

    private final RestClient restClient;

    public RulesClient(@Value("${rules-service.url}") String rulesServiceUrl) {
        this.restClient = RestClient.builder()
                .baseUrl(rulesServiceUrl)
                .requestFactory(clientRequestFactory())
                .build();
    }

    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> listAllRules() {
        Map<String, Object> body = restClient.get()
                .uri("/rules")
                .retrieve()
                .body(Map.class);
        return (List<Map<String, Object>>) body.get("rules");
    }

    private static org.springframework.http.client.ClientHttpRequestFactory clientRequestFactory() {
        var factory = new org.springframework.http.client.SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(10));
        factory.setReadTimeout(Duration.ofSeconds(10));
        return factory;
    }
}
