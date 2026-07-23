package app.rootwell.rules;

import java.util.List;
import java.util.Map;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class RulesController {

    private final RefCacheService refCacheService;
    private final StringRedisTemplate redisTemplate;

    public RulesController(RefCacheService refCacheService, StringRedisTemplate redisTemplate) {
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

    @GetMapping("/rules")
    public Map<String, Object> listRules(@RequestParam(required = false) String herbId) {
        List<Map<String, Object>> rules = refCacheService.listRules();
        if (herbId != null && !herbId.isBlank()) {
            rules = rules.stream().filter(r -> herbId.equals(String.valueOf(r.get("herb_id")))).toList();
        }
        return Map.of("rules", rules);
    }
}
