# Herb Dataset Expansion Plan — target: ~100 herbs in 3 days

Written 2026-07-23. Goal, from the user directly: this needs to become a
genuinely resourceful, trustworthy information source — not a padded
number — with real emphasis on being familiar/useful to people in India
and China specifically. Honesty up front: "3 days" and "all possible
searches" is being interpreted as *100 herbs at the same PubMed/NCBI-tier
rigor already established*, not hundreds at lower rigor. That tradeoff
was discussed and agreed on 2026-07-23 — see `CLAUDE.md`'s open items for
the full reasoning (web search ≠ primary-literature access; a real
"hundreds" push needs WHO monographs / national pharmacopoeias / expert
review this session doesn't have).

**Current state (2026-07-23, end of session 2): 43 herbs, 32 symptoms.**

## Priority 1 — zero-coverage symptoms (fix before adding anything else)

Checked linked_symptoms coverage across all 43 herbs. These 6 categories
exist in the catalog but have **no herb at all** — a user reporting any
of these gets nothing:

- `acid_reflux`
- `loss_of_appetite`
- `diarrhea`
- `acne`
- `nasal_congestion`
- `frequent_urination`

Next session should open here, not with a fresh symptom-agnostic herb
list. Candidates worth researching first (not yet vetted):
- Acid reflux: DGL licorice (deglycyrrhizinated licorice, distinct entry
  from `licorice_root` given DGL specifically removes the glycyrrhizin
  that causes licorice's hypertension risk — genuinely different safety
  profile, worth its own entry), slippery elm (Ulmus rubra)
- Loss of appetite: gentian root (Gentiana lutea), Ayurvedic candidates
  like pippali (Piper longum)
- Diarrhea: bilberry (Vaccinium myrtillus, tannin-based), Ayurvedic
  kutaja (Holarrhena antidysenterica)
- Acne: TCM honeysuckle (Jin Yin Hua / Lonicera japonica), niaouli or
  tea tree (topical, real antimicrobial evidence) — check both traditions
- Nasal congestion: TCM xanthium/magnolia flower combinations, or
  eyebright (Euphrasia) — check evidence quality carefully, this one has
  a lot of low-quality traditional-only sourcing to watch for
- Frequent urination: TCM cornus/eucommia-pattern herbs, Ayurvedic
  gokshura (Tribulus terrestris) — note gokshura also has real
  testosterone/hormone-claim overreach in low-quality sources, vet
  carefully

## Priority 2 — round out remaining thin categories (1-2 herbs each)

`hair_loss`(1), `low_libido`(1), `blood_sugar_imbalance`(1),
`chronic_headaches`(2), `muscle_tension`(2), `nausea`(2),
`occasional_constipation`(2), `menopausal_symptoms`(2),
`memory_lapses`(2), `water_retention`(2)

## Priority 3 — broaden Ayurvedic coverage (candidates, unresearched)

Haritaki, Bibhitaki, Amalaki (the 3 Triphala fruits — worth adding
individually now, unlike the Triphala formula itself which doesn't fit
the single-species schema), Manjistha (Rubia cordifolia), Jatamansi
(Nardostachys jatamansi), Shankhpushpi (Convolvulus pluricaulis), Bala
(Sida cordifolia), Kapikacchu (Mucuna pruriens), Bitter melon
(Momordica charantia), Moringa (Moringa oleifera), Vasaka (Adhatoda
vasica), Kalmegh (Andrographis paniculata), Pippali (Piper longum),
Vidanga, Musta (Cyperus rotundus), Gokshura (Tribulus terrestris —
vet hormone-claim overreach carefully), Sandalwood (Santalum album)

## Priority 4 — broaden TCM coverage (candidates, unresearched)

Cinnamon (Cinnamomum cassia), Rehmannia (Rehmannia glutinosa), White
peony (Paeonia lactiflora), Codonopsis (Dang Shen), Atractylodes (Bai
Zhu), Chrysanthemum (Ju Hua), Honeysuckle (Lonicera japonica),
Forsythia (Forsythia suspensa), Mulberry leaf (Morus alba), Eucommia
bark (Eucommia ulmoides), Coptis (Coptis chinensis — note: real
documented interactions, check carefully like Bupleurum/He Shou Wu),
Scutellaria (Scutellaria baicalensis), Platycodon (Platycodon
grandiflorus), Ophiopogon (Ophiopogon japonicus), Ziziphus seed
(Ziziphus jujuba var. spinosa), Notoginseng (Panax notoginseng),
Safflower (Carthamus tinctorius)

That's ~33 more candidates across priorities 3-4, plus ~10-12 across
priorities 1-2 — comfortably more than the ~57 needed to reach 100,
giving room to drop any that turn out to have weak/contradictory
evidence during research rather than forcing a bad entry in to hit a
number.

## Methodology (same as session 2, don't skip steps to go faster)

For each herb:
1. WebSearch: `"<Latin name>" <primary indication> clinical trial evidence contraindications` — batch 4-6 herbs per message (parallel tool calls), not one at a time
2. Classify `evidence_level` honestly from what the search actually shows
   — real RCTs/meta-analyses → `clinical_trial`; small/mixed/limited
   human data → `human_observational`; traditional use + some non-human
   data → `traditional_and_limited_clinical`; traditional use only, no
   real efficacy backing → `anecdotal_traditional`
3. **Contraindications must map onto `SafetyService.java`'s actual
   `CONDITION_KEYWORDS` vocabulary** (`services/agents/safety/.../
   SafetyService.java`) or they're silently non-functional — check the
   current list before writing `rules.json` entries. Extend the
   vocabulary (like `liver_disease` this session) only when a real,
   repeated safety signal justifies a new category, not per-herb.
4. Any herb with a real, documented serious safety signal (hepatotoxicity,
   etc.) gets that flagged prominently in `common_use` text itself, not
   just buried in a rules.json note.
5. New compound entries: leave `formula`/`pubchem_id` null unless
   genuinely confident, same standard as session 2.

## Deployment checklist per batch (don't batch this to the very end)

1. Validate JSON (`python -c "import json; json.load(open(...))"` on all
   3 files)
2. **Rebuild** `seed-loader` before running it locally — it bakes
   `seed/data/*.json` in at build time via `COPY`, a bare `run --rm`
   reuses the old image silently (real bug hit in session 2)
3. If `SafetyService.java` changed: rebuild + restart `agent-safety`
4. **Restart `agent-intake` and `agent-mapping`** after any reseed —
   both cache the symptom catalog in a module-level Python variable with
   no TTL (`_catalog_cache` in `services/agents/intake/main.py`);
   reseeding Redis alone does not update what they see (real bug hit in
   session 2, cost a full debugging round)
5. Test live: at least one full session (message -> advance -> analyze)
   exercising a newly-added symptom, plus a direct `agent-safety`
   `/safety/evaluate` call for any herb with a new/serious contraindication
6. Commit with real rationale (not just "add herbs")
7. Deploy to prod: `git archive` + `scp` (GitHub push still broken as of
   session 2 — check `docs/DEPLOYMENT.md` §9 to see if that's been fixed
   since), rebuild only the changed services, reseed, restart
   intake/mapping there too, re-verify against the live domain

## Progress log

- **2026-07-23, session 2**: 18 → 43 herbs, 20 → 32 symptoms. Full
  detail in `CLAUDE.md`'s open items and `git log`.
