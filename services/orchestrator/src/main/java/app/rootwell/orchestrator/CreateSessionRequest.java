package app.rootwell.orchestrator;

/** {@code language} is optional and only affects UI-visible text generated
 * by the LLM-backed agents (intake/mapping/explanation) -- see
 * OrchestratorService#normalizeLanguage. Backend catalog matching stays
 * English-only regardless of this value. */
public record CreateSessionRequest(String language) {
}
