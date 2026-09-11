---
name: cftc-agricultural-positioning
description: Generate an English agricultural positioning decision panel from official CFTC Legacy Futures Only Non-Commercial data. Use for CFTC positioning updates, historical extremes, open-interest normalization, change decomposition, and persistence across thirteen agricultural markets. Deliver one validated image per new or revised latest snapshot.
---

# CFTC Agricultural Positioning

Produce one English panel as the only successful user-facing output. Keep data, individual charts, validation evidence, and delivery state internal. Return no commentary with the successful panel. For recurring checks with unchanged data, use the host's silent-completion mechanism. Honor explicit requests for evidence or a different output contract.

## Setup

Resolve this skill's directory from its installation location, never from a previous session path. Use Python 3.10 or newer with this directory's `requirements.txt`. Prefer an existing environment with compatible dependencies; otherwise create a virtual environment. Read [installation.md](references/installation.md) for runtime-specific setup and GitHub installation.

Use an absolute `--state-dir` on persistent writable storage **outside the skill installation**. Reuse it across invocations. Use a separate directory for development or another delivery destination. Do not import another radar's state or reset existing publication history.

## Execute

Run the bundled deterministic code; do not reconstruct its arithmetic in prose:

```bash
python /absolute/skill/scripts/radar.py run --state-dir /absolute/persistent/cftc-radar
```

Interpret stdout as an internal JSON protocol:

- Empty stdout with exit 0: no new edition. Finish silently.
- `READY`: open `panel_path` and inspect legibility, English labels, position and comparison dates, category, units, metrics, and absence of unsupported causes or price targets. Inspect `validation.json` in `evidence_directory`. Use `delivery_idempotency_key` for the host's durable, deduplicated delivery.
- Nonzero exit: preserve the previous valid edition. Send the structured stderr error to operational monitoring, deduplicated by `failure_signature`. If no monitoring channel exists, report the limitation plainly; never invent a panel or silently present old data as new.

Retain the complete evidence directory durably. Deliver **only the panel image** using the host's attachment/rendering capability. Record confirmed delivery separately:

```bash
python /absolute/skill/scripts/radar.py ack \
  --state-dir /absolute/persistent/cftc-radar \
  --edition-id EDITION_ID_FROM_READY \
  --delivery-receipt HOST_CONFIRMED_RECEIPT
```

A generated file or planned final response is not confirmed delivery. If the host cannot run a post-delivery acknowledgement, leave the edition pending until its delivery or durable outbox receipt can be verified. Read [operations.md](references/operations.md) before configuring recurring delivery. The skill itself does not create a schedule or call a messaging service.

## Preserve the analytical contract

Use only public CFTC dataset `6dca-aqww`, Legacy Futures Only, Non-Commercial, and the thirteen bundled market codes. Never substitute Managed Money, Combined, prices, other vendors, or image estimates. Plot longs positively and shorts negatively; net equals source longs minus source positive shorts. Preserve spreading separately. Do not sum contracts across commodities or convert them to dollars.

Keep the four deterministic measures: prior-five-year net percentile excluding the current observation; signed net / open interest; change in longs and minus change in shorts; consecutive directional net changes. Read [methodology.md](references/methodology.md) for definitions, coverage rules, and source links. Describe review scenarios, not trading recommendations or proven causes.

Treat the position date separately from the publication date. The API maximum alone does not prove that the latest scheduled release has arrived. Use the official release calendar when explaining a delay. Never depend on the legacy TXT endpoint.

## Reproduce or maintain

For an explicitly requested offline reproduction, use `radar.py render --input SAVED_CFTC_JSON --output EMPTY_DIRECTORY`. It labels the panel offline and never changes publication state. Do not use synthetic test fixtures as market observations.

Before modifying calculations or delivery behavior, run:

```bash
python -m unittest discover -s /absolute/skill/scripts -p 'test_*.py' -v
```

Inspect a rendered panel after layout changes. Preserve the independent unit tests, all-row contract validation, raw source snapshot, canonical fingerprint, source query, retrieval timestamp, and artifact hashes. Increment `EDITION_VERSION` after changes that require previously delivered source data to be rendered again.
