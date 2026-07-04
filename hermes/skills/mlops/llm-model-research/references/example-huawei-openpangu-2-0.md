# Huawei openPangu-2.0 — Example of Chinese Tech Media Scraping (2026-06-30)

## Context

Huawei announced openPangu-2.0 at HDC 2026 (June 2026) and released Flash weights on June 30. This model was **not** on HuggingFace at announcement time — the only source was IT之家 (Chinese tech media). This demonstrates the Source D workflow from the main SKILL.md.

## Article Discovery

**Homepage scan:** IT之家 homepage (`www.ithome.com`) contained:
```html
<img ... alt="920 亿参数，华为 openPangu-2.0-Flash 模型正式开源上线"
     src="//img.ithome.com/uploadfiles/thumbnail/2026/6/970466_240.jpg">
```

**URL derivation:** Image filename `970466_240.jpg` → article URL `/0/970/466.htm`

**Full URL:** `https://www.ithome.com/0/970/466.htm`

## Extracted Data

### Article 1: Flash Release (2026-06-30)
Source: https://www.ithome.com/0/970/466.htm

- openPangu-2.0-Flash: **92B total / 6B active** (MoE), **512K context**
- openPangu-2.0-Pro: **505B total / 18B active** (MoE), **512K context** (coming July)
- OpenPangu is Huawei's open-source AI model brand, optimized for Ascend NPUs
- Per Ascend: single-card throughput is **2×** other mainstream open models
- 7 components to be open-sourced: weights, inference code, training code, training operators
- Platform: GitCode (https://gitcode.com/ascend-tribe), then HF mirror

### Article 2: HDC 2026 Announcement (2026-06-12)
Source: https://www.ithome.com/0/963/480.htm

- Yu Chengdong said they kept little compute for themselves, most went to supporting domestic enterprises
- Focus on latency and throughput improvement over pure parameter scaling
- Positioned for Agent era (鸿蒙系统级任务执行)

### Related articles from same press cycle
- https://www.ithome.com/0/965/303.htm — Xiaoyi Claw integrates openPangu 2.0 Pro
- https://www.ithome.com/0/963/943.htm — Yu Chengdong: "No second place, only first"

## Deployment Notes

| Model | Total Params | Active Params | INT4 Estimate | DGX Spark (42GB) |
|-------|-------------|---------------|--------------|------------------|
| Flash | 92B | 6B | ~31GB | **Feasible** |
| Pro | 505B | 18B | ~170GB | **Not feasible** |

**MoE memory trap:** Like all MoE models, total params determine VRAM, not active params. Flash 92B at INT4 needs ~92×0.5×0.6875 ≈ 31GB (loaded all experts). Pro 505B needs ~170GB — single-GPU impossible.

**CUDA compatibility unknown:** OpenPangu is Ascend-native. community llama.cpp/GGUF support depends on whether the architecture maps to standard MoE patterns. Not yet confirmed as of release day.

## Technique Summary

When a Chinese model is announced but not yet on HF:
1. Check IT之家 homepage for image thumbnails with relevant alt text
2. Extract article ID from image filename
3. Scrape post_content div (HTML is SSR, content div id="paragraph")
4. Meta description is always SSR-available for a quick summary
5. Cross-reference related articles linked in the footer
