---
name: engine-setup
description: Use on first use of Nomad Pro (before onboarding), whenever a tool under ~/nomad-pro-engine is missing or errors on import, and once a week to check for an engine update.
---

# Engine setup and updates

The Python tools, schemas, templates and a baseline copy of HMRC's SRT guidance are not part of this template. They live in the **Nomad Pro engine** repo, github.com/komalamee/Grok-NP_residency-tracker, installed on this box at **`~/nomad-pro-engine`**. The user's own records live in the **user data folder**, `~/nomad-pro-data/` (or wherever the user chose), never inside the engine folder.

## First use

1. Install the engine (no sudo; about a minute):

       curl -fsSL https://raw.githubusercontent.com/komalamee/Grok-NP_residency-tracker/main/install.sh -o /tmp/nomad-pro-install.sh && bash /tmp/nomad-pro-install.sh

   If `~/nomad-pro-engine/install.sh` already exists, run `bash ~/nomad-pro-engine/install.sh` instead. The script clones the repo (or downloads the `main` tarball if git fails), installs `tools/requirements.txt` with `pip --user` if anything is missing, runs the test suite and prints the installed version.
2. Read the last line it prints. If tests say `FAILED` or the script errors, tell the user plainly that the engine didn't install, quote the error line, and don't run any counts until it's fixed. If it says tests passed with some skipped (for example PDF tests when WeasyPrint's system libraries are absent), carry on and mention it only when the user asks for a PDF.
3. Create the user data folder and seed the user's working copies, never overwriting anything already there:

       mkdir -p ~/nomad-pro-data/{evidence,documents,profile,checklists,exports,watch}
       cp -rn ~/nomad-pro-engine/hmrc ~/nomad-pro-data/
       cp -n ~/nomad-pro-engine/schema/country-rules.json ~/nomad-pro-data/country-rules.json

   The user's `hmrc/` copy is the one the weekly HMRC watch updates; the engine's copy stays as shipped so updates apply cleanly.
4. Record the engine version in the user's `daylog.json` profile note or your memory ("engine 0.1.0 installed 3 Nov 2026").

## Weekly update check (with the weekly HMRC guidance routine)

1. `bash ~/nomad-pro-engine/install.sh --check` prints `installed=<x> published=<y>`. Exit 0 means up to date: say nothing. Exit 10 means a newer version is published. Exit 1 means it couldn't check (network): retry next week, say nothing unless it fails three weeks running.
2. If newer, run `bash ~/nomad-pro-engine/install.sh`. It uses `git pull --ff-only` (or a fresh tarball) and re-runs the tests. It refuses to update if files inside the engine folder were edited; never edit them, and never put user data there.
3. After an update, read `~/nomad-pro-engine/hmrc/CHANGES.md` for new entries and compare them with the user's `hmrc/` copy; the weekly HMRC watch then brings the user's copy up to date from gov.uk itself.
4. Tell the user only if the update or its test run did not complete cleanly. A successful update needs no message.

## Rules

* Run tools from the user data folder with the engine path, e.g. `cd ~/nomad-pro-data && python3 ~/nomad-pro-engine/tools/srt_engine.py validate daylog.json`.
* `--kb hmrc` (the user's copy) is the normal knowledge base; without `--kb` the tools fall back to `$NOMAD_PRO_KB`, then to `~/nomad-pro-engine/hmrc`.
* If a tool is missing or errors, say so; never estimate a figure the engine didn't return.
* Never send the user's data anywhere as part of setup or updates. The install only downloads.
