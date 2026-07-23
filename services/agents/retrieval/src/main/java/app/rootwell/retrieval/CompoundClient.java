package app.rootwell.retrieval;

import java.time.Duration;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestClient;

@Component
public class CompoundClient {

    private final RestClient restClient;

    public CompoundClient(@Value("${compound-service.url}") String compoundServiceUrl) {
        var factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofSeconds(10));
        factory.setReadTimeout(Duration.ofSeconds(10));
        this.restClient = RestClient.builder().baseUrl(compoundServiceUrl).requestFactory(factory).build();
    }

    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> compoundsByIds(List<String> ids) {
        Map<String, Object> body = restClient.get()
                .uri(uriBuilder -> uriBuilder.path("/compounds").queryParam("ids", String.join(",", ids)).build())
                .retrieve()
                .body(Map.class);
        return (List<Map<String, Object>>) body.get("compounds");
    }
}
