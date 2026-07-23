package app.rootwell.safety;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;

public record Verdict(
        @JsonProperty("herb_id") String herbId,
        boolean allowed,
        @JsonProperty("safety_factor") double safetyFactor,
        @JsonProperty("rules_fired") List<String> rulesFired,
        List<String> notes) {
}
