package app.rootwell.botanical;

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
 * shared/shared/cache.py needed by this service -- plain Redis strings at
 * {@code ref:<kind>:<id>}, JSON-encoded. Herb records are read as
 * {@code Map<String,Object>} rather than a fixed POJO: this service only
 * ever filters/passes them through, so a strict schema would risk silently
 * dropping fields the Python seed loader adds later.
 *
 * <p>Uses cursor-based SCAN (not KEYS) to enumerate keys, matching the
 * Python side's use of {@code scan_iter} over a blocking KEYS call --
 * KEYS walks the whole keyspace in one shot and can stall Redis on a large
 * dataset; SCAN pages through it incrementally instead.
 */
@Service
public class RefCacheService {

    private static final String HERB_PREFIX = "ref:herb:";
    private static final String HERB_DETAIL_PREFIX = "ref:herb_detail:";
    private static final String KB_VERSION_KEY = "ref:kb_version";

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public RefCacheService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public Optional<Map<String, Object>> getHerb(String herbId) {
        String raw = redisTemplate.opsForValue().get(HERB_PREFIX + herbId);
        if (raw == null) {
            return Optional.empty();
        }
        return Optional.of(parse(raw));
    }

    public List<Map<String, Object>> listHerbs() {
        List<Map<String, Object>> herbs = new ArrayList<>();
        for (String key : scanKeys(HERB_PREFIX + "*")) {
            String raw = redisTemplate.opsForValue().get(key);
            if (raw != null) {
                herbs.add(parse(raw));
            }
        }
        return herbs;
    }

    /** Raw record: {@code {id, en: {...}, hi: {...}?, ...}} -- one key per
     * language actually curated for this herb, missing keys mean "not yet
     * translated" (fallback to English happens in the controller, not here,
     * so this stays a thin, schema-agnostic read like {@link #getHerb}). */
    public Optional<Map<String, Object>> getHerbDetail(String herbId) {
        String raw = redisTemplate.opsForValue().get(HERB_DETAIL_PREFIX + herbId);
        if (raw == null) {
            return Optional.empty();
        }
        return Optional.of(parse(raw));
    }

    public Optional<String> getKbVersion() {
        return Optional.ofNullable(redisTemplate.opsForValue().get(KB_VERSION_KEY));
    }

    @SuppressWarnings("unchecked")
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
