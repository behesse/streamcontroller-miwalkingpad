# Mi WalkingPad Plugin for StreamController

Control a Xiaomi WalkingPad from StreamController.

## What it does

- Connects to a WalkingPad using device IP + token
- Keeps a background backend process running and auto-reconnecting
- Exposes StreamController actions:
  - `Start / Stop` toggle action
  - `Speed +0.5`
  - `Speed -0.5`

## Requirements

- StreamController (plugin API compatible with this project)
- A reachable WalkingPad on your network
- Device token (from your Miio-compatible setup)


## Config

Open plugin settings in StreamController and configure:
   - `WalkingPad IP`
   - `WalkingPad token`

## Action behavior

- **Start / Stop**
  - Offline: shows no/black icon
  - Online + stopped: treadmill icon
  - Running: rotating metrics (time, steps, distance)

- **Speed +0.5 / Speed -0.5**
  - Running: shows up/down icon + current speed label
  - Offline or stopped: shows no/black icon

## Manual Setup (non-store)

1. Install/copy the plugin into your StreamController plugins directory.
2. Install backend dependencies:
3. Activate the .venv of your streamcontroller

```bash
source .venv/bin/activate
python __install__.py
```

## Dependency

This plugin uses [`py-miwalkingpad`](https://github.com/behesse/py-miwalkingpad) from GitHub.
