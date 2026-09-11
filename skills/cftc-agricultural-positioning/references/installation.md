# Installation

## From GitHub

Intended repository: `FrancyJGLisboa/cftc-agricultural-positioning`. These commands become available after the repository is published. No GitHub authentication is needed to install from a public repository.

Using the [Agent Skills CLI](https://github.com/vercel-labs/skills):

```bash
npx skills add FrancyJGLisboa/cftc-agricultural-positioning --skill cftc-agricultural-positioning
```

Choose the desired runtime interactively, or specify it:

```bash
npx skills add FrancyJGLisboa/cftc-agricultural-positioning --skill cftc-agricultural-positioning -a codex -g
npx skills add FrancyJGLisboa/cftc-agricultural-positioning --skill cftc-agricultural-positioning -a claude-code -g
npx skills add FrancyJGLisboa/cftc-agricultural-positioning --skill cftc-agricultural-positioning -a opencode -g
```

The CLI installs instructions and resources; Python dependencies still need the setup below. Runtime names and discovery locations are maintained by that CLI. Use its interactive mode if a runtime identifier changes. Compatibility is based on the [Agent Skills specification](https://agentskills.io/specification), not a claim that every runtime has been tested.

## Without Node.js

```bash
git clone https://github.com/FrancyJGLisboa/cftc-agricultural-positioning.git
cd cftc-agricultural-positioning
```

Copy the complete skill folder into your runtime's supported skill directory. A portable copy helper is included. For [Claude Code](https://code.claude.com/docs/en/skills):

```bash
python skills/cftc-agricultural-positioning/scripts/install.py --skills-dir ~/.claude/skills
```

For another runtime, pass its documented skills directory to `--skills-dir`. The helper refuses to overwrite an existing installation. Review and replace an existing installation deliberately when upgrading; runtime state is separate and should be retained.

## Python environment

Python 3.10+ is required. Run from the repository root:

```bash
python -m venv .venv
```

macOS/Linux:

```bash
.venv/bin/python -m pip install -r skills/cftc-agricultural-positioning/requirements.txt
.venv/bin/python skills/cftc-agricultural-positioning/scripts/radar.py run --state-dir ./radar-state
```

Windows PowerShell:

```powershell
.venv\Scripts\python.exe -m pip install -r skills/cftc-agricultural-positioning/requirements.txt
.venv\Scripts\python.exe skills/cftc-agricultural-positioning/scripts/radar.py run --state-dir .\radar-state
```

When using an installed skill rather than a clone, substitute that skill's absolute directory. Give the runtime the selected Python executable and persistent state directory. No API key, account, price feed, ChatGPT-specific storage, or paid data subscription is required.

Ask the agent: “Use cftc-agricultural-positioning to update the agricultural radar. Return only the validated panel.”

## Tests

```bash
python -m unittest discover -s skills/cftc-agricultural-positioning/scripts -p 'test_*.py' -v
```

Unit tests use explicitly synthetic records and require no network. A live invocation additionally requires CFTC network access and matplotlib/numpy. Use a separate state directory when evaluating delivery behavior.

## Maintainer: export and publish

The same installed skill can generate a clean repository layout, including this skill under `skills/`, an English README, and a Linux/Windows test workflow:

```bash
python /absolute/installed/skill/scripts/export_repository.py --output /absolute/new/cftc-agricultural-positioning
```

From that exported directory, with GitHub CLI authenticated as `FrancyJGLisboa`:

```bash
git init -b main
git add .
git commit -m "Add portable CFTC agricultural positioning skill"
gh repo create FrancyJGLisboa/cftc-agricultural-positioning --public --source . --remote origin --push
```

Run the create command only if that repository does not already exist. For an existing repository, inspect its instructions and current content, then contribute through a branch and pull request. Do not overwrite it blindly. Select repository visibility deliberately; the example makes only the clean skill source public, without state, credentials, or market snapshots.
