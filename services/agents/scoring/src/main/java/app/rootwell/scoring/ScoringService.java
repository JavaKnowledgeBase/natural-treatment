package app.rootwell.scoring;

import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.springframework.stereotype.Service;

/**
 * Pure port of services/agents/scoring/main.py's confidence-score formula
 * (application_design_v2 §7). No LLM, no Redis, no external calls -- every
 * input arrives in the request body and every output is a deterministic
 * function of it, which is exactly why this agent is one of the two
 * (alongside agent-safety) that must never depend on model output.
 *
 *     Score = 0.30 x Evidence Strength
 *           + 0.25 x Mechanism Relevance
 *           + 0.20 x Concentration / Bioavailability
 *           + 0.15 x Safety Profile
 *           + 0.10 x Traditional / Historical Use
 *
 *     Adjusted Score = Score x Safety Factor (from the Safety Agent's verdict)
 */
@Service
public class ScoringService {

    private static final Map<String, Double> EVIDENCE_LEVEL_SCORES = Map.of(
            "clinical_trial", 1.0,
            "human_observational", 0.8,
            "animal_model", 0.6,
            "in_vitro_cellular", 0.3,
            "traditional_and_limited_clinical", 0.4,
            "anecdotal_traditional", 0.1);

    public RankResponse rank(RankRequest req) {
        Map<String, Map<String, Object>> verdictByHerb = new HashMap<>();
        for (Map<String, Object> verdict : req.verdicts()) {
            verdictByHerb.put(String.valueOf(verdict.get("herb_id")), verdict);
        }

        List<RankedCandidate> ranked = req.candidates().stream()
                .map(herb -> scoreOne(herb, req.symptomIds(), verdictByHerb))
                .sorted((a, b) -> Double.compare(b.adjustedScore(), a.adjustedScore()))
                .toList();

        return new RankResponse(ranked);
    }

    private RankedCandidate scoreOne(
            Map<String, Object> herb, List<String> symptomIds, Map<String, Map<String, Object>> verdictByHerb) {
        String herbId = String.valueOf(herb.get("id"));

        double baseScore =
                0.30 * evidenceStrength(herb)
                        + 0.25 * mechanismRelevance(herb, symptomIds)
                        + 0.20 * concentrationBioavailability(herb)
                        + 0.15 * safetyProfile(herb)
                        + 0.10 * traditionalUse(herb);

        Map<String, Object> verdict = verdictByHerb.get(herbId);
        double safetyFactor = verdict != null ? toDouble(verdict.get("safety_factor"), 1.0) : 1.0;
        boolean allowed = verdict == null || Boolean.TRUE.equals(verdict.getOrDefault("allowed", true));
        if (!allowed) {
            safetyFactor = 0.0;
        }

        double adjustedScore = round4(baseScore * safetyFactor);
        return new RankedCandidate(herbId, round4(baseScore), adjustedScore, confidenceBand(adjustedScore), safetyFactor);
    }

    @SuppressWarnings("unchecked")
    private double evidenceStrength(Map<String, Object> herb) {
        String level = String.valueOf(herb.getOrDefault("evidence_level", ""));
        return EVIDENCE_LEVEL_SCORES.getOrDefault(level, 0.3);
    }

    @SuppressWarnings("unchecked")
    private double mechanismRelevance(Map<String, Object> herb, List<String> symptomIds) {
        Set<String> requested = new HashSet<>(symptomIds);
        if (requested.isEmpty()) {
            return 0.3;
        }
        Object linkedObj = herb.get("linked_symptoms");
        Set<String> linked = linkedObj instanceof List<?> list
                ? list.stream().map(String::valueOf).collect(java.util.stream.Collectors.toSet())
                : Set.of();
        long overlap = linked.stream().filter(requested::contains).count();
        return Math.min((double) overlap / requested.size(), 1.0);
    }

    private double concentrationBioavailability(Map<String, Object> herb) {
        int compoundCount = listSize(herb.get("compounds"));
        return Math.min(0.5 + 0.15 * compoundCount, 1.0);
    }

    private double safetyProfile(Map<String, Object> herb) {
        int ruleCount = listSize(herb.get("contraindications"));
        return Math.max(1.0 - 0.15 * ruleCount, 0.4);
    }

    private double traditionalUse(Map<String, Object> herb) {
        String level = String.valueOf(herb.getOrDefault("evidence_level", ""));
        return level.contains("traditional") ? 0.8 : 0.5;
    }

    private String confidenceBand(double adjustedScore) {
        if (adjustedScore >= 0.75) return "high";
        if (adjustedScore >= 0.5) return "moderate";
        return "low";
    }

    private int listSize(Object value) {
        return value instanceof List<?> list ? list.size() : 0;
    }

    private double toDouble(Object value, double fallback) {
        if (value instanceof Number number) {
            return number.doubleValue();
        }
        return fallback;
    }

    private double round4(double value) {
        return Math.round(value * 10_000.0) / 10_000.0;
    }
}
