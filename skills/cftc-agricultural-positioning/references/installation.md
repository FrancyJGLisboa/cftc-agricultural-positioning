# Installation

## VS Code with GitHub Copilot: no Node.js, npm, npx, or Git required

Installing this skill means copying a folder. It does not require a package manager or administrator rights when the destination is writable. Running its analysis separately requires an approved Python environment, the dependencies listed below, and CFTC network access.

1. Open [the repository](https://github.com/FrancyJGLisboa/cftc-agricultural-positioning), select **Code > Download ZIP**, and extract the ZIP using your operating system. An internally approved copy of the same source also works.
2. In the extracted repository, locate `skills/cftc-agricultural-positioning`.
3. Open your working project in VS Code. Create `.github/skills` in that project's root, then copy the **complete** `cftc-agricultural-positioning` folder into it. Use File Explorer, Finder, or VS Code's Explorer; no terminal command is needed to copy the files.
4. Confirm the installed entrypoint is `<your-project>/.github/skills/cftc-agricultural-positioning/SKILL.md`, with `scripts`, `references`, `assets`, `agents`, and `requirements.txt` alongside it. Copying only `SKILL.md` is insufficient.
5. In Copilot Chat, type `/` and look for `cftc-agricultural-positioning`. If it is absent, reopen the project and check that your organization-approved VS Code/Copilot version supports Agent Skills. Follow your organization's settings for external skills and script execution.
6. Complete the Python setup below, then ask Copilot to use the skill with that Python executable and an absolute persistent state directory outside the installed skill.

The project location and slash-command discovery follow the [official VS Code Agent Skills documentation](https://code.visualstudio.com/docs/agent-customization/agent-skills). VS Code is the editor; these discovery instructions specifically target GitHub Copilot. Other extensions can use different skill locations.

For a personal Copilot installation across projects, copy the same folder into `~/.copilot/skills` instead. On Windows this is `%USERPROFILE%\.copilot\skills` in File Explorer. Do not install duplicate copies in both scopes. Team maintainers can distribute the approved folder through an internal project repository so colleagues receive it with their normal project checkout.

## Optional Python copy helper

If an approved Python interpreter is already available, the bundled helper can perform the same copy. From the extracted repository root, replace the example destination with your actual project path:

```powershell
python skills/cftc-agricultural-positioning/scripts/install.py --skills-dir "C:/Work/MyProject/.github/skills"
```

For [Claude Code](https://code.claude.com/docs/en/skills):

```bash
python skills/cftc-agricultural-positioning/scripts/install.py --skills-dir ~/.claude/skills
```

For another runtime, use its documented skills directory. The helper uses only the Python standard library, accesses no network, installs no dependencies, and refuses to overwrite an existing installation. It does not require Node.js. Keep runtime state separate when upgrading.

## Optional Git and Agent Skills CLI

If approved Git is available, cloning can replace the ZIP download:

```bash
git clone https://github.com/FrancyJGLisboa/cftc-agricultural-positioning.git
```

If Node.js and npm package execution are allowed, the [Agent Skills CLI](https://github.com/vercel-labs/skills) is another optional route:

```bash
npx skills add FrancyJGLisboa/cftc-agricultural-positioning --skill cftc-agricultural-positioning
```

Choose the runtime interactively. This command is unnecessary for the manual installation above. Compatibility follows the [Agent Skills specification](https://agentskills.io/specification); every host has not been tested end to end.

## Python environment

### Corporate laptops: use the existing approved environment first

The analysis requires Python 3.10+, `matplotlib>=3.8,<4`, and `numpy>=1.26,<3`. Copying the skill does not supply these dependencies. In the terminal/environment that the agent will use, check:

```bash
python --version
python -c "import matplotlib, numpy; print('matplotlib', matplotlib.__version__); print('numpy', numpy.__version__)"
```

If `python` is not your approved interpreter, use its full path instead. Missing or incompatible dependencies should be supplied through your organization's package repository or by its Python environment owner. If local Python execution is unavailable, run the skill in an approved remote environment and deliver the resulting panel from there; installing the folder alone cannot generate it. No remote runner is provisioned by this skill.

Example from the VS Code project root, using an already prepared interpreter:

```powershell
python .github/skills/cftc-agricultural-positioning/scripts/radar.py run --state-dir "C:/Work/CFTC-Radar-State"
```

Replace the state path with an approved persistent writable directory outside the skill installation. Tell the agent which Python executable to use; the editor's selected interpreter and its terminal interpreter may differ. Live collection needs HTTPS access to `publicreporting.cftc.gov`. Use your organization's approved proxy and certificate configuration. Package installation access and CFTC data access are separate requirements.

### Optional virtual environment when package installation is permitted

Run from the extracted or cloned repository root. These commands are optional when an approved compatible environment already exists:

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
