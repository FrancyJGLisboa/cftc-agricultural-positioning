#!/usr/bin/env python3
"""Export this installed skill as a clean GitHub-ready repository tree."""
import argparse
from pathlib import Path
import shutil

NAME = 'cftc-agricultural-positioning'
README = '''# CFTC Agricultural Positioning

An English Agent Skill that turns official CFTC agricultural positioning into one decision panel.

The final successful user-facing output is **the panel displayed automatically, with a Download PDF link immediately underneath**. The PNG and matching one-page PDF come from the same Matplotlib figure, with no new runtime dependency. A recurring check with no new or revised latest snapshot stays silent. Data, detailed charts, validation receipts, and delivery state remain internal unless requested.

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

## What version 2.0 adds

New destinations default to Disaggregated Managed Money; existing Legacy destinations keep their category. Use separate state directories for distinct report/unit/market combinations.

- Expanded weekly table: open interest, OI change, net and previous/4/13-week changes.
- Five-year minimum/maximum net positions with dates and explicit history windows.
- Seasonal net charts: current year, previous year, and prior-five-calendar-year median/range.
- Display net in contracts, million metric tonnes of physical equivalent, or percent of open interest.
- One-page commodity details with seasonal charts, history and decomposition.

## Core diagnostics

- Historical net-position percentile over the preceding five calendar years.
- Net positioning as a signed percentage of open interest.
- Net change decomposed into changes in longs and shorts.
- Persistence of consecutive increases or decreases in net positioning.

Coverage: corn, soybeans, Chicago SRW wheat, Kansas HRW wheat, soybean meal, soybean oil, live cattle, lean hogs, feeder cattle, cotton No. 2, sugar No. 11, coffee C, and cocoa.

Sources: official CFTC `72hh-3qpy` (Disaggregated Futures Only, Managed Money) or `6dca-aqww` (Legacy Futures Only, Non-Commercial). Categories never mix. No prices, dollar conversion, cash-flow estimates, cross-commodity totals or private providers. Spreading stays separate. Read the [methodology](skills/cftc-agricultural-positioning/references/methodology.md).

## Run directly

Requires Python 3.10+ and outbound access to publicreporting.cftc.gov. No API key is required. The example below creates an environment and installs packages only where permitted. With an approved compatible environment, use its Python executable directly and skip those setup steps. For a manually installed skill, use its installed path instead of `skills/`.

```bash
python -m venv .venv
.venv/bin/python -m pip install -r skills/cftc-agricultural-positioning/requirements.txt
.venv/bin/python skills/cftc-agricultural-positioning/scripts/radar.py run --state-dir ./radar-state
```

On Windows, use `.venv\\Scripts\\python.exe` in place of `.venv/bin/python`.

An unchanged check prints nothing and exits successfully. A new edition prints internal READY JSON with PNG/PDF paths and hashes, ordered presentation instructions, evidence directory, and delivery idempotency key. Inspect both outputs and use the host's rendering capability to display the panel and PDF link in that order. File generation alone does not display the report. Only after confirmation of the complete pair, call:

```bash
.venv/bin/python skills/cftc-agricultural-positioning/scripts/radar.py ack --state-dir ./radar-state --edition-id ID_FROM_READY --delivery-receipt CONFIRMED_HOST_RECEIPT
```

The code does not infer delivery from a generated file. A pending edition is safely retried. The host must supply actual panel display and PDF-link delivery, scheduling, and operational notifications. Hosts without a supported image display operation must expose accessible links and report that limitation; they must not claim automatic rendering succeeded. A single dispatcher and destination-side idempotency are required for reliable duplicate suppression across crashes. See [operations](skills/cftc-agricultural-positioning/references/operations.md).

To ask an agent: **Use cftc-agricultural-positioning to update the agricultural radar. Automatically display the validated panel with a Download PDF link immediately underneath.**

## Views

```bash
python skills/cftc-agricultural-positioning/scripts/radar.py run --state-dir ./mm-state --report managed-money
python skills/cftc-agricultural-positioning/scripts/radar.py run --state-dir ./mm-mmt-state --report managed-money --unit mmt
python skills/cftc-agricultural-positioning/scripts/radar.py run --state-dir ./corn-state --report managed-money --market 002602 --unit pct-oi
python skills/cftc-agricultural-positioning/scripts/radar.py run --state-dir ./legacy-state --report legacy
```

Ask naturally: **Show Managed Money positioning in million metric tonnes**, or **Show the corn detail with seasonal positioning as a percentage of open interest**. Supply a separate persistent state directory for each view. Subsequent `run` calls may omit view options to reuse the saved configuration.

MMT is a physical equivalent, not money invested or deliverable inventory. Conversion requires recognized official contract units. Percentage-of-OI changes are differences in percentage points. The table keeps open interest and extrema in contracts. Four- and thirteen-week comparisons use exact calendar dates; missing dates or intervening gaps give N/A. Seasonal bands require at least three of the preceding five calendar years per bin, without interpolation.

## Development

```bash
python -m unittest discover -s skills/cftc-agricultural-positioning/scripts -p 'test_*.py' -v
```

Tests use synthetic records, not market evidence. Collection additionally validates all source rows, complete latest coverage, integer counts, open-interest identities, and decomposition. CI exercises supported Python versions on Linux and Windows. Runtime state and retrieved market data are excluded from this repository.

Reproduce an official saved snapshot without publishing:

```bash
python skills/cftc-agricultural-positioning/scripts/radar.py render --input /path/to/cftc-source.json --output /path/to/empty-output-directory --report managed-money
```

Use `--report legacy` for saved Legacy data. Both outputs are explicitly labeled offline. Position dates differ from release dates. Descriptive extremes do not predict returns or prove causes.
'''
CI = '''name: Validate skill
on: [push, pull_request, workflow_dispatch]
permissions:
  contents: read
jobs:
  test:
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest]
        python: ['3.10', '3.12']
    runs-on: ${{ matrix.os }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: ${{ matrix.python }}
      - run: python -m pip install -r skills/cftc-agricultural-positioning/requirements.txt
      - run: python -m unittest discover -s skills/cftc-agricultural-positioning/scripts -p "test_*.py" -v
'''


def export(destination):
    destination = destination.expanduser().resolve()
    source = Path(__file__).resolve().parent.parent
    if destination.exists():
        raise FileExistsError('Export destination already exists; choose a new directory.')
    destination.mkdir(parents=True)
    target = destination / 'skills' / NAME
    shutil.copytree(source, target, ignore=shutil.ignore_patterns('.git', '__pycache__', '*.pyc', '.venv'))
    (destination / 'README.md').write_text(README, encoding='utf-8')
    (destination / '.gitignore').write_text('.venv/\n__pycache__/\n*.pyc\nradar-state/\noutput/\n.env\n', encoding='utf-8')
    workflow = destination / '.github' / 'workflows'
    workflow.mkdir(parents=True)
    (workflow / 'validate.yml').write_text(CI, encoding='utf-8')
    return destination


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    print(export(parser.parse_args().output))
