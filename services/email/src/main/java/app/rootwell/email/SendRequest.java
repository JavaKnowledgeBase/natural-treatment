package app.rootwell.email;

import com.fasterxml.jackson.annotation.JsonProperty;

public record SendRequest(
        @JsonProperty("verification_token") String verificationToken,
        String code,
        String subject,
        String html,
        String text) {
}
