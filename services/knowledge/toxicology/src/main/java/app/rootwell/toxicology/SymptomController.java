package app.rootwell.toxicology;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class SymptomController {

    private final RefCacheService refCacheService;
    private final StringRedisTemplate redisTemplate;

    public SymptomController(RefCacheService refCacheService, StringRedisTemplate redisTemplate) {
        this.refCacheService = refCacheService;
        this.redisTemplate = redisTemplate;
    }

    @GetMapping("/healthz")
    public Map<String, Object> healthz() {
        String kbVersion = refCacheService.getKbVersion().orElse(null);
        return Map.of("status", "ok", "kb_version", kbVersion == null ? "" : kbVersion);
    }

    @GetMapping("/readyz")
    public ResponseEntity<Map<String, Object>> readyz() {
        try {
            redisTemplate.getConnectionFactory().getConnection().ping();
            return ResponseEntity.ok(Map.of("status", "ready"));
        } catch (Exception e) {
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                    .body(Map.of("status", "not_ready", "reason", "redis_unreachable"));
        }
    }

    @GetMapping("/symptoms")
    public Map<String, Object> listSymptoms(@RequestParam(required = false) String query) {
        List<Map<String, Object>> symptoms = refCacheService.listSymptoms();
        if (query != null && !query.isBlank()) {
            String needle = query.toLowerCase();
            symptoms = symptoms.stream()
                    .filter(s -> String.valueOf(s.get("name")).toLowerCase().contains(needle)
                            || String.valueOf(s.get("id")).toLowerCase().contains(needle))
                    .toList();
        }
        return Map.of("symptoms", symptoms);
    }

    @GetMapping("/symptoms/{symptomId}")
    public Map<String, Object> getSymptom(@PathVariable String symptomId) {
        return requireSymptom(symptomId);
    }

    @SuppressWarnings("unchecked")
    @GetMapping("/symptoms/{symptomId}/related")
    public Map<String, Object> getRelatedSymptoms(@PathVariable String symptomId) {
        Map<String, Object> symptom = requireSymptom(symptomId);
        List<Map<String, Object>> related = new ArrayList<>();
        Object relatedIdsObj = symptom.get("related_symptom_ids");
        if (relatedIdsObj instanceof List<?> relatedIds) {
            for (Object relatedId : relatedIds) {
                refCacheService.getSymptom(String.valueOf(relatedId)).ifPresent(related::add);
            }
        }
        return Map.of("related", related);
    }

    private Map<String, Object> requireSymptom(String symptomId) {
        Optional<Map<String, Object>> symptom = refCacheService.getSymptom(symptomId);
        if (symptom.isEmpty()) {
            throw new ResponseStatusException(
                    HttpStatus.NOT_FOUND, "Symptom '" + symptomId + "' not found in reference cache");
        }
        return symptom.get();
    }
}
