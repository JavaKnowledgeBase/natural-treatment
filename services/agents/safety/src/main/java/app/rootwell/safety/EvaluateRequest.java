package app.rootwell.safety;

import java.util.List;
import java.util.Map;

public record EvaluateRequest(List<Map<String, Object>> candidates, Map<String, Object> profile) {
}
