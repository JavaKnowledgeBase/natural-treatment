# Natural Treatment Recommendation Engine — Comprehensive Application Design

## 1. Product Vision

Build an evidence-based decision support application that helps users explore herbal and natural interventions for symptoms associated with nutrient deficiency, toxic excess, or biochemical imbalance.

The system should:
- accept a symptom or set of symptoms from a user,
- map those symptoms to likely biochemical causes or compound imbalances,
- identify herbs and natural ingredients that may help address those imbalances,
- rank candidate treatments by a confidence score,
- explain why a treatment is recommended,
- enforce safety constraints and contraindications,
- clearly label the system as informational and not a substitute for medical care.

Important principle: this is not a diagnostic tool and should never present itself as a replacement for a licensed clinician.

---

## 2. Core Problem to Solve

The key hypothesis is:
- symptoms may be caused by biochemical deviations,
- those deviations may involve deficiency of useful compounds or excess of harmful compounds,
- herbs may help by providing nutrients, bioactive compounds, or supportive effects such as antioxidant, chelating, anti-inflammatory, or metabolic support action.

The application should therefore model a chain like:

Symptom -> probable biochemical imbalance -> candidate compounds -> candidate herbs -> recommendation score

---

## 3. Product Goals

### Primary goals
- Recommend the most plausible herbal options for a given symptom context.
- Produce transparent explanations for each ranking.
- Use high-quality evidence where possible.
- Keep the recommendation engine safe and conservative.

### Secondary goals
- Support multi-symptom input.
- Allow users to compare multiple herbs side-by-side.
- Show confidence levels with evidence sources.
- Support future expansion into personalized health profiles.

---

## 4. Non-Goals for MVP

The first version should not attempt to:
- diagnose disease conditions directly,
- prescribe medical treatment for serious illnesses,
- replace physician advice,
- claim guaranteed efficacy,
- support regulated medical claims without review.

---

## 5. High-Level User Flow

1. User enters symptoms.
2. System maps symptoms to likely biochemical patterns.
3. System retrieves candidate compounds and herbs.
4. Safety rules filter out unsafe or high-risk options.
5. Engine scores and ranks candidates.
6. App presents ranked recommendations with evidence and caution notes.
7. User can view details, supporting evidence, and warnings.

---

## 6. Recommended Application Architecture

### 6.1 Architecture Overview

The app should be split into five layers:

1. Frontend layer
   - web app for symptom input and recommendation display
   - simple, calm, evidence-focused UI

2. Application/API layer
   - handles request orchestration
   - runs the recommendation logic
   - manages user sessions and explanation generation

3. Knowledge layer
   - stores herbs, compounds, symptoms, evidence, and mappings
   - supports structured scoring and retrieval

4. External data integration layer
   - pulls botanical and biochemical data from public scientific APIs
   - stores normalized results for later use

5. Safety and governance layer
   - blocks unsafe recommendations
   - logs why recommendations were rejected
   - supports future expert review

### 6.2 Suggested Stack

#### Frontend
- React or Next.js
- TypeScript
- Tailwind CSS

#### Backend
- Python FastAPI
- PostgreSQL
- Redis (optional for caching)

#### Data ingestion
- Python workers
- Celery or background jobs

#### Infrastructure
- Docker Compose for local development
- AWS / Azure / GCP for production deployment
- Object storage for raw API responses

---

## 7. System Components

### 7.1 Symptom Intake Module
Purpose: collect user symptoms and context.

Inputs:
- symptom list
- age range
- pregnancy status
- medications
- chronic conditions
- allergies

Outputs:
- structured symptom profile

### 7.2 Symptom-to-Biochemical Mapping Engine
Purpose: map symptoms to potential biochemical imbalance patterns.

This can work in two modes:
- rule-based mapping for MVP
- ML/LLM-assisted mapping for later versions

Example mapping:
- fatigue -> possible iron deficiency, mitochondrial stress, low B12
- chronic headaches -> possible magnesium deficiency, inflammation, toxin burden
- skin rash -> possible allergy-related inflammation or oxidative stress

### 7.3 Compound Knowledge Base
Purpose: store compounds that are associated with symptoms, mechanisms, and evidence.

Example records:
- compound name
- molecular identifier
- mechanism of action
- target symptom cluster
- safety concerns
- evidence level

### 7.4 Herb Knowledge Base
Purpose: store herbal options linked to compounds and mechanisms.

Example records:
- herb name
- plant part used
- compound profile
- concentration approximations
- traditional use
- evidence level
- contraindications

### 7.5 Recommendation Scoring Engine
Purpose: score herbs based on evidence, relevance, concentration, and safety.

### 7.6 Safety Layer
Purpose: prevent unsafe recommendations.

Examples of rule checks:
- avoid herbs with known severe interactions with anticoagulants
- avoid for pregnancy unless explicitly marked safe
- avoid for kidney disease when toxicity risk is high
- avoid high-dose recommendations in minors

### 7.7 Explanation Engine
Purpose: show why a treatment scored highly.

Example explanation:
- “This herb contains compounds associated with antioxidant activity and has moderate clinical evidence for symptom support.”

---

## 8. Data Model Design

A relational schema is appropriate for the MVP.

### Core tables

#### symptoms
- id
- name
- category
- description

#### compounds
- id
- name
- canonical_name
- formula
- pubchem_id
- chebi_id
- mechanism_summary

#### herbs
- id
- name
- scientific_name
- plant_part_used
- common_use

#### herb_compounds
- herb_id
- compound_id
- concentration_estimate
- concentration_unit
- evidence_note

#### symptom_compound_links
- symptom_id
- compound_id
- relevance_score
- evidence_level
- source

#### symptom_herb_links
- symptom_id
- herb_id
- relevance_score
- evidence_level
- source

#### evidence_sources
- id
- source_name
- source_type
- url
- publication_year
- evidence_level

#### contraindications
- id
- herb_id
- condition_id
- severity
- note

#### user_profiles
- id
- age_group
- pregnancy_status
- medication_list
- allergy_list
- medical_conditions

#### recommendations
- id
- user_profile_id
- symptom_profile_id
- herb_id
- score
- explanation
- created_at

---

## 9. Scoring Model

The initial formula from your research is a good starting point, but for a safer product the scoring engine should include multiple factors.

### Recommended scoring formula

Score =
- 0.30 × Evidence Strength
- 0.25 × Mechanism Relevance
- 0.20 × Concentration / Bioavailability
- 0.15 × Safety Profile
- 0.10 × Traditional / Historical Use

### Factor definitions

#### Evidence Strength
- clinical trial = 1.0
- human observational = 0.8
- animal model = 0.6
- in vitro / cellular = 0.3
- anecdotal / traditional = 0.1

#### Mechanism Relevance
How well the herb or compound aligns with the likely biochemical issue.

#### Concentration / Bioavailability
How much of the active compounds the herb is known to contain and how bioavailable they are.

#### Safety Profile
Penalize unsafe combinations, high-risk populations, and known toxic effects.

#### Traditional / Historical Use
Useful as supporting evidence, but not enough alone to make a strong recommendation.

### Safety penalty logic
Apply a reduction if any of the following are true:
- known drug interaction
- pregnancy risk
- pediatric risk
- kidney/liver impairment concern
- high toxicity profile

Example:

Adjusted Score = Base Score × Safety Factor

Where:
- Safety Factor = 1.0 for low-risk
- 0.6 for moderate concern
- 0.2 for high concern
- 0 for disallowed cases

---

## 10. Recommendation Pipeline

### Phase A: Intake
- collect symptom input
- collect user context
- normalize the data

### Phase B: Candidate Generation
- look up relevant compounds for each symptom
- expand to associated herbs
- include supporting evidence links

### Phase C: Filtering
- remove herbs that violate safety rules
- remove herbs without sufficient evidence
- remove duplicate candidates

### Phase D: Scoring
- compute evidence and relevance scores
- apply safety penalties
- rank by final score

### Phase E: Presentation
- show top 3 to 5 results
- include confidence band
- include explanation summary
- include safety note

---

## 11. External Data Sources Strategy

### Botanical / phytochemistry data
Recommended sources:
- IMPPAT
- KNApSAcK
- plant-specific databases

### Compound validation
Recommended sources:
- ChEBI
- PubChem

### Symptom-to-compound evidence
Recommended sources:
- CTD (Comparative Toxicogenomics Database)
- PubMed or open biomedical literature APIs

### Data ingestion approach
- create a normalizer layer that turns each source into a common format
- store raw API payloads in a separate storage area
- create curated records in the main database

---

## 12. User Experience Design

### Main screen
- symptom entry form
- quick select chips for common symptoms
- optional context questions

### Recommendation results screen
- top recommended herbs
- confidence score as a percentage or band
- explanation panel
- evidence badges
- safety warning panel
- “compare” button

### Detail screen
- herb summary
- compounds linked to the herb
- evidence sources
- known caution notes
- not recommended if unsafe for user profile

### 12.5 Conversational Intake Flow (Requested UX)

This flow should be the primary experience for the first version of the product.

#### Layout
- The right half of the screen is the chat panel.
- The left half can show a lightweight summary panel, active selections, or a background explanation of what the system is learning.
- The chat panel should feel like a guided conversation rather than a form.

#### Step 1: Greeting and first question
- On first load, the chat opens with:
  - “Hello! How are you feeling today?”
- The user types their concern in free text or selects a common starter option.
- After submission, the system responds with a set of related symptoms.

#### Step 2: Symptom collection loop
- The system presents related symptoms one at a time or in small groups.
- The user can choose one symptom at a time.
- Each selected symptom is added to a symptom cache.
- After each selection, the engine generates more related symptoms based on the growing symptom set.
- This continues until the user feels they have said everything they want to share.

#### Step 3: Symptom cache behavior
- The system stores a persistent symptom cache in session memory.
- Each cached symptom should include:
  - label
  - source of discovery
  - timestamp
  - confidence level
- The UI should visually show the growing list of collected symptoms so the user knows the system is building a picture.

#### Step 4: Cause collection phase
- Once the symptom collection is complete, the system transitions to the cause collection stage.
- The chat asks:
  - “What events, stressors, or daily activities do you think may have contributed?”
- The user can enter recent events, exposures, habits, meals, sleep issues, work stress, travel, or anything else they remember.
- The system then presents related causes or contributing factors one at a time, similar to the symptom loop.

#### Step 5: Cause cache behavior
- Each selected cause is added to a causes cache.
- The causes cache should include:
  - label
  - category such as stress, diet, sleep, environment, exposure, routine
  - confidence level
  - timestamp
- The cause list should also be visible in the summary area so the user can review and adjust it.

#### Step 6: Sticky completion button
- A floating or sticky button should remain visible at the bottom of the chat window as the user scrolls.
- The button text should be:
  - “I have said everything I know now — analyze and give me suggestions”
- When clicked, the system should:
  - finalize the symptom and cause caches,
  - run the analysis engine,
  - produce suggestions with explanation and safety notes.

#### Suggested state model
- current_step: greeting | symptom_collection | cause_collection | analysis
- symptom_cache: array of selected symptoms
- cause_cache: array of selected causes
- pending_suggestions: array of related symptoms or causes
- user_profile: age range, pregnancy status, medication history, allergies, chronic conditions

#### Suggested interaction rules
- The user should be able to skip a suggested symptom or cause.
- The user should be able to remove an item from the cache.
- The system should not force the user to complete every suggestion.
- The analysis button should be enabled once the user has entered at least one symptom or one cause.

#### Expected result
- The app collects a structured symptom profile and cause profile from conversation rather than forcing the user into a rigid form.
- This makes the experience feel natural, collaborative, and adaptive.

---

## 13. Safety and Governance Design

This is one of the most important parts of the system.

### Safety rules should include
- contraindications by condition
- interactions with prescription medications
- pregnancy/breastfeeding warnings
- pregnancy-specific restrictions
- age restrictions
- toxicity concerns
- known allergy concerns

### Required UI behavior
- never present a recommendation as definite or guaranteed
- show a prominent disclaimer that the app is informational only
- encourage professional care for serious symptoms

### Recommended governance layer
- maintain an internal review queue for new herb-compound mappings
- require human review for high-risk recommendations
- log every recommendation decision and reason

---

## 14. MVP Scope

### MVP features
- symptom input form
- 10-20 common symptoms in a starter dictionary
- top 3 herb recommendations
- scoring explanation
- basic safety filtering
- evidence source display

### MVP data scope
- 50-100 herbs
- 200-500 compound mappings
- 20-30 symptom categories

---

## 15. Phase 2 Improvements

### Advanced features
- multi-symptom conflict resolution
- personalized profile support
- interaction risk engine
- dietary and lifestyle guidance
- clinician review mode
- explainability dashboard

### Future AI features
- LLM-assisted evidence summarization
- symptom categorization support
- natural-language explanation generation

However, AI should be used as a helper layer, not as the final authority.

---

## 16. Suggested Folder / Project Structure

```text
natural-treatment/
  backend/
    app/
      api/
      models/
      services/
      schemas/
      core/
      workers/
    tests/
  frontend/
    src/
      components/
      pages/
      services/
      styles/
  data/
    seed/
    raw_api_responses/
  docs/
  docker-compose.yml
  README.md
```

---

## 17. Implementation Plan

### Phase 1 — Foundation
- define symptom dictionary
- define herb and compound schema
- implement basic data ingestion layer
- build first scoring engine
- build simple recommendation API

### Phase 2 — MVP UI
- create symptom form
- render ranking results
- display evidence and safety notes

### Phase 3 — Safety and Quality
- add contraindication filters
- add medication interaction checks
- add review workflow for high-risk items

### Phase 4 — Expansion
- support multi-symptom analysis
- improve ranking accuracy
- add personalized history and preference tracking

---

## 18. Example Recommendation Response

```json
{
  "user_symptoms": ["fatigue", "low mood"],
  "top_recommendations": [
    {
      "herb": "Ashwagandha",
      "score": 0.82,
      "confidence_band": "moderate",
      "reason": "Associated with adaptogenic support and stress-related symptom modulation.",
      "evidence_level": "human_observational",
      "safety_note": "Use caution in thyroid disorders and pregnancy."
    },
    {
      "herb": "Maca",
      "score": 0.74,
      "confidence_band": "moderate",
      "reason": "Linked to energy support and nutrient-rich phytochemical content.",
      "evidence_level": "traditional_and_limited_clinical",
      "safety_note": "Use caution with hormone-sensitive conditions."
    }
  ]
}
```

---

## 19. Risks and Mitigations

### Risk: weak evidence
Mitigation: require evidence quality thresholds and down-rank low-evidence recommendations.

### Risk: unsafe advice
Mitigation: strict safety checks and disclaimers.

### Risk: data inconsistency across sources
Mitigation: normalize and curate external data before using it in scoring.

### Risk: over-claiming benefits
Mitigation: limit language to “may support,” “associated with,” and “evidence level.”

---

## 20. Final Recommendation

The best path is to build this as a conservative, evidence-aware recommendation engine rather than a direct treatment engine.

Start with:
- a structured symptom dictionary,
- a curated herb and compound database,
- a simple scoring engine,
- a robust safety filter,
- a transparent explanation layer.

That will give you a strong foundation for a trustworthy product.

---

## 21. Suggested Next Step

The next practical step is to implement a minimal prototype with:
1. a symptom input form,
2. a backend recommendation API,
3. a small seed database of 10-20 herbs and 20-30 symptom mappings,
4. a basic scoring engine.

That MVP will let you validate the concept before expanding the evidence and safety layers.
