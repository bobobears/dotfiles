---
name: spotify
description: "Spotify: play, search, queue, manage playlists and devices."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
prerequisites:
  tools: [spotify_playback, spotify_devices, spotify_queue, spotify_search, spotify_playlists, spotify_albums, spotify_library]
metadata:
  hermes:
    tags: [spotify, music, playback, playlists, media]
    related_skills: [gif-search]
---

# Spotify

Control the user's Spotify account via the Hermes Spotify toolset (7 tools).

## When to use this skill

- User asks to play music, skip tracks, control volume
- User asks about their playlists or recommends music
- User wants to search for songs, albums, artists
- User says "play something good" or similar

## Available Tools

| Tool | Description |
|------|-------------|
| `spotify_devices` | List available playback devices |
| `spotify_playback` | Start/stop/resume playback, adjust volume |
| `spotify_queue` | View or add to the playback queue |
| `spotify_search` | Search for tracks, albums, artists |
| `spotify_playlists` | List, create, or modify playlists |
| `spotify_albums` | Browse album details and tracks |
| `spotify_library` | Access saved tracks and albums |

## Setup

1. Follow: https://hermes-agent.nousresearch.com/docs/user-guide/features/spotify
2. Authorize Hermes to access your Spotify account
3. The tools become available automatically

## Workflow Examples

### Play a specific song
1. `spotify_search(query="Bohemian Rhapsody")` to find the track
2. `spotify_playback(action="play", uri="spotify:track:<id>")` to play it

### Create a playlist
1. `spotify_playlists(action="create", name="Chill Vibes")` to create
2. `spotify_search(query="...")` to find tracks
3. `spotify_playlists(action="add_items", playlist_id="<id>", uris=["..."])` to add tracks
