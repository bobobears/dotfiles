---
name: game-lore-and-fiction
description: "Answering questions about games, novels, fiction, TTRPGs, anime, and fictional worlds where confabulation risk is high. Never invent game items, characters, mechanics, or lore that sound plausible but are not verified."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [gaming, lore, fiction, accuracy, hallucination-prevention]
    related_skills: [humanizer]
---

# Gaming, Lore, and Fiction Q&A

## Overview

Game and fiction questions are high-risk territory for confabulation. LLM training data contains fan theories, mods, walkthroughs, and beta content that are NOT canon. If asked about specific game items, builds, mechanics, or lore details, the safest answer is "I'm not sure" followed by an offer to research — never a plausible-sounding guess.

## When to Use

- User asks about any video game, board game, or TTRPG (D&D, Pathfinder, etc.)
- User asks about lore/characters/items in a novel, anime, movie, or TV series
- User asks about game builds, strategies, farming routes, crafting systems
- User asks about fictional-world mechanics they intend to rely on in-game

## Workflow

1. **Pause and assess.** Do you actually know this game? Did you play it? Read its wiki or patch notes recently? If no, stop.
2. **DO NOT list specifics you're unsure about.** If your knowledge is from training data only, say so.
3. **Offer to research.** If the user provides a wiki link or lets you search, go look it up.
4. **If lookup fails** (blocked, DNS error, Cloudflare), report that honestly. Do NOT fill the gap with invented content.
5. **If you must give an answer without lookup:** give general principles only (e.g. "early game usually favors cheap-to-craft potions"), never specific item names or numbers.

## Common Pitfalls

1. **Confidence-by-association.** "This game has a poison theme, so it probably has poison herbs" — games are designed, not logically derived. Check, don't assume.
2. **Genre conflation.** "Stardew Valley has this mechanic, so similar games do too" — wrong. Every game makes different design choices.
3. **Training-data false memory.** You may have seen a mod, fan wiki edit, or beta patch note. What you "remember" may never have been in the shipped game.
4. **Fan-fiction bleed.** Lore that appears in many fan posts still isn't canon. Require primary sources.
5. **Plausible = correct.** The most dangerous trap. A completely made-up item/mechanic sounds convincing because you're good at generating plausible content. Fight this instinct.

## Examples

**Correct:**
> User: "觅长生竹山宗早期炼丹选什么品种好？"
> Assistant: "我不太确定具体的种植品种，让我去查一下攻略/Wiki。"

**Wrong:**
> User: "觅长生竹山宗早期炼丹选什么品种好？"
> Assistant: "竹山宗适合种蛇涎草、腐骨花、紫芝做毒系丹药…"
> [None of these exist in the game. All fabricated.]

## Verification

- [ ] If you named a specific item/mechanic/character, can you cite exactly where you know this from?
- [ ] If unsure, did you say "I'm not sure" before offering anything?
- [ ] Did you attempt actual research (web/wiki) before giving specifics?
---