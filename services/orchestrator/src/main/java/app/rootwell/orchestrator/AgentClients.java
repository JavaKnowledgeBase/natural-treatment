package app.rootwell.orchestrator;

import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

/** One DownstreamClient per agent service, all built with the same 30s
 * timeout the original Python orchestrator used for these calls -- long
 * enough to cover the whole multi-hop /analyze chain's slowest single hop. */
@Component
public class AgentClients {

    private static final Duration TIMEOUT = Duration.ofSeconds(30);

    public final DownstreamClient intake;
    public final DownstreamClient mapping;
    public final DownstreamClient retrieval;
    public final DownstreamClient safety;
    public final DownstreamClient scoring;
    public final DownstreamClient explanation;
    public final DownstreamClient reporting;
    public final DownstreamClient email;

    public AgentClients(
            @Value("${agents.intake-url}") String intakeUrl,
            @Value("${agents.mapping-url}") String mappingUrl,
            @Value("${agents.retrieval-url}") String retrievalUrl,
            @Value("${agents.safety-url}") String safetyUrl,
            @Value("${agents.scoring-url}") String scoringUrl,
            @Value("${agents.explanation-url}") String explanationUrl,
            @Value("${agents.reporting-url}") String reportingUrl,
            @Value("${agents.email-url}") String emailUrl) {
        this.intake = new DownstreamClient(intakeUrl, TIMEOUT);
        this.mapping = new DownstreamClient(mappingUrl, TIMEOUT);
        this.retrieval = new DownstreamClient(retrievalUrl, TIMEOUT);
        this.safety = new DownstreamClient(safetyUrl, TIMEOUT);
        this.scoring = new DownstreamClient(scoringUrl, TIMEOUT);
        this.explanation = new DownstreamClient(explanationUrl, TIMEOUT);
        this.reporting = new DownstreamClient(reportingUrl, TIMEOUT);
        this.email = new DownstreamClient(emailUrl, TIMEOUT);
    }
}
