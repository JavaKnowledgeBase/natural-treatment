package app.rootwell.retrieval;

import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.TreeSet;
import org.springframework.stereotype.Service;

/**
 * Port of services/agents/retrieval/main.py -- expands symptoms into
 * candidate herbs by calling the Botanical and Compound knowledge services.
 * No LLM, no live external API calls in this phase (design doc §2.2's
 * live-fallback path is a later addition) -- everything reads from the
 * seed-backed Tier 1 cache via those two services.
 */
@Service
public class RetrievalService {

    private final BotanicalClient botanicalClient;
    private final CompoundClient compoundClient;

    public RetrievalService(BotanicalClient botanicalClient, CompoundClient compoundClient) {
        this.botanicalClient = botanicalClient;
        this.compoundClient = compoundClient;
    }

    @SuppressWarnings("unchecked")
    public CandidatesResponse candidates(CandidatesRequest req) {
        Map<String, Map<String, Object>> herbsById = new LinkedHashMap<>();

        for (String symptomId : req.symptomIds()) {
            for (Map<String, Object> herb : botanicalClient.herbsForSymptom(symptomId)) {
                herbsById.put(String.valueOf(herb.get("id")), herb);
            }
        }

        TreeSet<String> compoundIds = new TreeSet<>();
        for (Map<String, Object> herb : herbsById.values()) {
            Object compoundsObj = herb.get("compounds");
            if (compoundsObj instanceof List<?> links) {
                for (Object linkObj : links) {
                    if (linkObj instanceof Map<?, ?> link) {
                        Object compoundId = link.get("compound_id");
                        if (compoundId != null) {
                            compoundIds.add(String.valueOf(compoundId));
                        }
                    }
                }
            }
        }

        Map<String, Map<String, Object>> compoundRecords = new LinkedHashMap<>();
        if (!compoundIds.isEmpty()) {
            for (Map<String, Object> compound : compoundClient.compoundsByIds(new ArrayList<>(compoundIds))) {
                compoundRecords.put(String.valueOf(compound.get("id")), compound);
            }
        }

        for (Map<String, Object> herb : herbsById.values()) {
            Object compoundsObj = herb.get("compounds");
            if (compoundsObj instanceof List<?> links) {
                for (Object linkObj : links) {
                    if (linkObj instanceof Map<?, ?> rawLink) {
                        Map<String, Object> link = (Map<String, Object>) rawLink;
                        Map<String, Object> record = compoundRecords.get(String.valueOf(link.get("compound_id")));
                        if (record != null) {
                            link.put("mechanism_summary", record.get("mechanism_summary"));
                        }
                    }
                }
            }
        }

        return new CandidatesResponse(new ArrayList<>(herbsById.values()));
    }
}
