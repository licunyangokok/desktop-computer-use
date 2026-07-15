# desktop-computer-use

> Let AI "see" and operate your Windows desktop like a human — not by clicking coordinates on a screenshot, but by reading the UI Automation accessibility tree and controlling controls semantically.

## What is this

`desktop-computer-use` is a Windows desktop automation skill for AI assistants. It enables an AI to:

- **Semantic control**: Read the UI structure via Windows UI Automation (UIA) and interact with controls by their *name / role* rather than pixel coordinates.
- **Dual channel**: Control both native desktop apps (Calculator, Notepad, Settings, etc.) and web browsers via Chrome DevTools Protocol (CDP).
- **Safety first**: Dangerous actions (closing windows, system shortcut combos) require explicit `--confirm`. Everything runs locally — no network, no data upload.

## Why it's different (the key highlight)

Traditional desktop automation relies on "screenshot + coordinate clicking", which breaks the moment the layout shifts. `desktop-computer-use` reads the **accessibility tree** — a structured description of UI elements, like a labeled checklist for the AI. This is far more robust to minor UI changes and closer to how a *human* understands an interface (see the "OK" button and click it, instead of memorizing its pixel position).

## Install

Requires Python 3.8+. In the skill directory:

```bash
pip install -r requirements.txt
```

Dependencies: `uiautomation`, `websocket-client`, `Pillow` (licenses in `THIRD_PARTY_LICENSES.md`).

## Usage

In any AI assistant that supports this skill, trigger it in natural language:

- "Open Calculator and compute 1+1"
- "Fill out this form and submit it"
- "Open a website in the browser and take a screenshot"

Built-in tools (`scripts/`): `find_roots`, `observe`, `search`, `expand`, `inspect`, `act`, `read_text`, `wait_for`, `browser`.

## Originality

This skill is an independent Python re-implementation based on the open-source project **pi-computer-use** (`earendil-works/pi`, MIT License), not a line-by-line copy. Original author copyright is retained per the MIT license. See `THIRD_PARTY_LICENSES.md`.

## License

MIT License © 2026 木火晨鸣 (Muhuo Chenming)

## Note

- Windows only.
- Operating local apps requires the user to actively trigger and authorize.
- Dangerous actions (e.g., closing a window, system shortcuts) require a second confirmation.
- Runs entirely locally; no public network connection, no data upload.

## Author & Source

- Author: **木火晨鸣 (Muhuo Chenming)**
- Source: https://github.com/licunyangokok/desktop-computer-use
- Independently re-implemented based on [pi-computer-use](https://github.com/earendil-works/pi) (MIT License).
