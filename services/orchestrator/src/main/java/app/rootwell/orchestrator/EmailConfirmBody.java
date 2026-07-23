package app.rootwell.orchestrator;

import com.fasterxml.jackson.annotation.JsonProperty;

public record EmailConfirmBody(
        @JsonProperty("verification_token") String verificationToken,
        String code) {
}
