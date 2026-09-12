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

## Research Techniques for Chinese Gaming Content

This environment (China, DGX Spark, ARM64, restricted DNS) requires specific techniques:

### DNS Workaround: curl --resolve
System DNS is unstable (REFUSED responses). Use Google DNS (8.8.8.8) via `host` to manually resolve IPs, then bypass DNS with:

```bash
# Step 1: Resolve IP
host www.3dmgame.com 8.8.8.8 2>&1 | grep "has address"
# Returns: www.3dmgame.com.c.vedcdnlb.com has address 222.186.176.174

# Step 2: curl with --resolve
curl -sL --connect-timeout 8 --resolve "www.3dmgame.com:443:222.186.176.174" \
  -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "https://www.3dmgame.com/gl/3873978.html" \
  -o /tmp/output.html
```

### Known Working Chinese Gaming Sites (tested on this environment)

| Site | Resolution Method | Notes |
|------|-------------------|-------|
| 3DM (www.3dmgame.com) | `--resolve` | Full HTML content, no JS required |
| 游侠网 (gl.ali213.net) | `--resolve` | Full HTML content |
| Bing CN (cn.bing.com) | `--resolve` | JS-rendered results → use only as fallback |
| B站 Wiki (wiki.biligame.com) | `--resolve` | 404 redirects to portal if sub-wiki missing |
| 搜狗 (www.sogou.com) | `--resolve` | JS-rendered results, but HTML includes real URLs |

### What DOES NOT Work (on this environment)
- Baidu (any variant) — always requires captcha
- Steam Community — connection timeout (blocked)
- GitHub (direct) — timeout (blocked), use ghproxy.com
- browser_navigate tool — returns empty shell pages
- DuckDuckGo — DNS resolution fails

### Content Extraction
Once HTML is fetched, strip scripts/styles and search for article content:

```python
import re, html
text = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL)
text = re.sub(r'<[^>]+>', '\n', text)
text = html.unescape(text)
lines = [l.strip() for l in text.split('\n') if l.strip() and len(l.strip()) > 10]
```

Check `references/michangsheng-source-data.md` for session-specific source URLs and data.

### Multi-Source Cross-Verification
Verify findings across at least 2 independent sources before reporting. In this session, 3DM and 游侠网 both confirmed the same Dan recipes and profit figures independently.

### Session Data
- `references/michangsheng-source-data.md` — verified 竹山宗 alchemy guide data from this session
- `references/michangsheng-case-study.md` — confabulation case study (earlier session)
- `references/michangsheng-economy-case-20260730.md` — game economy calculation disaster case study: Agent attempted profit/loss analysis with entirely fabricated prices. Demonstrates the "confident math with guessed numbers" pitfall.

## Common Pitfalls

1. **Confidence-by-association.** "This game has a poison theme, so it probably has poison herbs" — games are designed, not logically derived. Check, don't assume.
2. **Genre conflation.** "Stardew Valley has this mechanic, so similar games do too" — wrong. Every game makes different design choices.
3. **Training-data false memory.** You may have seen a mod, fan wiki edit, or beta patch note. What you "remember" may never have been in the shipped game.
4. **Fan-fiction bleed.** Lore that appears in many fan posts still isn't canon. Require primary sources.
5. **Plausible = correct.** The most dangerous trap. A completely made-up item/mechanic sounds convincing because you're good at generating plausible content. Fight this instinct.
6. **Confident math with guessed prices.** When a user asks "is X profitable?" in a game economy question, calculating profit/loss with guessed numbers is the most dangerous trap of all — because the math *looks* right even when every input is wrong. The output format (table, cost-benefit, conclusion) makes you sound authoritative while being completely off. Never do math on game economy questions without verified price data from a reliable source. If you can't find prices, say "I'd need to look up actual prices" rather than "let me calculate it out."

## Game Economy Questions (is X profitable?)

This is the highest-risk sub-type of game questions. The user is likely farming/grinding and making real in-game decisions based on your answer.

**Never** do this:
- Calculate profit margins using guessed material costs and selling prices
- Assume you know how many items a batch produces (early game vs late game differs)
- Confuse one item's formula with another
- Present a confident-looking table of made-up numbers

**Always** do this:
- Say "I'd need the actual prices to calculate — do you have them?" — the user may know exact values
- If you do get actual prices, cite them explicitly in the calculation
- When the math shows a small margin (±20%), flag it as boundary-sensitive rather than giving a definitive "profit" or "loss"
- If a source gave you some numbers but not others, note which values are verified vs which you're still guessing

## Examples

**Correct:**
> User: "觅长生玄元丹早期炼是赚钱还是亏损？丹方是阴凝草×5 + 苦曼藤×1"
> Assistant: "我需要这两个材料的具体售价和玄元丹的售价才能算。你知道价格吗？"

**Wrong (what happened this session):**
> User: "觅长生玄元丹早期炼是赚钱还是亏损？"
> Assistant: [invents prices at ~80-200 per material, sells at ~300-500, concludes "small profit on collected, loss on bought" — all fabricated numbers]
> [Actual: materials cost 1,440 each, sell for 9,375. Assistant was off by 10-20x on every number.]

Also wrong (same session, follow-up):
> Assistant: "玄元丹丹方:阴凝草3阴凝草2苦曼藤1 — 成本~550-650, 收益~300-500 → 采集小赚全买亏"
> [Still off by 10x because assistant kept guessing rather than asking for actual prices.]

## Verification

- [ ] If you named a specific item/mechanic/character, can you cite exactly where you know this from?
- [ ] If unsure, did you say "I'm not sure" before offering anything?
- [ ] Did you attempt actual research (web/wiki) before giving specifics?
---