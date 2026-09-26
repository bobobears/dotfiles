# 国家标准（GB / GB-T）查询：openstd.samr.gov.cn

Purpose: confirm that a standard cited by an article exists, and pull its accurate
number / name / status / release date / 目次 structure.

## Reachability

Plain `curl` works (use a normal desktop Chrome UA). **This is NOT an
nhc.gov.cn-style WAF situation** — there is no JS challenge here. Do not infer that
openstd is blocked just because some other government site was.

## 1. Search a standard → get its hcno

```bash
curl -sL -A "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "https://openstd.samr.gov.cn/bzgk/gb/std_list?p.p1=0&p.p90=circulation_date&p.p91=desc&p.p2=GB+48013" \
  -o /tmp/openstd_search.html
```

- `p.p2` is the keyword (spaces as `+`; the bare number is enough, no year needed).
- Each result row carries `<a onclick="showInfo('<hcno>')">GB 48013-2026</a>` plus
  the Chinese name and a status cell (a mandatory standard shows `强标`).
- **hcno is a 32-char uppercase hex id** and is the key for everything below.
  Extract with `showInfo\('([A-F0-9]{32})'\)`.

## 2. Standard info page

```
https://openstd.samr.gov.cn/bzgk/gb/newGbInfo?hcno=<hcno>
```

Its table is JS-rendered, so `curl` does not return the field values. **Take the
metadata from the search results page instead** — do not burn time on this page.

## 3. Online preview (structure only — not a text source)

```
https://openstd.samr.gov.cn/bzgk/std/showGb?type=online&hcno=<hcno>&request_locale=zh
```

Returns a PDF.js-style viewer page. The data lives in the body:

- Each `<div class="page" bg="<fileName>">` is one screen; several screens share one
  `fileName`, i.e. **multiple pages are tiled into a single tall image**.
- Image endpoint: `/bzgk/std/viewGbImg?fileName=<fileName>` → **webp**.
- `fileName` is already URL-encoded in the HTML (contains `%2B` / `%2F`) — **splice
  it in as-is, do not encode twice**. The request needs a `Referer` of the showGb URL.

```bash
curl -sL -A "<desktop UA>" \
  -H "Referer: https://openstd.samr.gov.cn/bzgk/std/showGb?type=online&hcno=<hcno>&request_locale=zh" \
  -o pic_1.bin "https://openstd.samr.gov.cn/bzgk/std/viewGbImg?fileName=<fileName as-is>"
file pic_1.bin   # -> RIFF ... Web/P image
```

**Quality warning**: the preview is a **low-resolution tiled collage** (~2320px wide ×
several thousand px tall, the whole standard compressed into a few images). Local
multimodal OCR recovers only the standard number, the 目次 and section headings; body
clauses bleed into each other and come out as fragments. **Do not treat it as a text
source** — use it to confirm number and structure only.

## 4. Full-text download: CAPTCHA-gated — do not bypass

```
/bzgk/std/showGb?type=download&hcno=<hcno>
```

Returns a page with a `verifyCode` / CAPTCHA form (`var i18n = {..., 'verifyCode': '验证码', ...}`).
This is a deliberate human-verification gate: **do not recognise, solve, or simulate
submitting it.** Put the official page link into the delivered document and let the
user pull the official text from the official channel.

## Summary table

| Wanted | Auto-retrievable? | How |
|--------|-------------------|-----|
| Number / name / status / release date | yes | `std_list` search endpoint |
| 目次 / chapter structure | low-res preview only | `showGb?type=online` + `viewGbImg` — structure reference only |
| Clause text | no | CAPTCHA-gated download; store the official link, user fetches |

When filing: put the **verified metadata table** in the document (more reliable than
the article), and state that the full text was not mirrored and should be obtained
from the official page.
