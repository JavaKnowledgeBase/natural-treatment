package app.rootwell.retrieval;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record CandidatesRequest(
        @JsonProperty("symptom_ids") List<String> symptomIds,
        List<String> imbalances) {
}
