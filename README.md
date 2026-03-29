# Fastest Route — Real-Time GPS Navigation for Barcelona

A GPS navigation system that calculates the fastest route between two points in Barcelona, accounting for street length, speed limits, and **live traffic congestion**. Accessible via a Telegram chatbot.

## Demo

<p align="center">
  <img src="https://user-images.githubusercontent.com/88190336/127870013-2682dc88-cdd3-4b02-9cfa-2e8b9d40bf9d.PNG" width="250">
</p>

## How It Works

### The `itime` Metric

We designed a custom edge-weight metric called **itime** (intelligent time):

```
itime = (length / max_speed) * congestion_factor
```

- **length** and **max_speed** come from OpenStreetMap graph data
- **congestion_factor** is pulled from Barcelona's live traffic API, updated every 5 minutes
- For streets without congestion data, a heuristic value is assigned based on road type (e.g., primary roads = fluid, residential = dense)

### Performance Optimization

| Operation | Time |
|-----------|------|
| Initial graph download + setup | ~25 seconds (one-time) |
| Route calculation | **~0.5 seconds** |

**Strategy:** The full Barcelona street graph is downloaded once with generic `itime` values. Every 5 minutes, only the edges with real congestion data are updated — the rest remain cached. This avoids recomputing the entire graph and enables sub-second route calculations.

## Architecture

| Module | Purpose |
|--------|---------|
| `igo.py` | Core routing engine — downloads/caches the street graph, fetches live congestion data, computes shortest paths using `itime`, generates map images |
| `bot.py` | Telegram bot interface — handles user commands, translates locations to coordinates, serves route images |

## Bot Commands

| Command | Description |
|---------|-------------|
| `/start` | Initialize the bot and download the graph |
| `/help` | Show available commands |
| `/go <destination>` | Get the fastest route from your location to a destination (name or coordinates) |
| `/pos <location>` | Set a simulated current location |
| `/unpos` | Revert to using your real location |
| `/where` | Show your current location on a map |

## Setup

### Prerequisites

```bash
pip install staticmap networkx osmnx
```

### Running

1. Create a Telegram bot via [BotFather](https://t.me/botfather) and save your TOKEN
2. Place the token file in the same directory as `bot.py` and `igo.py`
3. Run:

```bash
python3 bot.py
```

## Tech Stack

- Python
- OpenStreetMap + OSMnx
- NetworkX (graph algorithms)
- Telegram Bot API
- Barcelona Open Data (live traffic congestion)

