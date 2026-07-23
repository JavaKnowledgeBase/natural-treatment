package app.rootwell.email;

import com.fasterxml.jackson.annotation.JsonProperty;

public record VerifyResponse(
        @JsonProperty("verification_token") String verificationToken,
        @JsonProperty("mock_mode") boolean mockMode) {
}
