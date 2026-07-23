package app.rootwell.scoring;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

public record RankRequest(
        @JsonProperty("symptom_ids") List<String> symptomIds,
        List<Map<String, Object>> candidates,
        List<Map<String, Object>> verdicts) {
}
