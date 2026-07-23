package app.rootwell.scoring;

import java.util.List;

public record RankResponse(List<RankedCandidate> ranked) {
}
