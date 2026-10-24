# Publish `loadmark` to PyPI - step by step (all free)

Everything here is free: Python, Git, GitHub, TestPyPI and PyPI cost nothing.
Commands are for Ubuntu. Run them in the VS Code terminal.

**Already checked for you:** 32 tests pass, the package builds, `twine check` passes, and the built
file installs in a clean environment. I could not upload it to PyPI myself, so you do that part.

## Rules before you start
- Build this on your **own laptop in your own time**. Do not add any Solventum or Capgemini code,
  table names, column names, bucket names or data. The example here is generic. Keep it that way.
- If you are unsure about your company's IP policy, ask your manager once. It takes 2 minutes.
- PyPI does not give a "licence". You choose one. This project uses **MIT** (the `LICENSE` file).

---

## Part 1: Tools (one time)
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git
python3 --version          # must be 3.9 or higher
```

## Part 2: Open the project and put your details in
```bash
unzip loadmark.zip
cd loadmark
code .
```
Edit these three files (search for `YOUR`):
1. `pyproject.toml` -> `authors` (your name and email), and both `YOUR_GITHUB_USERNAME` links.
2. `LICENSE` -> replace `YOUR NAME`.
3. Nothing else needs editing.

**Email tip:** the email in `pyproject.toml` becomes public on PyPI. Use a personal email, not your
company one.

## Part 3: Make sure the name is free
The name `loadmark` was free when I checked, but someone could take it before you. Check:
```bash
curl -s -o /dev/null -w "%{http_code}\n" https://pypi.org/pypi/loadmark/json
```
- `404` = free, go on.
- `200` = taken. Choose another name (for example `loadmark-etl` or `runmarker`) and change it in:
  `pyproject.toml` (`name = ...`), the folder `src/loadmark` (rename it), and every
  `from loadmark import ...` in `tests/`, `examples/` and `README.md`.

## Part 4: Run it on your laptop
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
python examples/basic_usage.py
python examples/basic_usage.py       # run twice: the second run is "incremental"
```
`pytest` should show `32 passed`.

## Part 5: Put the code on GitHub
1. GitHub -> **New repository** -> name `loadmark` -> **Public** -> do **not** add a README or license
   (you already have them) -> Create.
2. In the terminal:
```bash
git init -b main
git add .
git status                      # no .venv, no *.db files in the list
git commit -m "First version of loadmark"
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/loadmark.git
git push -u origin main
```
3. Open the **Actions** tab. The "Tests" workflow should turn green on Python 3.9, 3.11 and 3.12.

## Part 6: Create your PyPI accounts (two separate sites)
1. Sign up on **https://test.pypi.org** (the practice site) and on **https://pypi.org** (the real one).
   They are separate accounts, so register on both.
2. On each one: Account settings -> turn on **two-factor authentication (2FA)**. Save the recovery codes.
3. On each one: Account settings -> **API tokens** -> **Add API token**.
   - Name: `loadmark-upload`
   - Scope: **Entire account** (the project does not exist yet, so a project-only token is not possible
     for the first upload).
   - Copy the token (it starts with `pypi-`). It is shown **only once**. Keep the TestPyPI token and the
     PyPI token in a password manager or a private note. **Never put a token in the repo.**

## Part 7: Build and upload

### 7a. Build
```bash
source .venv/bin/activate
pip install build twine
rm -rf dist
python -m build
twine check dist/*              # must say PASSED for both files
```
This creates two files in `dist/`: a `.whl` and a `.tar.gz`.

### 7b. Practice upload to TestPyPI
```bash
export TWINE_USERNAME=__token__
read -s -p "Paste TestPyPI token: " TWINE_PASSWORD; export TWINE_PASSWORD; echo
twine upload --repository testpypi dist/*
```
(`read -s` hides the token and keeps it out of your command history.)
Open `https://test.pypi.org/project/loadmark/` to see the page.

Test installing it from TestPyPI in a fresh environment:
```bash
python3 -m venv /tmp/t && source /tmp/t/bin/activate
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ loadmark
python -c "import loadmark; print(loadmark.__version__)"
deactivate
```

### 7c. The real upload to PyPI
```bash
source .venv/bin/activate
export TWINE_USERNAME=__token__
read -s -p "Paste PyPI token: " TWINE_PASSWORD; export TWINE_PASSWORD; echo
twine upload dist/*
```
Open `https://pypi.org/project/loadmark/`. Now anyone can run:
```bash
pip install loadmark
```
Test it in a fresh environment as in 7b (without the `--index-url` options).

### 7d. Tighten security (do this once, right after the first upload)
On pypi.org: delete the "Entire account" token, then create a new token with scope **Project: loadmark**.
Use that one from now on.

## Part 8 (optional): Publish automatically from GitHub, with no token at all
This uses PyPI's "Trusted Publishing". The file `.github/workflows/publish.yaml` is already in the project.
1. On pypi.org: Your account -> **Publishing** -> **Add a new pending publisher**:
   - PyPI project name: `loadmark`
   - Owner: your GitHub username
   - Repository: `loadmark`
   - Workflow file name: `publish.yaml`
   - Environment name: `pypi`
2. On GitHub: repo -> Settings -> **Environments** -> New environment -> name it `pypi`.
3. Create a release: repo -> **Releases** -> Draft a new release -> tag `v0.1.0` -> Publish release.
4. The "Publish to PyPI" workflow runs the tests, builds, and uploads.

(If you already uploaded 0.1.0 by hand in Part 7, use this for your next version instead.)

## Part 9: Releasing a new version later
PyPI never accepts the same version twice, and you cannot replace a file.
1. Change the version in **both** `pyproject.toml` and `src/loadmark/__init__.py` (for example `0.1.1`).
2. Run `pytest`, then `rm -rf dist && python -m build && twine check dist/*`.
3. Upload with Part 7c, or create a GitHub release with tag `v0.1.1` if you set up Part 8.

Version rule of thumb: bug fix = `0.1.1`, new feature = `0.2.0`, breaking change = `1.0.0`.

## Part 10: Make it look good for your resume
- Add the green test badge to the top of `README.md`:
  `![Tests](https://github.com/YOUR_GITHUB_USERNAME/loadmark/actions/workflows/tests.yaml/badge.svg)`
- Repo -> About (gear icon) -> add a description and topics: `etl`, `data-engineering`, `incremental-load`, `python`.
- Pin the repo on your GitHub profile.
- Add `PyPI` and `GitHub` links on your resume and LinkedIn (Projects section).
- Ideas for version 0.2.0 that make it stronger: a `SnowflakeStore` (as an optional extra), an S3 store,
  a small command-line tool (`loadmark history crm/contacts`), and more tests.

**Resume line**
> Published `loadmark` on PyPI: an open-source Python library for incremental-load checkpoints
> (bookmark moves only on success, configurable lookback, backfill, run history with pluggable stores),
> with a pytest suite and GitHub Actions CI/CD.

**Interview story (30 seconds)**
"In my project each ingestion job reads the last successful run from an audit table and starts from
midnight of that day to avoid losing late data. I generalized that idea into a small library so the
same safe logic is not copy-pasted across jobs. I wrote the tests, packaged it, and published it with
a CI pipeline." Do not mention client names, tables or sources.

## Troubleshooting
| Problem | Fix |
|---|---|
| `externally-managed-environment` when running pip | Use the virtual environment: `source .venv/bin/activate` |
| `403 Invalid or non-existent authentication` | Username must be exactly `__token__`, and the password must be the full token starting with `pypi-` |
| `403 ... isn't allowed to upload to project` | The name is taken by someone else, or your token is scoped to another project. Rename the package |
| `400 File already exists` | That version was already uploaded. Raise the version number |
| `twine check` fails on the README | Look at the message. Usually a broken table or code block in `README.md` |
| `No matching distribution` after upload | Wait 1-2 minutes and try again |
| `ModuleNotFoundError: loadmark` | You forgot `pip install -e .` or the virtual environment is not active |
| Tests fail on GitHub but pass locally | Check the Python version in the failing job, and that you committed all files |
