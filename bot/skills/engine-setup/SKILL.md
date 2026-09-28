---
name: engine-setup
description: "Nomad Pro engine (v0.1.4 or later): use before the first Nomad Pro count, whenever a tool under ~/nomad-pro-engine is missing or fails, and when the Nomad Pro weekly update check runs."
---
# Engine setup and updates

Tools, schemas, templates and a baseline mirror of HMRC's SRT guidance (143 gov.uk pages) live in the **Nomad Pro engine**, github.com/komalamee/Grok-NP_residency-tracker, installed at **`~/nomad-pro-engine`**. The user's records live in **`~/nomad-pro-data/`** (or where the user chose), never inside the engine folder.

## First use
1. Install (no sudo, about a minute):
       curl -fsSL https://raw.githubusercontent.com/komalamee/Grok-NP_residency-tracker/main/install.sh -o /tmp/nomad-pro-install.sh && bash /tmp/nomad-pro-install.sh
   If `~/nomad-pro-engine/install.sh` exists, run that instead. It clones the repo (or the `main` tarball), installs `tools/requirements.txt` with `pip --user` if needed, runs the tests and prints the version.
2. Read the last line. `FAILED` or a script error: tell the user the engine didn't install, quote the error line, run no counts until fixed. Some tests skipped (e.g. PDF without WeasyPrint's libraries): carry on; mention it only when a PDF is asked for.
3. Create the data folder and seed working copies, never overwriting:
       mkdir -p ~/nomad-pro-data/{evidence,documents,profile,checklists,exports,watch}
       cp -rn ~/nomad-pro-engine/hmrc ~/nomad-pro-data/
       cp -n ~/nomad-pro-engine/schema/country-rules.json ~/nomad-pro-data/country-rules.json
   The weekly HMRC watch updates the user's `hmrc/` copy; the engine's copy stays as shipped.
4. **Minimum version 0.1.4** (`cat ~/nomad-pro-engine/VERSION`; the skills need `result_withheld`, `matches`, `plan`'s `days_remaining`). Below it: run `bash ~/nomad-pro-engine/install.sh` and check again; still below: tell the user it couldn't update, quote the last line, run no counts until it does.
5. Record the engine version and install date in memory.

## Weekly update check (with the HMRC guidance routine)
1. `bash ~/nomad-pro-engine/install.sh --check` prints `installed=<x> published=<y>`. Exit 0: up to date, say nothing. Exit 10: newer version published. Exit 1: couldn't check; retry next week, mention only after three failed weeks.
2. If newer, run `bash ~/nomad-pro-engine/install.sh` (`git pull --ff-only` or a fresh tarball, then tests). It refuses if engine files were edited; never edit them or put user data there.
3. After an update, read new entries in `~/nomad-pro-engine/hmrc/CHANGES.md` (the HMRC watch updates the user's `hmrc/` copy from gov.uk).
4. Tell the user only if the update or its tests did not complete cleanly, or the version is still below 0.1.4.

## Rules
* Run tools from the data folder: `cd ~/nomad-pro-data && python3 ~/nomad-pro-engine/tools/srt_engine.py validate daylog.json`. `--kb hmrc` (the user's copy) is normal; without it tools fall back to `$NOMAD_PRO_KB`, then the engine mirror.
* A missing or failing tool: say so; never estimate a figure.
* Setup and updates only download; never send the user's data anywhere.
