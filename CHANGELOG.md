## 1.4.2 (2026-09-09)

### fixed (1 change)

- [Support FLEX_NEXT JSON format from multimon-ng 1.6.0 — handle `msg_type` field as alternative to `demod_name`, support both legacy and FLEX_NEXT schemas, gracefully skip non-message packets (`bch_stats`, `biw_*`).](lucid/mmng-ui@a38419f) ([issue #3](lucid/mmng-ui/-/issues/3))

## 1.4.1 (2026-09-09)

### fixed (1 change)

- [Fix FLEX JSON address extraction — FLEX JSON output uses `capcode` not `address`; each demod branch now handles its own field.](lucid/mmng-ui@9ffcaf5)

## 1.4.0 (2026-05-30)

### added (5 changes)

- [Multi-feed tab support — listen on multiple UDP ports simultaneously, each decoded in its own tab with independent status, sparkline, and message log.](lucid/mmng-ui@e5b25bd9255d8d184549f76681b18a1ddf3a80ee)
- [Capcode database support — load known capcodes from JSON or CSV via `--capcodes`/`-k`; matching addresses display a coloured alias with dimmed raw address, unknown ones show raw as before.](lucid/mmng-ui@8c15fd862ce89da6908144bddc59f24975143588)
- [Emoji icon support for capcode entries — the `icon` field in capcode JSON/CSV (e.g. "fire", "ambulance") renders as a Rich emoji prefix.](lucid/mmng-ui@0283c44ba0aa22dc7f379625bb57058e3cb63e16)
- [Tab naming — `--port 8888=Name` or `--port 8888:Name` syntax at launch, plus runtime rename of the active tab by pressing `r`.](lucid/mmng-ui@b1655ba6b2b825fe57edbaaec4ce153dca6967fe)
- [Save tab to file — press `s` to open a save dialog; export the active tab's messages as CSV, Markdown, or JSON.](lucid/mmng-ui@b7f8e77b6a5fedfe40df5a9b3e33a92ad4d4a410) ([issue #7](lucid/mmng-ui/-/issues/7))

### fixed (2 changes)

- [Fix DataTable rendering blank rows when few messages exist — moved height from inline Python to CSS.](lucid/mmng-ui@3dbb8610a569420a5aa6e8aa0c0e613b9787dbc6)
- [Fix 4 previously-skipped tests covering FLEX fragmented/complete messages and POCSAG numeric handling; boost reader.py coverage 54% → 80%.](lucid/mmng-ui@80910668298b48500b2415dc72e59277f4143268)

### changed (2 changes)

- [Improve PyPI metadata — add SDR/pager keywords, 9 new Trove classifiers, and Changelog/CI project URLs.](lucid/mmng-ui@1ed33cef167d55d9375501f0836c91e6f7f5cd54)
- [Extract serve/version-detection for testability; add 31 new tests across Phases 1–2 (pocsag.py coverage 0% → 64%).](lucid/mmng-ui@9b04b68279877b0c540aaf8f3059632b8c8d5a94)

### other (4 changes)

- [Add root `.gitignore` with entries for `__pycache__`, `.coverage`, `htmlcov/`, `graphify-out/`, `.idea/`, `.opencode/`, and build artifacts.](lucid/mmng-ui@1ed33cef167d55d9375501f0836c91e6f7f5cd54)
- [Add AGENTS.md for AI agent integration; ignore auto-generated `_version.py` from hatch-vcs.](lucid/mmng-ui@6cc6ac08052ec1b7921a9006b19b1ab0d5b2b17f)
- [Remove Pipfile (Pipenv) and tox.ini (tox) — Hatch now handles both environments and testing.](lucid/mmng-ui@7d069afb333df7e9529beb6f7edbdc7f5fecceb9)
- [Add stale bot GitHub Action to auto-close inactive issues and PRs.](lucid/mmng-ui@467158a630d2e602c67d18a7a530fa2ea89afe66)

## 1.3.1 (2025-10-22)

### fixed (1 change)

- [Fixes GH #6, I didn't know FLEX does/does not have an address field, or that it's optional.](lucid/mmng-ui@c3ac56b8a48b4bf09d5f7fc7e325799e7e7ec4c9)

## 1.3.0 (2025-10-21)

### added (1 change)

- [This adds support for running sox in the pipeline to convert incoming streams...](lucid/mmng-ui@1da9ff2480d83045d728a4639477bf50845a82f3) ([merge request](lucid/mmng-ui!4))

## 1.2.0 (2025-10-20)

### added (1 change)

- [Add the ability to use mmng-ui in a web browser!](lucid/mmng-ui@99aece4bb13e0d3ee7b36e47151d33392e54fb27) ([merge request](lucid/mmng-ui!3))

## 1.1.0 (2025-10-19)

### added (1 change)

- [Add an about/info screen, showing version numbers and paths to binaries.](lucid/mmng-ui@9488b16f1c85d2c078dd118a058d58f383e858ca) ([merge request](lucid/mmng-ui!2))

### fixed (1 change)

- [Update GitLab pipeline to use hatch and do some coverage](lucid/mmng-ui@6ca069a083e517c5f352ed85d2d13c3d86934f41) ([merge request](lucid/mmng-ui!1))

### changed (5 changes)

- [Change to hatch, update and lock down textual to 6.3.0 (and supporting libs),...](lucid/mmng-ui@5ab5cfa15a834def9d2d9bf9fa3a2b43aae90b6a) ([merge request](lucid/mmng-ui!1))
- [Update CSS for *way* newer version of textual.](lucid/mmng-ui@6a325128206e72a80a6873cdf2ffe4c0bdbfbd85) ([merge request](lucid/mmng-ui!1))
- [Update helpscreen.](lucid/mmng-ui@9d5880c914d724eec3fc5d756fcf071f531a3021) ([merge request](lucid/mmng-ui!1))
- [Update screenshots.](lucid/mmng-ui@1443efc1e22efe198857420b1bdd866ac3f606bb) ([merge request](lucid/mmng-ui!1))
- [Update doco to reflect multimon-ng merged my JSON code at version 1.4.0.](lucid/mmng-ui@5bf1c2a76c2f6f9b1cfd4854f932c8001cb281fd) ([merge request](lucid/mmng-ui!1))

## 1.0.8 (2025-09-01)

### added (2 changes)

- [Implement the ability to choose a charset. Addresses GH #4. Temporarily removed the filtering code.](lucid/mmng-ui@a4f9c43d2df28005e7e7f69c26405f6237e93452)
- [Add FLEX_NEXT decoding to multimon-ng.](lucid/mmng-ui@186e0c198a5ca266519ae0cf56a1cf85371c2291)

## 1.0.7 (2024-12-11)

### added (1 change)

- [Add FLEX_NEXT decoding to multimon-ng.](lucid/mmng-ui@186e0c198a5ca266519ae0cf56a1cf85371c2291)

## 1.0.6 (2024-12-09)

### fixed (1 change)

- [FLEX fixes.](lucid/mmng-ui@77242a8ea0658def57cc63a1ddac84200379378c)

### added (1 change)

- [Add a filter feature.](lucid/mmng-ui@da2c8ee3f4a48ab0b0ece98693f7ec2b7132f391)

## 1.0.5 (2024-10-09)

### fixed (1 change)

- Bugfixes, doco and tidy up

## 1.0.4 (2024-10-08)

### fixed (1 change)

- Bugfix

## 1.0.3 (2024-10-07)

### added (1 change)

- [CLI argument for listening port](lucid/mmng-ui@246ceb3808d5e2cfb25d85f6a7ba70a3e4ec6d75)

## 1.0.2 (2024-10-06)

### fixed (1 change)

- [JSON support detection in multimon-ng](lucid/mmng-ui@a0f8318dfaa4e0f55d878beb0096a90947ffae75)

## 1.0.1 (2024-10-06)

### changed (1 change)

- Re-code reader.py a little

### added (1 change)

- More tests

### fixed (1 change)

- [Parse normal output or JSON mode](lucid/mmng-ui@d71897dc24e553f9a0a04dc3b4f59cbeb0296b7b)

## 1.0.0 (2024-10-04)

### other (1 change)

- Initial release
