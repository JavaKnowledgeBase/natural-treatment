package app.rootwell.rules;

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

@Service
public class RefCacheService {

    private static final String RULE_PREFIX = "ref:rule:";
    private static final String KB_VERSION_KEY = "ref:kb_version";

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public RefCacheService(StringRedisTemplate redisTemplate) {
        this.redisTemplate = redisTemplate;
    }

    public List<Map<String, Object>> listRules() {
        List<Map<String, Object>> rules = new ArrayList<>();
        for (String key : scanKeys(RULE_PREFIX + "*")) {
            String raw = redisTemplate.opsForValue().get(key);
            if (raw != null) {
                rules.add(parse(raw));
            }
        }
        return rules;
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
