# CLAUDE.md

Guidance for Claude Code (and other AI assistants) working in this repository.

## 1. Project Overview

DeerAnalysis 2026 is a major re-design and re-release of the classic DEER / dipolar-EPR
distance-analysis tool, originally released as a MATLAB GUI in 2004. The 2026 version is a
**Python + Dash/JavaScript desktop application** that extracts distance distributions P(r)
from Double-Electron-Electron-Resonance (DEER/PELDOR) data.

It wraps two fitting engines:

- **DeerLab** — Tikhonov-regularisation (non-parametric) and parametric fitting, plus global,
  population, and background-only fits, with multi-pathway support and a compactness criterion.
- **DeerNet** — neural-network-based fitting, run via ONNX Runtime.

On top of fitting, the app provides a dataset/fit **management and comparison** layer backed by a
local SQLite database.

- Developed by the Jeschke Lab (ETH Zürich) / UNIGE; author Hugo Karas.
- MIT licensed. Current version: `2026.0.3` (see [pyproject.toml](pyproject.toml)).

## 2. Tech Stack & Key Dependencies

- **Python ≥ 3.12**, packaged with **Poetry** (`poetry-core` build backend).
- **Dash 4.x** multi-page app with:
  - `dash-mantine-components` (v2) — the primary UI toolkit (`dmc`).
  - `dash-bootstrap-components`, `dash-ag-grid`, `dash-iconify`, Plotly.
- **pywebview** — wraps the Dash server in a native desktop window (the shipped app).
- **DeerLab** (≥1.1.5) — fitting engine; **onnxruntime** — DeerNet inference.
- **SQLAlchemy** (>2.0) + SQLite — persistence.
- `xarray`, `numpy` (2.x), `scipy`, `pandas`, `h5py`, `quadprog` — scientific stack.
- `pyepr-esr`, `logs-py` — EPR file loading / lab data integration.
- `psutil` — system monitor page.

Primarily this is a **desktop application**; the Dash server can also be run in a browser for development.
The dash app is run inside a **pywebview** window in the shipped desktop app, which is built with **PyInstaller** (Mac/Win) or **Flatpak** (Linux).



## 3. Repository Layout

```
src/deeranalysis/
  app.py            # Dash app: MantineProvider AppShell, sidebar nav, global theme/scale callbacks
  main.py           # Desktop entrypoint: free port -> Dash in thread -> pywebview window + splash
  pages/            # One module per route (Dash use_pages)
  components/       # Reusable UI pieces & modals
  utils/            # Logic layer: DB, fitting engines, IO, options, figure builders
  parsers/          # Bruker + generic file parsers
  assets/           # CSS/JS (clientside callbacks), logos, favicon, splash
tests/              # pytest suite
packaging/          # pyinstaller/*.spec (Mac/Win/Linux/1dir) + flatpak/
docsrc/dev/         # Developer docs (getting_started, build, flatpak_package)
build/  dist/       # PyInstaller outputs & distributables (generated)
```

### Pages (`src/deeranalysis/pages/`)
Datasets: `upload`, `logs_upload`, `datasets`, `dataset_detail`, `comparison`.
DeerLab fitting: `nonparametric`, `parametric`, `global`, `population`, `background`, `fit_detail`.
DeerNet fitting: `deernet`.
App: `configuration`, `system_monitor`, `about`, `citation`, `not_found_404`.

Routes are registered by each page module (`use_pages=True`); the sidebar nav that links to them
is defined centrally in [app.py](src/deeranalysis/app.py).

### Utils (`src/deeranalysis/utils/`)
- `database.py` — SQLAlchemy models + session/init helpers (see Data Model below).
- `deerlab_normal.py` — non-parametric/parametric/background fitting, plus helpers like
  `apply_model_overrides`, `MNR_estimate`.
- `deerlab_global.py`, `deerlab_population.py` — global and population fits.
- `deernet.py` — DeerNet (ONNX) inference.
- `deerlab_options.py` — experiment types, background models, `build_model_data`, and all the
  centralized Plotly figure builders (`plotly_deerlab`, `plotly_comparison`, `plotly_lcurve`,
  `plotly_goodness_of_fit`, `plotly_dipolar_spectrum`, …).
- `eprload.py`, `io.py`, `csv_loader.py`, `file_parser.py` — data loading/saving (incl. Bruker BES3T).
- `logs_plugin.py` — optional "logs" lab-data API integration.
- `desktop.py`, `figures.py` — desktop helpers and figure utilities.

## 4. Architecture & Data Model

### Runtime modes
- `sys.frozen` (PyInstaller) toggles `desktop_mode`. When frozen, asset/page base paths come from
  `sys._MEIPASS`; in dev mode they resolve relative to the source tree.
- The desktop app runs Dash on a free local port in a background thread and points a pywebview
  window at it ([main.py](src/deeranalysis/main.py)). In dev mode you just run the Dash server and
  open it in a browser.
- Some behaviour keys off `DEERANALYSIS_PYWEBVIEW` (env var) / `window.DEERANALYSIS_PYWEBVIEW` (JS).

### User data directory
- Defaults to `~/DeerAnalysis`, configurable and persisted in `~/.deeranalysis/config.json`
  (`get_DeerAnalysis_directory()` in [components/setup_modal_desktop.py](src/deeranalysis/components/setup_modal_desktop.py)).
- Holds `deeranalysis.db` and the downloaded `deernet/` models.
- **First run**: `first_time_setup()` checks for the DB; a setup modal prompts for the data
  directory and offers to download the DeerNet models.

### Persistence (SQLAlchemy / SQLite) — [database.py](src/deeranalysis/utils/database.py)
- `Dataset` — time axis `t`, real/imag signal `V`/`V_im`, boolean `mask`, experiment type,
  `delays`, `meta`, timestamps. One-to-many with `Fit`.
- `Fit` — belongs to a `Dataset`; `engine` (`DeerLab`/`DeerNet`), `fit_type`
  (`parametric`/`non-parametric`/`AI`), distance distribution (`r`, `P_model`, `PUncert`),
  time-domain `model`/`background`, `pathways`, goodness-of-fit, distance stats, and the fully
  serialized DeerLab `FitResult` in `data`.
- Association tables: `fit_global_datasets` (global fits spanning multiple datasets) and
  `fit_siblings` (related fits). `Settings` stores appearance preferences.
- Numeric arrays are stored in **JSON columns** — (de)serialize via the xarray helpers
  (`dataarray_from_database_entry` and friends in `utils/__init__.py`), not raw dict access.
- Schema migrations run through `update_schema()`.

### Fit pipeline (typical flow)
Page collects user options → `utils/deerlab_*` builds the DeerLab model
(`build_model_data`, `apply_model_overrides`) → fit runs → results serialized to the DB →
Plotly figures rendered by the builders in `deerlab_options.py`.

## 5. Development Workflow

### Setup
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .\.venv\Scripts\Activate.ps1
pip install ../DeerLab             # sibling repos, from source
pip install ../PyEPR
pip install .                      # or use Poetry
```

### Run the app (development)
- VS Code launch config **"Python: Dash"** runs `src/deeranalysis/app.py`
  (`app.run(debug=True)`), served in the browser.
- Or run it directly: `python src/deeranalysis/app.py`.
- Run the full desktop shell (pywebview window): `python src/deeranalysis/main.py`.

> Note: `docsrc/dev/getting_started.md` says `python src/app.py`, but the actual entrypoint is
> `src/deeranalysis/app.py`.

### Tests
```bash
pytest
```
- Config lives in [pyproject.toml](pyproject.toml); `pytest` auto-runs coverage
  (`--cov=deeranalysis --cov-report=term-missing`).
- Suite covers EPR loading (`eprload`), Bruker save, CSV loading, DeerNet, and DeerLab
  normal/global/population fits.

### Build / package
- PyInstaller specs are in `packaging/pyinstaller/` (`DeerAnalysis_MacOS.spec`, `_Win.spec`,
  `_Linux.spec`, `_1dir.spec`).
- Per-OS build steps, DMG creation, and Flatpak packaging are documented in
  [docsrc/dev/build.md](docsrc/dev/build.md) and `docsrc/dev/flatpak_package.md`.

## 6. Conventions & Patterns

- **Dash multi-page**: `use_pages=True`; each `pages/*.py` registers its own route. Add new pages
  there and wire the nav link in the `sidebar_content` list in [app.py](src/deeranalysis/app.py).
- **UI**: prefer Mantine (`dmc`) components; the global theme is `components/dmc_theme.py`
  (`da_dmctheme`). Color scheme, UI scale, and plot template are driven by `dcc.Store` +
  callbacks, synced to appearance settings persisted in the DB.
- **Plotting**: keep figure construction in the centralized `plotly_*` builders in
  `deerlab_options.py`. A custom `compact` Plotly template is registered in `app.py`; theme is
  resolved via `resolve_plot_template`.
- **Clientside callbacks** live in `assets/*.js` — e.g. mirroring the color scheme onto `<html>`,
  scientific-notation number inputs (`scinotation.js`), and figure download → native save dialog
  via the `/save-figure` Flask route registered in `main.py`.
- **Separation of concerns**: UI in `pages`/`components`; scientific, IO, and DB logic in
  `utils`/`parsers`. Keep heavy computation out of callback bodies where practical.

## 7. Domain Glossary

- **DEER / PELDOR** — the pulsed-EPR experiment producing the dipolar signal.
- **P(r)** — distance distribution, the primary result.
- **Background** — intermolecular contribution removed/fit before/with the form factor.
- **Experiment types** — 3-pulse, 4-pulse, 5-pulse DEER (see `experiment_type_options`).
- **Multi-pathway fitting** — modelling multiple dipolar pathways simultaneously.
- **Compactness criterion** — regularisation aid favouring compact distributions.
- **Regularisation vs. parametric vs. neural-net (DeerNet)** — the three fitting approaches.
- **MNR** — modulation-to-noise ratio (data quality metric, `MNR_estimate`).

## 8. Gotchas

- **DeerNet models are not shipped in the installed package** — they are downloaded on first run
  into the user data dir (`[data dir]/deernet`).
- **Frozen vs. dev paths** differ (`sys._MEIPASS`); don't hard-code asset/page paths.
- **JSON columns** require the (de)serialization helpers; don't treat stored arrays as plain lists.
- **Two rendering contexts** (browser dev vs. pywebview desktop) — features like the native
  figure-save bridge only exist in the desktop context.
- The `deernet/nets/` directory in-repo contains many model files; avoid bulk-reading them.

## 9. Citation & Links

When using DeerAnalysis in published work, cite:

- **DeerLab** — Fábregas Ibáñez, Jeschke, Stoll. *Magn. Reson.* 1, 209–224 (2020).
  https://doi.org/10.5194/mr-1-209-2020
- **DeerNet** — Worswick, Spencer, Jeschke, Kuprov. *Science Advances* (2018).
  https://doi.org/10.1126/sciadv.aat5218

Repositories: [DeerAnalysis](https://github.com/JeschkeLab/DeerAnalysis) ·
[DeerLab](https://github.com/JeschkeLab/DeerLab)

## 10. Code Standards
- **Python**: PEP8, type hints, docstrings (Numpy style), 
- Please write reusable functions in `utils/` rather than putting heavy logic in callbacks.
- Please write reusable UI components in `components/` rather than putting heavy layout in callbacks.
- Keep the number of functions and callbacks to a minimum, without too many private functions. The goal is to have a small number of well-defined entrypoints for each page, with the heavy lifting done in `utils/` and `components/`.
- Document each function and class with a docstring, including parameters and return values. Use Numpy style for consistency. **Be consice but clear**. Avoid unnecessary verbosity.
- Write consice but clear code. 
- Add unit tests for new features. Use `pytest` and aim for high coverage. Tests should be located in the `tests/` directory and follow the naming convention `test_*.py`.
