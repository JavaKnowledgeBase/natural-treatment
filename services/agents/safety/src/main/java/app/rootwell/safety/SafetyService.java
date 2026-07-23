package app.rootwell.safety;

import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import org.springframework.stereotype.Service;

/**
 * Port of services/agents/safety/main.py -- deterministic contraindication
 * checking. Deliberately independent from agent-scoring (design doc §3.2):
 * this service must never call an LLM to decide whether something is safe.
 * It only matches the user's *volunteered* profile fields against the
 * ground-truth rules from knowledge-rules. There is no LLM dependency
 * anywhere in this module or its pom.xml -- structurally, not just by
 * convention.
 */
@Service
public class SafetyService {

    private static final Map<String, Double> SEVERITY_TO_FACTOR = Map.of(
            "moderate", 0.6,
            "high", 0.2,
            "disallowed", 0.0);

    private static final Map<String, List<String>> CONDITION_KEYWORDS = Map.ofEntries(
            Map.entry("thyroid_disorder", List.of("thyroid")),
            Map.entry("hormone_sensitive_condition", List.of("hormone", "estrogen", "breast cancer", "endometriosis", "pcos")),
            Map.entry("autoimmune_condition", List.of("autoimmune", "lupus", "rheumatoid", "hashimoto", "crohn", "multiple sclerosis")),
            Map.entry("kidney_disease", List.of("kidney", "renal")),
            Map.entry("liver_disease", List.of("liver", "hepatic", "hepatitis", "cirrhosis")),
            Map.entry("hypertension", List.of("hypertension", "high blood pressure")),
            Map.entry("gerd", List.of("gerd", "acid reflux", "heartburn")),
            Map.entry("gallstones", List.of("gallstone", "gallbladder")),
            Map.entry("bipolar_disorder", List.of("bipolar")),
            Map.entry("cardiac_medication", List.of("heart medication", "cardiac", "beta blocker", "heart failure")),
            Map.entry("anticoagulant_medication", List.of("blood thinner", "anticoagulant", "warfarin", "aspirin", "heparin", "clopidogrel")),
            Map.entry("sedative_medication", List.of("sedative", "benzodiazepine", "sleep aid", "ambien", "xanax", "valium")));

    private static final List<String> PEDIATRIC_MARKERS =
            List.of("child", "kid", "infant", "toddler", "teen", "minor");

    private final RulesClient rulesClient;

    public SafetyService(RulesClient rulesClient) {
        this.rulesClient = rulesClient;
    }

    public EvaluateResponse evaluate(EvaluateRequest req) {
        Map<String, Object> profile = req.profile() != null ? req.profile() : Map.of();
        List<Map<String, Object>> allRules = rulesClient.listAllRules();

        Map<String, List<Map<String, Object>>> rulesByHerb = new java.util.HashMap<>();
        for (Map<String, Object> rule : allRules) {
            rulesByHerb.computeIfAbsent(String.valueOf(rule.get("herb_id")), k -> new ArrayList<>()).add(rule);
        }

        String haystack = profileHaystack(profile);
        List<Verdict> verdicts = new ArrayList<>();

        for (Map<String, Object> herb : req.candidates()) {
            String herbId = String.valueOf(herb.get("id"));
            List<Map<String, Object>> fired = rulesByHerb.getOrDefault(herbId, List.of()).stream()
                    .filter(rule -> conditionMatches(String.valueOf(rule.get("condition")), profile, haystack))
                    .toList();

            if (fired.isEmpty()) {
                verdicts.add(new Verdict(herbId, true, 1.0, List.of(), List.of()));
                continue;
            }

            Map<String, Object> worst = worstRule(fired);
            String severity = String.valueOf(worst.get("severity"));
            double safetyFactor = SEVERITY_TO_FACTOR.getOrDefault(severity, 1.0);
            List<String> rulesFired = fired.stream().map(r -> String.valueOf(r.get("id"))).toList();
            List<String> notes = fired.stream().map(r -> String.valueOf(r.get("note"))).toList();

            verdicts.add(new Verdict(herbId, !severity.equals("disallowed"), safetyFactor, rulesFired, notes));
        }

        return new EvaluateResponse(verdicts);
    }

    /** Mirrors Python's max(fired, key=lambda r: SEVERITY_TO_FACTOR.get(severity, 1.0) * -1):
     * the most restrictive (lowest factor) rule wins; first occurrence wins ties. */
    private Map<String, Object> worstRule(List<Map<String, Object>> fired) {
        Map<String, Object> worst = fired.get(0);
        double worstFactor = SEVERITY_TO_FACTOR.getOrDefault(String.valueOf(worst.get("severity")), 1.0);
        for (Map<String, Object> rule : fired) {
            double factor = SEVERITY_TO_FACTOR.getOrDefault(String.valueOf(rule.get("severity")), 1.0);
            if (factor < worstFactor) {
                worst = rule;
                worstFactor = factor;
            }
        }
        return worst;
    }

    private String profileHaystack(Map<String, Object> profile) {
        List<String> parts = new ArrayList<>();
        parts.addAll(stringList(profile.get("medications")));
        parts.addAll(stringList(profile.get("chronic_conditions")));
        return String.join(" | ", parts).toLowerCase();
    }

    @SuppressWarnings("unchecked")
    private List<String> stringList(Object value) {
        if (value instanceof List<?> list) {
            return list.stream().map(String::valueOf).toList();
        }
        return List.of();
    }

    private boolean conditionMatches(String condition, Map<String, Object> profile, String haystack) {
        if (condition.equals("pregnancy")) {
            String status = String.valueOf(Optional.ofNullable(profile.get("pregnancy_status")).orElse("")).toLowerCase();
            return !status.isEmpty() && !status.contains("not") && status.contains("pregnant");
        }
        if (condition.equals("pediatric")) {
            String ageRange = String.valueOf(Optional.ofNullable(profile.get("age_range")).orElse("")).toLowerCase();
            return PEDIATRIC_MARKERS.stream().anyMatch(ageRange::contains);
        }
        List<String> keywords = CONDITION_KEYWORDS.getOrDefault(condition, List.of());
        return keywords.stream().anyMatch(haystack::contains);
    }
}
