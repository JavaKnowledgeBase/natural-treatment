package app.rootwell.email;

import com.fasterxml.jackson.annotation.JsonProperty;

public record SendResponse(String status, @JsonProperty("message_id") String messageId) {
}
