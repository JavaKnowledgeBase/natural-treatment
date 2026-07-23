package app.rootwell.compound;

import java.util.Arrays;
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
public class CompoundController {

    private final RefCacheService refCacheService;
    private final StringRedisTemplate redisTemplate;

    public CompoundController(RefCacheService refCacheService, StringRedisTemplate redisTemplate) {
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

    @GetMapping("/compounds")
    public Map<String, Object> listCompounds(@RequestParam(required = false) String ids) {
        if (ids != null && !ids.isBlank()) {
            List<String> wanted = Arrays.stream(ids.split(",")).map(String::trim).filter(s -> !s.isEmpty()).toList();
            return Map.of("compounds", refCacheService.listCompoundsByIds(wanted));
        }
        return Map.of("compounds", refCacheService.listCompounds());
    }

    @GetMapping("/compounds/{compoundId}")
    public Map<String, Object> getCompound(@PathVariable String compoundId) {
        Optional<Map<String, Object>> compound = refCacheService.getCompound(compoundId);
        if (compound.isEmpty()) {
            throw new ResponseStatusException(
                    HttpStatus.NOT_FOUND, "Compound '" + compoundId + "' not found in reference cache");
        }
        return compound.get();
    }
}
