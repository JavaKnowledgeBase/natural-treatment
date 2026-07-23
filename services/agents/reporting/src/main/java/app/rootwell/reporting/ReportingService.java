package app.rootwell.reporting;

import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;
import java.util.Map;
import org.springframework.stereotype.Service;
import org.springframework.web.util.HtmlUtils;

/**
 * Port of services/agents/reporting/main.py's compile_report(). Deterministic
 * templating only, no LLM -- the disclaimer and structure must not vary.
 *
 * <p>Every field interpolated into {@code html} is run through
 * {@link HtmlUtils#htmlEscape(String)} first -- the Python original did not
 * do this (see docs/API_REFERENCE.md §4d, since fixed there too), and since
 * chat text and cause labels are free-form user/LLM-influenced input, this
 * is a real XSS-shaped gap otherwise. {@code text} output needs no escaping;
 * it's plain text, not markup.
 */
@Service
public class ReportingService {

    private static final DateTimeFormatter TIMESTAMP_FORMAT =
            DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm 'UTC'").withZone(ZoneOffset.UTC);

    private static final String DISCLAIMER =
            "This message is informational only and is not a substitute for professional "
                    + "medical advice, diagnosis, or treatment. The herb data used to generate these "
                    + "suggestions is an unreviewed starter dataset. Please consult a licensed "
                    + "clinician before making any changes to your care.";

    public CompileResponse compile(CompileRequest req) {
        String subject = "Your natural treatment session summary";

        StringBuilder text = new StringBuilder("YOUR SESSION SUMMARY\n").append("=".repeat(21)).append("\n\n");
        StringBuilder htmlBuilder = new StringBuilder("<h1>Your session summary</h1>");

        text.append("Symptoms you shared:\n");
        htmlBuilder.append("<h2>Symptoms you shared</h2><ul>");
        for (Map<String, Object> s : req.symptoms()) {
            String label = str(s.get("label"));
            text.append("  - ").append(label).append('\n');
            htmlBuilder.append("<li>").append(esc(label)).append("</li>");
        }
        htmlBuilder.append("</ul>");

        text.append("\nPossible contributing causes:\n");
        htmlBuilder.append("<h2>Possible contributing causes</h2><ul>");
        for (Map<String, Object> c : req.causes()) {
            String label = str(c.get("label"));
            String category = c.get("category") != null ? str(c.get("category")) : "general";
            text.append("  - ").append(label).append(" (").append(category).append(")\n");
            htmlBuilder.append("<li>").append(esc(label)).append(" (").append(esc(category)).append(")</li>");
        }
        htmlBuilder.append("</ul>");

        text.append("\nTop recommendations:\n");
        htmlBuilder.append("<h2>Top recommendations</h2>");
        for (Map<String, Object> r : req.recommendations()) {
            String herbName = str(r.get("herb_name"));
            String score = str(r.get("score"));
            String confidenceBand = str(r.get("confidence_band"));
            String reason = str(r.get("reason"));
            String evidenceLevel = str(r.get("evidence_level"));
            String safetyNote = r.get("safety_note") != null ? str(r.get("safety_note")) : "None noted";

            text.append("  - ").append(herbName).append(" (score ").append(score).append(", ")
                    .append(confidenceBand).append(" confidence)\n")
                    .append("      ").append(reason).append('\n')
                    .append("      Evidence level: ").append(evidenceLevel).append('\n')
                    .append("      Safety note: ").append(safetyNote).append('\n');

            htmlBuilder.append("<div><strong>").append(esc(herbName)).append("</strong> (score ")
                    .append(esc(score)).append(", ").append(esc(confidenceBand)).append(" confidence)")
                    .append("<p>").append(esc(reason)).append("</p>")
                    .append("<p>Evidence level: ").append(esc(evidenceLevel)).append("</p>")
                    .append("<p>Safety note: ").append(esc(safetyNote)).append("</p></div>");
        }

        text.append("\nFull conversation:\n");
        htmlBuilder.append("<h2>Full conversation</h2>");
        for (Map<String, Object> msg : req.chatHistory()) {
            String ts = formatTimestamp(msg.get("ts"));
            String role = str(msg.get("role"));
            String msgText = str(msg.get("text"));
            text.append("  [").append(ts).append("] ").append(role).append(": ").append(msgText).append('\n');
            htmlBuilder.append("<p><em>").append(ts).append("</em> <strong>").append(esc(role))
                    .append("</strong>: ").append(esc(msgText)).append("</p>");
        }

        text.append('\n').append(DISCLAIMER);
        htmlBuilder.append("<hr/><p><small>").append(DISCLAIMER).append("</small></p>");

        return new CompileResponse(subject, htmlBuilder.toString(), text.toString());
    }

    private String esc(String value) {
        return HtmlUtils.htmlEscape(value);
    }

    private String str(Object value) {
        return value == null ? "" : String.valueOf(value);
    }

    private String formatTimestamp(Object ts) {
        double epochSeconds = ts instanceof Number number ? number.doubleValue() : 0.0;
        return TIMESTAMP_FORMAT.format(Instant.ofEpochMilli((long) (epochSeconds * 1000)));
    }
}
