---
name: cftc-agricultural-positioning
description: Generate English agricultural positioning panels from official CFTC Managed Money or Legacy Non-Commercial futures-only data. Use for weekly tables, historical extremes, seasonality, physical equivalents, open-interest normalization, change decomposition, and persistence across thirteen agricultural markets. Automatically display the validated panel with a PDF download immediately underneath for each new or revised latest snapshot.
---

# CFTC Agricultural Positioning

Automatically display one English panel image, followed immediately underneath by a **Download PDF** link to the matching one-page report. This ordered pair is the entire successful user-facing output; no introduction, summary, or intervening text. Keep data, individual charts, validation evidence, and delivery state internal. For recurring checks with unchanged data, use the host's silent-completion mechanism. Honor explicit requests for evidence or a different output contract.

## Setup

Resolve this skill's directory from its installation location, never from a previous session path. Use Python 3.10 or newer with this directory's `requirements.txt`. Prefer an existing approved environment with compatible dependencies; create a virtual environment only where package installation is permitted. Read [installation.md](references/installation.md) for manual VS Code/Copilot installation without Node.js or npx, corporate Python setup, and other runtime installation paths. The copy step does not install Python dependencies.

Use an absolute `--state-dir` on persistent writable storage **outside the skill installation**. Reuse it across invocations. Use a separate directory for development or another delivery destination. Do not import another radar's state or reset existing publication history.

## Select the view

Use Managed Money for a new destination unless the user requests Legacy Non-Commercial. Existing state directories retain their category, units and summary/detail view. Do not silently switch categories or reuse another view's publication history. Use a distinct persistent state directory for each report/unit/market combination.

- `--report managed-money`: Disaggregated Futures Only, dataset `72hh-3qpy`.
- `--report legacy`: Legacy Futures Only, dataset `6dca-aqww`.
- `--unit contracts` (default), `--unit mmt` (million metric tonnes of physical equivalent), or `--unit pct-oi`.
- `--market CODE`: automatically display that commodity's detail page, with the matching PDF directly below it. Omit for the thirteen-market summary. Find codes in [methodology.md](references/methodology.md).

Omitted options on `run` reuse the existing destination's settings. For a saved snapshot, `render` defaults to Managed Money; specify `--report legacy` for Legacy evidence. A category mismatch fails validation rather than substituting data.

## Execute

Run the bundled deterministic code; do not reconstruct its arithmetic in prose:

```bash
python /absolute/skill/scripts/radar.py run --state-dir /absolute/persistent/cftc-radar
```

Interpret stdout as an internal JSON protocol:

- Empty stdout with exit 0: no new edition. Finish silently.
- `READY`: open `panel_path` and inspect legibility, English labels, position and comparison dates, category, units, metrics, and absence of unsupported causes or price targets. Check that `pdf_path` is the matching one-page panel, and inspect `validation.json` in `evidence_directory`. Both files must be intact before delivery. Use `delivery_idempotency_key` for the host's durable, deduplicated delivery.
- Nonzero exit: preserve the previous valid edition. Send the structured stderr error to operational monitoring, deduplicated by `failure_signature`. If no monitoring channel exists, report the limitation plainly; never invent a panel or silently present old data as new.

Retain the complete evidence directory durably. Complete the display step in the same invocation; do not ask whether the user wants to see the result. Follow the ordered `presentation.items`: first render `panel_path` visibly, then place the `pdf_path` download link directly underneath, labeled **Download PDF**. Upload or attach both files using the host's supported mechanism and use its returned user-accessible targets. An image link alone, raw JSON, a filesystem path, or an inspection-tool result is not the requested display.

For Markdown-capable hosts, the final response must have this structure (substitute the actual host-provided targets; do not output this as a code block):

```markdown
![CFTC Agricultural Positioning](IMAGE_TARGET)

[Download PDF](PDF_TARGET)
```

In VS Code, use the available editor/preview integration if chat cannot render the image. A terminal-only host may need its configured graphical viewer. Never install a viewer or bypass permissions automatically. If the host provides no supported display operation, return accessible PNG/PDF links with a brief display limitation and keep delivery pending; do not claim automatic rendering succeeded. Read [operations.md](references/operations.md) for host integration and upgrade behavior.

Record confirmed delivery of **both** items separately:

```bash
python /absolute/skill/scripts/radar.py ack \
  --state-dir /absolute/persistent/cftc-radar \
  --edition-id EDITION_ID_FROM_READY \
  --delivery-receipt HOST_CONFIRMED_RECEIPT
```

Generated files, opening an image for internal inspection, or a planned final response are not confirmed delivery of the pair. If the host cannot run a post-delivery acknowledgement, leave the edition pending until its delivery or durable outbox receipt can be verified. Read [operations.md](references/operations.md) before configuring recurring delivery. The skill itself does not create a schedule or call a messaging service.

## Preserve the analytical contract

Use only the selected official CFTC futures-only dataset and the thirteen bundled market codes. Keep Managed Money and Legacy Non-Commercial histories separate. Never substitute Combined, prices, other vendors or image estimates. Plot longs positively and shorts negatively; net equals source longs minus source positive shorts. Preserve spreading separately. Do not sum contracts or physical equivalents across commodities, estimate dollars or label positioning changes as cash flows.

Use only the bundled physical conversion registry after matching each row's official `contract_units`. Unknown or changed units block MMT rendering; never guess a replacement factor. MMT means physical equivalent, not inventory, delivery commitments or actual investment. Conversion by a constant does not change a percentile or the shape of a series.

Keep the four deterministic measures: prior-five-year net percentile excluding the current observation; signed net / open interest; change in longs and minus change in shorts; consecutive directional net changes. Read [methodology.md](references/methodology.md) for definitions, coverage rules, and source links. Add open-interest changes, exact-calendar 4/13-week net changes, five-year minimum/maximum net and their dates, and seasonal net curves. The table keeps OI and extrema in contracts even when another display unit is selected. Percent-of-OI changes are percentage-point differences; they are not contract changes divided by OI. Seasonal bands use the prior five calendar years and require at least three available years per bin. Missing comparisons remain N/A, without interpolation. Describe review scenarios, not trading recommendations or proven causes.

Treat the position date separately from the publication date. The API maximum alone does not prove that the latest scheduled release has arrived. Use the official release calendar when explaining a delay. Never depend on the legacy TXT endpoint.

## Reproduce or maintain

For an explicitly requested offline reproduction, use `radar.py render --input SAVED_CFTC_JSON --output EMPTY_DIRECTORY --report managed-money`. It labels the panel offline and never changes publication state. Do not use synthetic test fixtures as market observations.

Before modifying calculations or delivery behavior, run:

```bash
python -m unittest discover -s /absolute/skill/scripts -p 'test_*.py' -v
```

Inspect a rendered panel after layout changes. Preserve the independent unit tests, all-row contract validation, raw source snapshot, canonical fingerprint, source query, retrieval timestamp, and artifact hashes. Increment `EDITION_VERSION` after changes that require previously delivered source data to be rendered again.
