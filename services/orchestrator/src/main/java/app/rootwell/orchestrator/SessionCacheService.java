package app.rootwell.orchestrator;

import com.fasterxml.jackson.databind.ObjectMapper;
import java.nio.charset.StandardCharsets;
import java.time.Duration;
import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Range;
import org.springframework.data.redis.connection.RedisConnection;
import org.springframework.data.redis.connection.stream.MapRecord;
import org.springframework.data.redis.connection.stream.StreamRecords;
import org.springframework.data.redis.core.Cursor;
import org.springframework.data.redis.core.ScanOptions;
import org.springframework.data.redis.core.StringRedisTemplate;
import org.springframework.stereotype.Service;

/**
 * Java port of the Tier 2 (per-session) subset of shared/shared/cache.py.
 * Every key lives under {@code session:{sid}:*}, TTL'd to
 * SESSION_IDLE_TIMEOUT_SECONDS and slid forward on every write ({@link #touch}),
 * hard-deleted via UNLINK on purge -- see docs/ARCHITECTURE.md §3. This is
 * the only Java service in the system that ever writes Tier 2 data; every
 * knowledge/agent service that stayed or moved to Java only ever reads
 * Tier 1 reference data.
 */
@Service
public class SessionCacheService {

    private final StringRedisTemplate redisTemplate;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final long sessionTtlSeconds;

    public SessionCacheService(
            StringRedisTemplate redisTemplate,
            @Value("${session.idle-timeout-seconds}") long sessionTtlSeconds) {
        this.redisTemplate = redisTemplate;
        this.sessionTtlSeconds = sessionTtlSeconds;
    }

    private String prefix(String sid) {
        return "session:" + sid + ":";
    }

    private void touch(String sid) {
        String prefix = prefix(sid);
        for (String key : scanKeys(prefix + "*")) {
            redisTemplate.expire(key, Duration.ofSeconds(sessionTtlSeconds));
        }
    }

    public void createSession(String sid, String language) {
        String now = formatEpochSeconds(nowEpochSeconds());
        Map<String, String> meta = new HashMap<>();
        meta.put("session_id", sid);
        meta.put("current_step", "greeting");
        meta.put("language", language);
        meta.put("created_at", now);
        meta.put("last_active_at", now);
        redisTemplate.opsForHash().putAll(prefix(sid) + "meta", meta);
        redisTemplate.opsForHash().put(prefix(sid) + "profile", "_placeholder", "1");
        touch(sid);
    }

    public Map<String, Object> getMeta(String sid) {
        Map<Object, Object> raw = redisTemplate.opsForHash().entries(prefix(sid) + "meta");
        if (raw.isEmpty()) {
            return null;
        }
        Map<String, Object> meta = new HashMap<>();
        raw.forEach((k, v) -> meta.put(String.valueOf(k), v));
        return meta;
    }

    public void setStep(String sid, String step) {
        Map<String, String> fields = Map.of(
                "current_step", step,
                "last_active_at", formatEpochSeconds(nowEpochSeconds()));
        redisTemplate.opsForHash().putAll(prefix(sid) + "meta", fields);
        touch(sid);
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> getProfile(String sid) {
        Map<Object, Object> raw = redisTemplate.opsForHash().entries(prefix(sid) + "profile");
        Map<String, Object> profile = new HashMap<>();
        raw.forEach((k, v) -> profile.put(String.valueOf(k), v));
        profile.remove("_placeholder");
        for (String field : List.of("medications", "allergies", "chronic_conditions")) {
            if (profile.containsKey(field)) {
                profile.put(field, parseJson(String.valueOf(profile.get(field)), List.class));
            }
        }
        return profile;
    }

    public void updateProfile(String sid, Map<String, Object> fields) {
        if (fields == null || fields.isEmpty()) {
            return;
        }
        Map<String, String> encoded = new HashMap<>();
        fields.forEach((key, value) -> encoded.put(key, value instanceof List ? toJson(value) : String.valueOf(value)));
        redisTemplate.opsForHash().putAll(prefix(sid) + "profile", encoded);
        touch(sid);
    }

    public void appendChatMessage(String sid, String role, String text) {
        Map<String, String> fields = Map.of("role", role, "text", text, "ts", formatEpochSeconds(nowEpochSeconds()));
        redisTemplate.opsForStream().add(StreamRecords.newRecord().in(prefix(sid) + "chat").ofMap(fields));
        touch(sid);
    }

    public List<Map<String, Object>> getChatHistory(String sid) {
        List<MapRecord<String, Object, Object>> records =
                redisTemplate.opsForStream().range(prefix(sid) + "chat", Range.unbounded());
        List<Map<String, Object>> history = new ArrayList<>();
        for (MapRecord<String, Object, Object> record : records) {
            Map<Object, Object> value = record.getValue();
            Map<String, Object> entry = new HashMap<>();
            entry.put("role", String.valueOf(value.get("role")));
            entry.put("text", String.valueOf(value.get("text")));
            entry.put("ts", Double.parseDouble(String.valueOf(value.get("ts"))));
            history.add(entry);
        }
        return history;
    }

    public void addCachedItem(String sid, String cacheName, String itemId, Map<String, Object> value) {
        redisTemplate.opsForHash().put(prefix(sid) + cacheName, itemId, toJson(value));
        touch(sid);
    }

    public void removeCachedItem(String sid, String cacheName, String itemId) {
        redisTemplate.opsForHash().delete(prefix(sid) + cacheName, itemId);
    }

    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> listCachedItems(String sid, String cacheName) {
        Map<Object, Object> raw = redisTemplate.opsForHash().entries(prefix(sid) + cacheName);
        List<Map<String, Object>> items = new ArrayList<>();
        for (Object value : raw.values()) {
            items.add(parseJson(String.valueOf(value), Map.class));
        }
        return items;
    }

    public void pushListItem(String sid, String listName, Map<String, Object> value) {
        redisTemplate.opsForList().rightPush(prefix(sid) + listName, toJson(value));
        touch(sid);
    }

    @SuppressWarnings("unchecked")
    public List<Map<String, Object>> getList(String sid, String listName) {
        List<String> raw = redisTemplate.opsForList().range(prefix(sid) + listName, 0, -1);
        List<Map<String, Object>> items = new ArrayList<>();
        if (raw != null) {
            for (String value : raw) {
                items.add(parseJson(value, Map.class));
            }
        }
        return items;
    }

    public void clearList(String sid, String listName) {
        redisTemplate.delete(prefix(sid) + listName);
    }

    public int purgeSession(String sid) {
        List<String> keys = scanKeys(prefix(sid) + "*");
        if (keys.isEmpty()) {
            return 0;
        }
        try (RedisConnection connection = redisTemplate.getConnectionFactory().getConnection()) {
            byte[][] keyBytes = keys.stream().map(k -> k.getBytes(StandardCharsets.UTF_8)).toArray(byte[][]::new);
            connection.keyCommands().unlink(keyBytes);
        }
        return keys.size();
    }

    public boolean sessionExists(String sid) {
        return Boolean.TRUE.equals(redisTemplate.hasKey(prefix(sid) + "meta"));
    }

    private double nowEpochSeconds() {
        return Instant.now().toEpochMilli() / 1000.0;
    }

    /** Java's Double.toString switches to scientific notation above 10^7 --
     * Python's str(time.time()) never does for this range, so a plain
     * String.valueOf(double) here would silently change the stored format. */
    private String formatEpochSeconds(double value) {
        return new java.math.BigDecimal(value).setScale(6, java.math.RoundingMode.HALF_UP).stripTrailingZeros().toPlainString();
    }

    private String toJson(Object value) {
        try {
            return objectMapper.writeValueAsString(value);
        } catch (Exception e) {
            throw new IllegalStateException("Failed to serialize value for Tier 2 cache", e);
        }
    }

    private <T> T parseJson(String raw, Class<T> type) {
        try {
            return objectMapper.readValue(raw, type);
        } catch (Exception e) {
            throw new IllegalStateException("Malformed JSON in Tier 2 cache", e);
        }
    }

    private List<String> scanKeys(String pattern) {
        List<String> keys = new ArrayList<>();
        try (RedisConnection connection = redisTemplate.getConnectionFactory().getConnection()) {
            try (Cursor<byte[]> cursor =
                    connection.keyCommands().scan(ScanOptions.scanOptions().match(pattern).count(100).build())) {
                while (cursor.hasNext()) {
                    keys.add(new String(cursor.next(), StandardCharsets.UTF_8));
                }
            }
        }
        return keys;
    }
}
