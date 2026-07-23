package app.rootwell.botanical;

import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
public class HerbController {

    private static final Logger log = LoggerFactory.getLogger(HerbController.class);

    private final RefCacheService refCacheService;
    private final StringRedisTemplate redisTemplate;

    public HerbController(RefCacheService refCacheService, StringRedisTemplate redisTemplate) {
        this.refCacheService = refCacheService;
        this.redisTemplate = redisTemplate;
    }

    /** Liveness-style: is this process able to respond at all. No downstream check. */
    @GetMapping("/healthz")
    public Map<String, Object> healthz() {
        String kbVersion = refCacheService.getKbVersion().orElse(null);
        return Map.of("status", "ok", "kb_version", kbVersion == null ? "" : kbVersion);
    }

    /**
     * Readiness-style: can this instance actually serve a request right now,
     * i.e. is Redis reachable. Kept separate from {@link #healthz()} on
     * purpose -- see docs/TECHNICAL_GUIDE.md's "liveness vs readiness"
     * section for why conflating the two is a real production mistake.
     */
    @GetMapping("/readyz")
    public ResponseEntity<Map<String, Object>> readyz() {
        try {
            redisTemplate.getConnectionFactory().getConnection().ping();
            return ResponseEntity.ok(Map.of("status", "ready"));
        } catch (Exception e) {
            log.warn("Readiness check failed: Redis unreachable", e);
            return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE)
                    .body(Map.of("status", "not_ready", "reason", "redis_unreachable"));
        }
    }

    @GetMapping("/herbs")
    public Map<String, Object> listHerbs(@RequestParam(required = false) String symptomId) {
        List<Map<String, Object>> herbs = refCacheService.listHerbs();
        if (symptomId != null && !symptomId.isBlank()) {
            herbs = herbs.stream()
                    .filter(h -> linkedSymptomsContain(h, symptomId))
                    .toList();
        }
        log.info("Listed {} herb(s), symptomId={}", herbs.size(), symptomId);
        return Map.of("herbs", herbs);
    }

    @GetMapping("/herbs/{herbId}")
    public Map<String, Object> getHerb(@PathVariable String herbId) {
        Optional<Map<String, Object>> herb = refCacheService.getHerb(herbId);
        if (herb.isEmpty()) {
            throw new ResponseStatusException(
                    HttpStatus.NOT_FOUND, "Herb '" + herbId + "' not found in reference cache");
        }
        return herb.get();
    }

    @SuppressWarnings("unchecked")
    private boolean linkedSymptomsContain(Map<String, Object> herb, String symptomId) {
        Object linked = herb.get("linked_symptoms");
        return linked instanceof List<?> list && list.contains(symptomId);
    }
}
