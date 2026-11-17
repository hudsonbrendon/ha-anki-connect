<p align="center">
  <img src="custom_components/anki_connect/brand/logo@2x.png" alt="Anki" height="128">
</p>

# Anki for Home Assistant

[![Tests](https://github.com/hudsonbrendon/ha-anki-connect/actions/workflows/tests.yml/badge.svg)](https://github.com/hudsonbrendon/ha-anki-connect/actions/workflows/tests.yml)
[![Hassfest](https://github.com/hudsonbrendon/ha-anki-connect/actions/workflows/hassfest.yml/badge.svg)](https://github.com/hudsonbrendon/ha-anki-connect/actions/workflows/hassfest.yml)
[![HACS](https://github.com/hudsonbrendon/ha-anki-connect/actions/workflows/validate.yml/badge.svg)](https://github.com/hudsonbrendon/ha-anki-connect/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/hudsonbrendon/ha-anki-connect?sort=semver)](https://github.com/hudsonbrendon/ha-anki-connect/releases)
[![Downloads](https://img.shields.io/github/downloads/hudsonbrendon/ha-anki-connect/total)](https://github.com/hudsonbrendon/ha-anki-connect/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.12.0%2B-18BCF2?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![License](https://img.shields.io/github/license/hudsonbrendon/ha-anki-connect)](LICENSE)

  Monitor and control your <a href="https://apps.ankiweb.net/">Anki</a> collection from Home Assistant via the
  <a href="https://github.com/amikey/anki-connect">AnkiConnect</a> add-on.
</p>

<p align="center">
  <a href="https://github.com/hudsonbrendon/ha-anki-connect/actions/workflows/validate.yaml"><img src="https://github.com/hudsonbrendon/ha-anki-connect/actions/workflows/validate.yaml/badge.svg" alt="Validate"></a>
  <a href="https://github.com/hudsonbrendon/ha-anki-connect/actions/workflows/tests.yaml"><img src="https://github.com/hudsonbrendon/ha-anki-connect/actions/workflows/tests.yaml/badge.svg" alt="Tests"></a>
  <a href="https://github.com/hacs/integration"><img src="https://img.shields.io/badge/HACS-Custom-41BDF5.svg" alt="HACS"></a>
  <img src="https://img.shields.io/github/v/release/hudsonbrendon/ha-anki-connect" alt="Release">
</p>

## Features

- **Collection sensors** — cards reviewed today, cards due, new / learning / review / total cards, deck count.
- **Per-deck devices** — every deck becomes its own device with due / new / learning / review / total sensors, added automatically as decks appear.
- **Diagnostics** — AnkiConnect version, profiles, tags, note types, media directory.
- **Review session binary sensor** — on while a review is open in Anki.
- **Buttons** — sync, open deck browser, show question/answer, undo, check database, reload collection, clear unused tags, remove empty notes, exit Anki.
- **Services** — a generic `anki_connect.api` action that exposes *every* AnkiConnect command, plus typed helpers (`add_note`, `find_notes`, `notes_info`, `find_cards`, `gui_browse`, `gui_deck_overview`, `gui_deck_review`, `create_deck`, `add_tags`, `remove_tags`, `suspend`, `unsuspend`, `sync`, `collection_stats_html`).

## Requirements

1. **Anki** running on a machine reachable from Home Assistant.
2. The **[AnkiConnect](https://ankiweb.net/shared/info/2055492159)** add-on installed (code `2055492159`).
3. For access from another machine, allow LAN binding by setting an environment variable before launching Anki:

   ```bash
   export ANKICONNECT_BIND_ADDRESS=0.0.0.0
   ```

   Optionally set an `apiKey` in the AnkiConnect add-on config; enter the same key in the integration's setup dialog.

> Anki must be **open** for the integration to poll. While Anki is closed the entities show as unavailable.

## Installation

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hudsonbrendon&repository=ha-anki-connect&category=integration)
[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=anki_connect)

### HACS (recommended)

1. HACS → Integrations → ⋮ → **Custom repositories**.
2. Add `https://github.com/hudsonbrendon/ha-anki-connect` as category **Integration**.
3. Install **Anki**, then restart Home Assistant.

### Manual

Copy `custom_components/anki_connect` into your Home Assistant `config/custom_components/` directory and restart.

## Configuration

**Settings → Devices & Services → Add Integration → Anki.** Enter the host, port (default `8765`), a name, and an optional API key.

## Services

Call any AnkiConnect action directly:

```yaml
action: anki_connect.api
data:
  config_entry_id: <your entry id>
  action: getNumCardsReviewedByDay
response_variable: reviews
```

Add a note:

```yaml
action: anki_connect.add_note
data:
  config_entry_id: <your entry id>
  deck: "Spanish"
  model: "Basic"
  fields:
    Front: "hola"
    Back: "hello"
  tags: ["spanish"]
```

## Development

```bash
uv venv
uv pip install -r requirements_test.txt homeassistant
uv run pytest -q
```

## License

MIT
