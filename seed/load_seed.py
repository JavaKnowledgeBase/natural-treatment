"""Loads the immutable starter seed bundle into the Tier 1 reference cache.

This stands in for the offline curation job described in the design doc
(application_design_v2 §2.1): in a real deployment this data would be
produced by a scheduled batch job querying IMPPAT/ChEBI/PubChem/CTD and
published as a versioned artifact. For phase 1 it is a hand-curated starter
dataset read from seed/data/*.json.

Idempotent and cheap -- safe to call from every knowledge service's startup
hook rather than requiring strict container start ordering.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

from shared import cache

SEED_DIR = Path(os.environ.get("SEED_DATA_DIR", Path(__file__).parent / "data"))


def _read(name: str) -> list[dict]:
    return json.loads((SEED_DIR / name).read_text(encoding="utf-8"))


async def load_seed() -> str:
    herbs = _read("herbs.json")
    compounds = _read("compounds.json")
    symptoms = _read("symptoms.json")
    rules = _read("rules.json")

    for herb in herbs:
        await cache.set_ref("herb", herb["id"], herb)
    for compound in compounds:
        await cache.set_ref("compound", compound["id"], compound)
    for symptom in symptoms:
        await cache.set_ref("symptom", symptom["id"], symptom)
    for rule in rules:
        await cache.set_ref("rule", rule["id"], rule)

    fingerprint = json.dumps([herbs, compounds, symptoms, rules], sort_keys=True).encode("utf-8")
    version = "starter-" + hashlib.sha256(fingerprint).hexdigest()[:12]
    await cache.set_kb_version(version)
    return version


if __name__ == "__main__":
    import asyncio

    loaded_version = asyncio.run(load_seed())
    print(f"Seed loaded into Tier 1 cache. kb_version={loaded_version}")
