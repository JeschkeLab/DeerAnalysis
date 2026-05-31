# Flatpak packaging

DeerAnalysis ships a simple [Flatpak](https://flatpak.org/) packaging for
Linux. The app is a Dash (Flask) web app rendered in a native window via
[pywebview](https://pywebview.flowrl.com/); on Linux pywebview uses the
GTK + WebKitGTK backend, both supplied by the GNOME runtime.

## Files

All packaging files live under `packaging/flatpak/`:

| File | Purpose |
| --- | --- |
| `packaging/flatpak/io.github.JeschkeLab.DeerAnalysis.yml` | flatpak-builder manifest |
| `packaging/flatpak/io.github.JeschkeLab.DeerAnalysis.desktop` | Desktop launcher entry |
| `packaging/flatpak/io.github.JeschkeLab.DeerAnalysis.metainfo.xml` | AppStream metadata |
| `packaging/flatpak/build-bundle.sh` | Builds the distributable `.flatpak` |

(The PyInstaller `.spec` files live alongside, under `packaging/pyinstaller/`.)

## Runtime

We target the current **GNOME 50** runtime (`org.gnome.Platform//50`), which
ships Python ≥ 3.12, the app's minimum. (GNOME 48 is EOL; GNOME 46 only
provides Python 3.11 and will not work.)

```sh
flatpak install flathub org.gnome.Platform//50 org.gnome.Sdk//50
```

(The Flathub remote, if not already added:
`flatpak remote-add --if-not-exists flathub https://dl.flathub.org/repo/flathub.flatpakrepo`)

## Build & install

Run from the repository root:

```sh
flatpak-builder --user --install --force-clean build-dir \
    packaging/flatpak/io.github.JeschkeLab.DeerAnalysis.yml
```

Then launch:

```sh
flatpak run io.github.JeschkeLab.DeerAnalysis
```

## Building a distributable bundle

`--install` only registers the app in your local Flatpak DB. To produce a
single file you can hand to others, run from the repo root:

```sh
./packaging/flatpak/build-bundle.sh
```

This (1) builds and exports the app into a local OSTree repo (`./repo`), then
(2) packs it into **`DeerAnalysis.flatpak`** in the repo root. The equivalent
manual commands:

```sh
flatpak-builder --force-clean --repo=repo build-dir \
    packaging/flatpak/io.github.JeschkeLab.DeerAnalysis.yml
flatpak build-bundle repo DeerAnalysis.flatpak \
    io.github.JeschkeLab.DeerAnalysis \
    --runtime-repo=https://flathub.org/repo/flathub.flatpakrepo
```

End users install and run it with:

```sh
flatpak install --user DeerAnalysis.flatpak
flatpak run io.github.JeschkeLab.DeerAnalysis
```

The `--runtime-repo` flag embeds where to fetch `org.gnome.Platform//50`, so
users without the GNOME 50 runtime get it pulled from Flathub automatically on
install (requires network on first install). The bundle is unsigned, which is
fine for ad-hoc sharing; for trusted repeat distribution, host `./repo` as a
GPG-signed `.flatpakrepo` remote instead.

## How it works

- `pip3 install . --prefix=/app` installs the app and its dependencies into
  the Flatpak prefix.
- The `src/deeranalysis` tree is then copied over the installed package to
  guarantee all bundled assets (`assets/`, `pages/`, `components/`) are
  present regardless of wheel data-file packaging.
- A small `/app/bin/deeranalysis` launcher runs `python3 -m deeranalysis.main`
  with `PYWEBVIEW_GUI=gtk` plus `WEBKIT_DISABLE_DMABUF_RENDERER=1` and
  `WEBKIT_DISABLE_COMPOSITING_MODE=1` (the latter two work around a WebKitGTK
  blank-window rendering bug seen on some GPU drivers).
- `--share=network` is granted. Even though Dash only binds to `localhost`,
  WebKitGTK's network stack (libsoup) resolves connections through GIO's
  proxy-resolver portal, which is denied in a network-isolated sandbox and
  causes the page's sub-resources to fail loading.

## Notes / limitations

- **Network at build time.** For simplicity the manifest sets
  `--share=network` on the build step so pip can fetch dependencies from
  PyPI. This is convenient locally but **not accepted on Flathub**, which
  requires fully pinned, offline sources. To submit to Flathub, generate a
  pinned dependency list with
  [`flatpak-pip-generator`](https://github.com/flatpak/flatpak-builder-tools/tree/master/pip)
  and drop the `--share=network` build arg.
- **Local `deerlab` / `pyepr-esr`.** The manifest builds these two from the
  sibling `../DeerLab` and `../PyEPR` checkouts (added as `dir` sources under
  `_deps/` and passed to `pip install` alongside `.`). To use the released
  PyPI versions instead, drop the two `./_deps/*` paths from the first
  `pip install` command and remove the two extra sources.
- **`type: dir` source.** The manifest copies the whole working directory
  into the build, including `.venv/` and `.flatpak-builder/`. For a faster,
  cleaner build, run flatpak-builder from a fresh `git clone`, or switch the
  source to `type: git`.
