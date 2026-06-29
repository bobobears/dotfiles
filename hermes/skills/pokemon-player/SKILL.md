---
name: pokemon-player
description: "Play Pokemon via headless emulator + RAM reads."
tags: [gaming, pokemon, emulator, pyboy, gameplay, gameboy]
platforms: [linux, macos, windows]
---

# Pokemon Player

Play Pokemon games via headless emulation using `pokemon-agent`.

## When to Use
- User says "play pokemon", "start pokemon", "pokemon game"
- User wants to watch an AI play Pokemon

## Setup

```bash
pip install pokemon-agent pyboy
```

You need a Pokemon ROM file (.gb, .gbc, .gba). The user must provide it — do not distribute ROMs.

## Usage

```bash
# Start a new game
pokemon-agent play --rom path/to/pokemon.gb

# Resume from save state
pokemon-agent play --rom path/to/pokemon.gb --state path/to/save.state

# Watch the AI play (headless, outputs screen states and actions)
pokemon-agent play --rom path/to/pokemon.gb --watch
```

The agent reads emulator RAM to determine game state (position, HP, badges, party) and makes decisions based on:
- Pathfinding to next objective
- Battle strategy (type matchups, move selection)
- Item management
- Route optimization
