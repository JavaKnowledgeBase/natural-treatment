package app.rootwell.retrieval;

import java.util.List;
import java.util.Map;

public record CandidatesResponse(List<Map<String, Object>> candidates) {
}
