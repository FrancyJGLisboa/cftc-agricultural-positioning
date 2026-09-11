# Runtime and delivery integration

## Internal protocol

`radar.py run --state-dir PATH` returns exit 0 with either empty stdout (unchanged) or one READY JSON object. Parse JSON; do not scrape prose. The successful output is an automatically displayed PNG panel with a **Download PDF** link immediately below it. Use `panel_path` and `pdf_path` from the same edition. Other evidence files remain internal.

READY includes an edition ID, source reference date, absolute `panel_path` and `pdf_path`, separate SHA-256 hashes, evidence directory, delivery idempotency key, and a `presentation` object. `presentation.layout` is `image_then_pdf_link`; its ordered items describe the image and PDF download, with MIME types, image alt text, and the label `Download PDF`. `automatic_display: true` is a requirement for the host adapter, not proof of a completed display.

Persist evidence, inspect the matching outputs, and map both local paths to user-accessible attachments or URLs. Render the PNG inline and the PDF link directly beneath it as one ordered response, with no surrounding or intervening commentary. Do this without an additional user prompt. Markdown-capable hosts should emit an image embed followed by a blank line and the PDF link; never a fenced block or an image hyperlink without the image embed. A PDF attachment may render as a download card when that is the host's supported format.

VS Code integrations should use a supported editor preview/open operation if their chat cannot display the PNG. A CLI integration must supply a viewer if it promises automatic display. The Python command deliberately performs no GUI launch or browser installation: rendering files is portable; presentation is host-specific. Do not assume one host's attachment URI format works in another. If no supported display operation exists, provide accessible links and state that automatic display is unavailable, without acknowledging the pair as delivered.

Call `ack` only after confirmed delivery of both items or a durable outbox receipt guaranteeing ordered retry of the complete pair. Use one idempotency key for the pair; if the destination requires per-item IDs, derive stable `:panel` and `:pdf` suffixes from it. A failed PDF upload/link must leave the edition pending even if the image is already visible. Never acknowledge merely because a render or internal inspection succeeded.

The pending edition is returned unchanged on retries. It is drained before checking for another edition. This preserves recovery after failed delivery. Delivery can be delayed while a pending edition awaits acknowledgement. Do not label it the newest scheduled publication without checking the calendar and source.

## Upgrading existing state

English edition version 2.0.0 adds report modes, extended analytics and seasonal views. A previously acknowledged 1.x snapshot is eligible for one new edition even if the source is unchanged. Normal silent checks resume after the pair is acknowledged.

A pending 1.0.0 or 1.1.0 Legacy edition is verified and rebuilt from its retained `cftc-source.json` before any new network collection. Its original folder is retained unchanged; the replacement has a new edition/idempotency key and records `supersedes_pending_edition` in the event log. A failed rebuild leaves the original state and pending edition intact. Missing or corrupt source evidence requires restoration; never discard publication history. Current-version pending editions missing either output fail verification instead of being delivered partially.

State configuration binds a destination to `report`, `unit` and optional `market`. Omitted CLI options reuse the binding. State without configuration is a Legacy/contracts/summary destination. New CLI state defaults to Managed Money/contracts/summary. A mismatch fails before collection or state writes; use a separate persistent directory for a different view. Never reset existing history to enable a new report mode. Internal Python functions retain their Legacy defaults for compatibility; the CLI performs new-state Managed Money selection.

Examples (use absolute installed paths in an agent invocation):

```bash
python scripts/radar.py run --state-dir /persistent/cftc-mm --report managed-money
python scripts/radar.py run --state-dir /persistent/cftc-mm-mmt --report managed-money --unit mmt
python scripts/radar.py run --state-dir /persistent/cftc-corn-detail --report managed-money --market 002602 --unit pct-oi
python scripts/radar.py run --state-dir /persistent/cftc-legacy --report legacy
python scripts/radar.py render --input /saved/cftc-source.json --output /empty/corn --report managed-money --market 002602 --unit mmt
```

For a detail request using already retained evidence, prefer offline `render` with the matching report, unit and market over creating a recurring destination. It returns the same ordered PNG/PDF presentation with an OFFLINE label.

## Scheduling and concurrency

Have cron, a CI runner, or the agent host invoke `run` hourly or on another authorized schedule. The command does not send messages. Avoid automatic acknowledgement in a bare cron job: a delivery adapter must actually handle the image and PDF link first. Do not promise instantaneous release delivery.

Use one delivery dispatcher per state directory. The filesystem lock serializes prepare and ack operations, but does not cover external delivery. For crash-safe duplicate suppression, the destination must honor the returned idempotency key. Without destination-side deduplication, exactly-once external delivery cannot be guaranteed across a crash between sending and acknowledging; document that limitation. Multiple machines need shared durable storage with reliable exclusive file creation and atomic rename, plus a single dispatcher, or an external transactional adapter.

A crashed process may leave `.run.lock`. Confirm the process has stopped before removing that lock; never automatically steal it based only on age. Keep state and edition folders together in backups. Do not store runtime state in a public GitHub repository or the installed skill directory.

## Errors

Errors return exit 1 and a JSON stderr record containing `failure_signature`. The operational adapter should persist and deduplicate notifications by signature; a new failure signature warrants a new operational notification. A successful check clears that adapter's active failure. The CLI itself does not send or deduplicate external error notifications.

Source regression, incomplete latest coverage, malformed data, rendering failure, corrupt state, or artifact hash mismatch must not advance the publication marker. Never suppress an error by resetting state. Missing state alongside existing editions is an error. An empty directory is a new independent deployment, not recovery of a lost deployment.

## Files retained for each edition

- One decision panel in PNG and matching one-page PDF, exported from the same Matplotlib figure with no new runtime dependency.
- Thirteen commodity detail pages, each a matching PNG/PDF pair, retained internally. A selected detail page becomes the canonical displayed pair.
- `cftc-source.json`: original selected CFTC fields and quantities.
- `history.csv`, `latest-report.csv`: organized positions, conversions, extended metrics, comparison dates and coverage status.
- `seasonality.json`: year windows, bin alignment, reference counts, curves and observation dates.
- `diagnostics.json`, `highlights.json`: deterministic English observations.
- `validation.json`: source query, retrieval time, raw-download hash, canonical latest fingerprint, validation checks, and artifact hashes.

State keeps a pending record, last acknowledged publication, and an append-only event log. Atomic file replacement is used for writes. Edition files are immutable after preparation and verified again before acknowledgement. No user account IDs, private storage IDs, prior production state, or previously retrieved market snapshots ship with the skill.

## Hosts without native skills

Load `SKILL.md` as task instructions, permit execution of the Python entry point, and implement the JSON/delivery protocol above. The analytical engine needs neither an LLM nor a specific agent SDK. The agent handles source-aware explanation when needed and visual review; arithmetic and state transitions stay in Python.
