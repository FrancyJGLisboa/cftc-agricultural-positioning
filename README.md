# CFTC Agricultural Positioning

An English Agent Skill that turns official CFTC agricultural positioning into one decision panel.

The final successful user-facing output is **one PNG image**. A recurring check with no new or revised latest snapshot stays silent. Data, detailed charts, validation receipts, and delivery state remain internal unless requested.

## Install in VS Code without Node.js or npx

With GitHub Copilot in VS Code, installation is a folder copy:

1. On [GitHub](https://github.com/FrancyJGLisboa/cftc-agricultural-positioning), select **Code > Download ZIP** and extract it, or obtain an internally approved copy.
2. Copy the complete `skills/cftc-agricultural-positioning` folder into `<your-project>/.github/skills/`.
3. Open that project in VS Code. In Copilot Chat, type `/` and select `cftc-agricultural-positioning`.
4. Use an approved Python environment with the dependencies below before requesting a live panel.

The resulting entrypoint is `.github/skills/cftc-agricultural-positioning/SKILL.md`. No Node.js, npm, npx, Git, or administrator rights are needed for the folder copy into a writable project. An organization-approved VS Code/Copilot version with Agent Skills support is required; see the [official VS Code documentation](https://code.visualstudio.com/docs/agent-customization/agent-skills).

**Running the analysis still requires Python 3.10+, matplotlib, numpy, and HTTPS access to publicreporting.cftc.gov.** Use existing approved dependencies or your organization's environment provisioning process. Copying the folder does not install Python packages or provision a remote runner.

See the [installation guide](skills/cftc-agricultural-positioning/references/installation.md) for Windows paths, personal Copilot installation, the optional Python copy helper, corporate environment setup, and other runtimes.

If npm package execution is permitted, the Agent Skills CLI remains optional:

```bash
npx skills add FrancyJGLisboa/cftc-agricultural-positioning --skill cftc-agricultural-positioning
```

The skill follows the [Agent Skills specification](https://agentskills.io/specification). Runtime compatibility is based on supported installation paths, not end-to-end certification on every host.

## What the panel measures

- Historical net-position percentile over the preceding five calendar years.
- Net positioning as a signed percentage of open interest.
- Net change decomposed into changes in longs and shorts.
- Persistence of consecutive increases or decreases in net positioning.

Coverage: corn, soybeans, Chicago SRW wheat, Kansas HRW wheat, soybean meal, soybean oil, live cattle, lean hogs, feeder cattle, cotton No. 2, sugar No. 11, coffee C, and cocoa.

Source: official CFTC dataset `6dca-aqww`, Legacy Futures Only, Non-Commercial. No Managed Money substitution, prices, dollar conversion, cross-commodity contract totals, or private data providers. Spreading stays separate. Read the [methodology](skills/cftc-agricultural-positioning/references/methodology.md).

## Run directly

Requires Python 3.10+ and outbound access to publicreporting.cftc.gov. No API key is required. The example below creates an environment and installs packages only where permitted. With an approved compatible environment, use its Python executable directly and skip those setup steps. For a manually installed skill, use its installed path instead of `skills/`.

```bash
python -m venv .venv
.venv/bin/python -m pip install -r skills/cftc-agricultural-positioning/requirements.txt
.venv/bin/python skills/cftc-agricultural-positioning/scripts/radar.py run --state-dir ./radar-state
```

On Windows, use `.venv\Scripts\python.exe` in place of `.venv/bin/python`.

An unchanged check prints nothing and exits successfully. A new edition prints internal READY JSON with the panel path, evidence directory, and delivery idempotency key. Inspect the panel and hand it to the host's durable delivery mechanism. Only after confirmation, call:

```bash
.venv/bin/python skills/cftc-agricultural-positioning/scripts/radar.py ack --state-dir ./radar-state --edition-id ID_FROM_READY --delivery-receipt CONFIRMED_HOST_RECEIPT
```

The code does not infer delivery from a generated file. A pending edition is safely retried. The host must supply actual image delivery, scheduling, and operational notifications. A single dispatcher and destination-side idempotency are required for reliable duplicate suppression across crashes. See [operations](skills/cftc-agricultural-positioning/references/operations.md).

To ask an agent: **Use cftc-agricultural-positioning to update the agricultural radar. Return only the validated panel.**

## Development

```bash
python -m unittest discover -s skills/cftc-agricultural-positioning/scripts -p 'test_*.py' -v
```

Tests use synthetic records, not market evidence. Collection additionally validates all source rows, complete latest coverage, integer counts, open-interest identities, and decomposition. CI exercises supported Python versions on Linux and Windows. Runtime state and retrieved market data are excluded from this repository.

Reproduce an official saved snapshot without publishing:

```bash
python skills/cftc-agricultural-positioning/scripts/radar.py render --input /path/to/cftc-source.json --output /path/to/empty-output-directory
```

The image is explicitly labeled offline. Position dates differ from release dates. Descriptive extremes do not predict returns or prove causes.
