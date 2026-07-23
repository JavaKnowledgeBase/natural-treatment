package app.rootwell.retrieval;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class BotanicalClient {

    private final RestClient restClient;

    public BotanicalClient(@Value("${botanical-service.url}") String botanicalServiceUrl) {
        var factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(10));
        factory.setReadTimeout(Duration.ofSeconds(10));
        this.restClient = RestClient.builder().baseUrl(botanicalServiceUrl).requestFactory(factory).build();
    }

    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> herbsForSymptom(String symptomId) {
        Map<String, Object> body = restClient.get()
                .uri(uriBuilder -> uriBuilder.path("/herbs").queryParam("symptom_id", symptomId).build())
                .retrieve()
                .body(Map.class);
        return (List<Map<String, Object>>) body.get("herbs");
    }
}
