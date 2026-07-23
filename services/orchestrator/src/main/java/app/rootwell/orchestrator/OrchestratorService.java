package app.rootwell.orchestrator;

import java.time.Instant;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.web.server.ResponseStatusException;

/**
 * Port of services/orchestrator/main.py -- runs the state graph from
 * application_design_v2 §4: Greeting -> SymptomCollection -> CauseCollection
 * -> Analysis -> Results -> EmailSent/Purged. Owns all Tier 2 (session)
 * reads/writes; every agent it calls is a stateless HTTP service. There is
 * no profile-collection state anywhere in this graph -- that's what makes
 * "never proactively ask for personal details" a structural property of the
 * orchestration, not just a prompt instruction (see docs/ARCHITECTURE.md §5).
 */
@Service
public class OrchestratorService {

    /** UI + LLM-conversation languages only (see docs/ARCHITECTURE.md) --
     * backend catalog matching stays English regardless of this value. */
    private static final Set<String> SUPPORTED_LANGUAGES = Set.of("en", "hi", "zh", "fr", "es");
    private static final String DEFAULT_LANGUAGE = "en";

    private final SessionCacheService cache;
    private final AgentClients agents;

    public OrchestratorService(SessionCacheService cache, AgentClients agents) {
        this.cache = cache;
        this.agents = agents;
    }

    private String normalizeLanguage(String language) {
        return language != null && SUPPORTED_LANGUAGES.contains(language) ? language : DEFAULT_LANGUAGE;
    }

    public Map<String, Object> createSession(String language) {
        String sid = newSessionId();
        String lang = normalizeLanguage(language);
        cache.createSession(sid, lang);
        Map<String, Object> greetingResp = agents.intake.get("/intake/greeting?language=" + lang);
        String greeting = String.valueOf(greetingResp.get("message"));
        cache.appendChatMessage(sid, "assistant", greeting);
        return Map.of("session_id", sid, "greeting", greeting);
    }

    public Map<String, Object> getState(String sid) {
        requireSession(sid);
        Map<String, Object> state = new HashMap<>();
        state.put("meta", cache.getMeta(sid));
        state.put("chat", cache.getChatHistory(sid));
        state.put("symptoms", cache.listCachedItems(sid, "symptoms"));
        state.put("causes", cache.listCachedItems(sid, "causes"));
        state.put("recommendations", cache.getList(sid, "recommendations"));
        return state;
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> postMessage(String sid, MessageRequest req) {
        Map<String, Object> meta = requireSession(sid);
        String step = String.valueOf(meta.get("current_step"));
        String language = normalizeLanguage((String) meta.get("language"));
        cache.appendChatMessage(sid, "user", req.text());

        List<Map<String, Object>> suggestions;
        Map<String, Object> extractedProfile;
        String assistantMessage;

        if (step.equals("greeting") || step.equals("symptom_collection")) {
            if (step.equals("greeting")) {
                cache.setStep(sid, "symptom_collection");
                step = "symptom_collection";
            }
            List<Map<String, Object>> knownSymptoms = cache.listCachedItems(sid, "symptoms");
            List<String> knownIds = knownSymptoms.stream().map(s -> String.valueOf(s.get("id"))).toList();

            Map<String, Object> result = agents.intake.post("/intake/symptom-turn", Map.of(
                    "user_message", req.text(),
                    "known_symptom_ids", knownIds,
                    "language", language));

            for (Map<String, Object> m : (List<Map<String, Object>>) result.getOrDefault("matched", List.of())) {
                String id = String.valueOf(m.get("id"));
                cache.addCachedItem(sid, "symptoms", id, cacheItem(id, String.valueOf(m.get("label")), "user_stated", null));
            }
            suggestions = (List<Map<String, Object>>) result.getOrDefault("suggestions", List.of());
            extractedProfile = (Map<String, Object>) result.getOrDefault("extracted_profile", Map.of());
            assistantMessage = String.valueOf(result.get("assistant_message"));

        } else if (step.equals("cause_collection")) {
            List<Map<String, Object>> knownCauses = cache.listCachedItems(sid, "causes");
            List<String> knownLabels = knownCauses.stream().map(c -> String.valueOf(c.get("label"))).toList();

            Map<String, Object> result = agents.intake.post("/intake/cause-turn", Map.of(
                    "user_message", req.text(),
                    "known_cause_labels", knownLabels,
                    "language", language));

            for (Map<String, Object> m : (List<Map<String, Object>>) result.getOrDefault("matched", List.of())) {
                String itemId = shortId();
                Object category = m.get("category");
                cache.addCachedItem(sid, "causes", itemId,
                        cacheItem(itemId, String.valueOf(m.get("label")), "user_stated", category == null ? null : String.valueOf(category)));
            }
            suggestions = (List<Map<String, Object>>) result.getOrDefault("suggestions", List.of());
            extractedProfile = (Map<String, Object>) result.getOrDefault("extracted_profile", Map.of());
            assistantMessage = String.valueOf(result.get("assistant_message"));

        } else {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Chat input isn't accepted in step '" + step + "'");
        }

        applyExtractedProfile(sid, extractedProfile);
        cache.appendChatMessage(sid, "assistant", assistantMessage);

        Map<String, Object> turnResult = new HashMap<>();
        turnResult.put("assistant_message", assistantMessage);
        turnResult.put("current_step", step);
        turnResult.put("suggestions", suggestions);
        turnResult.put("symptoms", cache.listCachedItems(sid, "symptoms"));
        turnResult.put("causes", cache.listCachedItems(sid, "causes"));
        return turnResult;
    }

    public Map<String, Object> addItem(String sid, AddItemRequest req) {
        requireSession(sid);
        String cacheName = req.kind().equals("symptom") ? "symptoms" : "causes";
        String itemId = req.id() != null ? req.id() : shortId();
        cache.addCachedItem(sid, cacheName, itemId, cacheItem(itemId, req.label(), "suggested_accepted", req.category()));
        return Map.of("status", "added", "id", itemId);
    }

    public Map<String, Object> removeItem(String sid, RemoveItemRequest req) {
        requireSession(sid);
        String cacheName = req.kind().equals("symptom") ? "symptoms" : "causes";
        cache.removeCachedItem(sid, cacheName, req.id());
        return Map.of("status", "removed");
    }

    public Map<String, Object> advanceToCauses(String sid) {
        Map<String, Object> meta = requireSession(sid);
        if (!"symptom_collection".equals(meta.get("current_step"))) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Can only advance to cause collection from symptom collection");
        }
        cache.setStep(sid, "cause_collection");
        String message = "What events, stressors, or daily activities do you think may have contributed?";
        cache.appendChatMessage(sid, "assistant", message);
        return Map.of("current_step", "cause_collection", "assistant_message", message);
    }

    @SuppressWarnings("unchecked")
    public Map<String, Object> analyze(String sid) {
        Map<String, Object> meta = requireSession(sid);
        String currentStep = String.valueOf(meta.get("current_step"));
        if (!currentStep.equals("symptom_collection") && !currentStep.equals("cause_collection")) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Analysis is only available during symptom or cause collection");
        }

        List<Map<String, Object>> symptoms = cache.listCachedItems(sid, "symptoms");
        List<Map<String, Object>> causes = cache.listCachedItems(sid, "causes");
        if (symptoms.isEmpty() && causes.isEmpty()) {
            throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "Add at least one symptom or cause before analyzing");
        }

        List<String> symptomIds = symptoms.stream().map(s -> String.valueOf(s.get("id"))).toList();
        Map<String, Object> profile = cache.getProfile(sid);
        String language = normalizeLanguage((String) meta.get("language"));

        Map<String, Object> mappingResult = agents.mapping.post("/mapping/analyze", Map.of(
                "symptom_ids", symptomIds,
                "language", language));
        Map<String, Object> retrievalResult = agents.retrieval.post("/retrieval/candidates", Map.of(
                "symptom_ids", symptomIds,
                "imbalances", mappingResult.getOrDefault("imbalances", List.of())));
        List<Map<String, Object>> candidates = (List<Map<String, Object>>) retrievalResult.get("candidates");

        Map<String, Object> safetyResult = agents.safety.post("/safety/evaluate", Map.of("candidates", candidates, "profile", profile));
        Map<String, Object> scoringResult = agents.scoring.post("/scoring/rank", Map.of(
                "symptom_ids", symptomIds,
                "candidates", candidates,
                "verdicts", safetyResult.get("verdicts")));
        Map<String, Object> explanationResult = agents.explanation.post("/explanation/generate", Map.of(
                "candidates", candidates,
                "ranked", scoringResult.get("ranked"),
                "verdicts", safetyResult.get("verdicts"),
                "language", language));

        List<Map<String, Object>> recommendations = (List<Map<String, Object>>) explanationResult.get("recommendations");
        cache.clearList(sid, "recommendations");
        for (Map<String, Object> rec : recommendations) {
            cache.pushListItem(sid, "recommendations", rec);
        }

        cache.setStep(sid, "results");
        Object reasoning = mappingResult.get("reasoning");
        String summary = reasoning != null
                ? String.valueOf(reasoning)
                : "Here's what the starter dataset suggests based on what you shared.";
        cache.appendChatMessage(sid, "assistant", summary);

        Map<String, Object> result = new HashMap<>();
        result.put("current_step", "results");
        result.put("reasoning", reasoning);
        result.put("recommendations", recommendations);
        return result;
    }

    public Map<String, Object> emailRequest(String sid, EmailRequestBody req) {
        requireSession(sid);
        return agents.email.post("/email/verify", Map.of("to", req.to()));
    }

    public Map<String, Object> emailConfirm(String sid, EmailConfirmBody req) {
        requireSession(sid);
        Map<String, Object> state = getState(sid);
        Map<String, Object> compiled = agents.reporting.post("/reporting/compile", Map.of(
                "chat_history", state.get("chat"),
                "symptoms", state.get("symptoms"),
                "causes", state.get("causes"),
                "recommendations", state.get("recommendations")));
        Map<String, Object> sendResult = agents.email.post("/email/send", Map.of(
                "verification_token", req.verificationToken(),
                "code", req.code(),
                "subject", compiled.get("subject"),
                "html", compiled.get("html"),
                "text", compiled.get("text")));
        cache.setStep(sid, "email_sent");
        int deleted = cache.purgeSession(sid);
        return Map.of("email", sendResult, "purged_keys", deleted);
    }

    public Map<String, Object> endSession(String sid) {
        requireSession(sid);
        int deleted = cache.purgeSession(sid);
        return Map.of("status", "purged", "purged_keys", deleted);
    }

    private Map<String, Object> requireSession(String sid) {
        Map<String, Object> meta = cache.getMeta(sid);
        if (meta == null) {
            throw new ResponseStatusException(HttpStatus.NOT_FOUND, "Session not found or already expired/purged");
        }
        return meta;
    }

    private void applyExtractedProfile(String sid, Map<String, Object> extracted) {
        if (extracted != null && !extracted.isEmpty()) {
            cache.updateProfile(sid, extracted);
        }
    }

    private Map<String, Object> cacheItem(String itemId, String label, String source, String category) {
        Map<String, Object> item = new HashMap<>();
        item.put("id", itemId);
        item.put("label", label);
        item.put("source", source);
        item.put("category", category);
        item.put("ts", Instant.now().toEpochMilli() / 1000.0);
        return item;
    }

    private String newSessionId() {
        return UUID.randomUUID().toString().replace("-", "");
    }

    private String shortId() {
        return UUID.randomUUID().toString().replace("-", "").substring(0, 8);
    }
}
