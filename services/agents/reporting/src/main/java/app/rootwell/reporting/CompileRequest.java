package app.rootwell.reporting;

import com.fasterxml.jackson.annotation.JsonProperty;
import java.util.List;
import java.util.Map;

public record CompileRequest(
        @JsonProperty("chat_history") List<Map<String, Object>> chatHistory,
        List<Map<String, Object>> symptoms,
        List<Map<String, Object>> causes,
        List<Map<String, Object>> recommendations) {
}
