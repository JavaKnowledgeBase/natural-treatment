package app.rootwell.compound;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.core.Cursor;
import org.springframework.data.redis.core.ScanOptions;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

/**
 * Java port of the Tier 1 (shared reference cache) subset of
 * shared/shared/cache.py needed by this service. See knowledge-botanical's
 * RefCacheService for the full rationale (generic Map over a strict POJO,
 * cursor-based SCAN over KEYS).
 */
@Service
public class RefCacheService {

    private static final String COMPOUND_PREFIX = "ref:compound:";
    private static final String KB_VERSION_KEY = "ref:kb_version";

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public RefCacheService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public Optional<Map<String, Object>> getCompound(String compoundId) {
        String raw = redisTemplate.opsForValue().get(COMPOUND_PREFIX + compoundId);
        if (raw == null) {
            return Optional.empty();
        }
        return Optional.of(parse(raw));
    }

    public List<Map<String, Object>> listCompounds() {
        List<Map<String, Object>> compounds = new ArrayList<>();
        for (String key : scanKeys(COMPOUND_PREFIX + "*")) {
            String raw = redisTemplate.opsForValue().get(key);
            if (raw != null) {
                compounds.add(parse(raw));
            }
        }
        return compounds;
    }

    public List<Map<String, Object>> listCompoundsByIds(List<String> ids) {
        List<Map<String, Object>> compounds = new ArrayList<>();
        for (String id : ids) {
            getCompound(id).ifPresent(compounds::add);
        }
        return compounds;
    }

    public Optional<String> getKbVersion() {
        return Optional.ofNullable(redisTemplate.opsForValue().get(KB_VERSION_KEY));
    }

    private Map<String, Object> parse(String raw) {
        try {
            return objectMapper.readValue(raw, new TypeReference<Map<String, Object>>() {});
        } catch (JsonProcessingException e) {
            throw new IllegalStateException("Malformed JSON in reference cache", e);
        }
    }

    private List<String> scanKeys(String pattern) {
        List<String> keys = new ArrayList<>();
        try (RedisConnection connection = redisTemplate.getConnectionFactory().getConnection()) {
            try (Cursor<byte[]> cursor =
                    connection.keyCommands()
                            .scan(ScanOptions.scanOptions().match(pattern).count(100).build())) {
                while (cursor.hasNext()) {
                    keys.add(new String(cursor.next(), StandardCharsets.UTF_8));
                }
            }
        }
        return keys;
    }
}
