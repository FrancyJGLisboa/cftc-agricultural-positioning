# Runtime and delivery integration

## Internal protocol

`radar.py run --state-dir PATH` returns exit 0 with either empty stdout (unchanged) or one READY JSON object. Parse JSON; do not scrape prose. Use its `panel_path` as the sole successful user-facing artifact. Evidence files are internal by default.

READY includes an edition ID, source reference date, absolute image path, image SHA-256, evidence directory, and delivery idempotency key. Persist evidence on durable storage, verify the image, then use the host's delivery mechanism. Call `ack` only after a confirmed delivery or a durable outbox receipt that guarantees retry. Never acknowledge merely because a render succeeded.

The pending edition is returned unchanged on retries. It is drained before checking for another edition. This preserves recovery after failed delivery. Delivery can be delayed while a pending edition awaits acknowledgement. Do not label it the newest scheduled publication without checking the calendar and source.

## Scheduling and concurrency

Have cron, a CI runner, or the agent host invoke `run` hourly or on another authorized schedule. The command does not send messages. Avoid automatic acknowledgement in a bare cron job: a delivery adapter must actually handle the image first. Do not promise instantaneous release delivery.

Use one delivery dispatcher per state directory. The filesystem lock serializes prepare and ack operations, but does not cover external delivery. For crash-safe duplicate suppression, the destination must honor the returned idempotency key. Without destination-side deduplication, exactly-once external delivery cannot be guaranteed across a crash between sending and acknowledging; document that limitation. Multiple machines need shared durable storage with reliable exclusive file creation and atomic rename, plus a single dispatcher, or an external transactional adapter.

A crashed process may leave `.run.lock`. Confirm the process has stopped before removing that lock; never automatically steal it based only on age. Keep state and edition folders together in backups. Do not store runtime state in a public GitHub repository or the installed skill directory.

## Errors

Errors return exit 1 and a JSON stderr record containing `failure_signature`. The operational adapter should persist and deduplicate notifications by signature; a new failure signature warrants a new operational notification. A successful check clears that adapter's active failure. The CLI itself does not send or deduplicate external error notifications.

Source regression, incomplete latest coverage, malformed data, rendering failure, corrupt state, or artifact hash mismatch must not advance the publication marker. Never suppress an error by resetting state. Missing state alongside existing editions is an error. An empty directory is a new independent deployment, not recovery of a lost deployment.

## Files retained for each edition

- One decision panel and thirteen individual PNG charts.
- `cftc-source.json`: original selected CFTC fields and quantities.
- `history.csv`, `latest-report.csv`: organized positions and four metrics.
- `diagnostics.json`, `highlights.json`: deterministic English observations.
- `validation.json`: source query, retrieval time, raw-download hash, canonical latest fingerprint, validation checks, and artifact hashes.

State keeps a pending record, last acknowledged publication, and an append-only event log. Atomic file replacement is used for writes. Edition files are immutable after preparation and verified again before acknowledgement. No user account IDs, private storage IDs, prior production state, or previously retrieved market snapshots ship with the skill.

## Hosts without native skills

Load `SKILL.md` as task instructions, permit execution of the Python entry point, and implement the JSON/delivery protocol above. The analytical engine needs neither an LLM nor a specific agent SDK. The agent handles source-aware explanation when needed and visual review; arithmetic and state transitions stay in Python.
