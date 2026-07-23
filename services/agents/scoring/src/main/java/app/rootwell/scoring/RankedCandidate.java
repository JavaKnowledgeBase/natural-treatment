package app.rootwell.scoring;

import com.fasterxml.jackson.annotation.JsonProperty;

public record RankedCandidate(
        @JsonProperty("herb_id") String herbId,
        @JsonProperty("base_score") double baseScore,
        @JsonProperty("adjusted_score") double adjustedScore,
        @JsonProperty("confidence_band") String confidenceBand,
        @JsonProperty("safety_factor") double safetyFactor) {
}
