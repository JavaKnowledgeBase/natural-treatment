package app.rootwell.safety;

import java.util.List;

public record EvaluateResponse(List<Verdict> verdicts) {
}
