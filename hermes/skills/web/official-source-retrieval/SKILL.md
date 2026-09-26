---
name: official-source-retrieval
description: "Use when fetching or verifying official documents."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [Research, Government, Standards, Verification, Provenance]
    related_skills: [blocked-page-recovery, grounded-citations]
---

# Official Source Retrieval & Verification

For any task that rests on an OFFICIAL document: a ministry/agency notice, a
national standard (GB), a policy file, or a news / self-media article that claims
one exists. Two things reliably go wrong here — the primary site will not serve
you the page, and the claim itself is wrong — and both are cheap to handle if you
do them in this order.

Companion to the bundled `blocked-page-recovery` skill (the generic blocked-fetch
ladder: Wayback → archive.today → Jina → API pivot → browser). This skill adds the
official-document specifics that ladder does not cover.

## When to Use

- A task depends on a document you must fetch from an official body: ministry /
  agency notice, national standard, policy file, statistical bulletin.
- A fetch came back blocked (HTTP 412 / JS-challenge page / HTTP 200 with an
  empty body) and you still need the real text.
- An article — news, self-media, blog — claims a regulation, standard, or policy
  exists, and you are about to act on it or file it.
- You are filing official material into a knowledge base or a report and must
  decide which parts are verified fact and which are the author's claims.

## Rule 0 — verify the claim BEFORE you spend effort fetching

Self-media and derived articles (industry accounts, 科普号, reposts) routinely
exaggerate and mis-cite. Treat their factual claims as unverified input, never as
fact.

- Cross-verify the core claim — standard number, issuing body, effective date,
  quantitative targets — against an authoritative source: the issuing ministry's
  press release, official media (新华社 / 央广网 / 中国质量报), or the standards
  body. Searching `<keywords> + 强制性国家标准` or `<keywords> + 发布` surfaces
  press-conference write-ups fast.
- **Numbers that appear only in the derived article are the ones most likely to be
  invented** — staffing ratios, bed counts, scores, thresholds. Mark them
  explicitly as unverified instead of repeating them as fact.
- Check where an "official link" in the article actually points. It is often a
  companion document, not the subject (an article about standard A linking to
  standard B). Verify, then correct or flag it.
- Verify the article's identity too: the same event generates both a formal notice
  and a same-day "interpretation" page under the same column and date. Decide
  which one is meant (usually the formal file when the user files source texts)
  and say which you picked.

## Rule 1 — when the primary site is WAF-gated

Signature (detect early, stop early):

| Client | Result |
|--------|--------|
| `curl` | HTTP **412** with a JS challenge (e.g. Aliyun / icloudwaf) |
| headless browser | HTTP **200**, body **~57 bytes**, title = a single emoji |
| `web_extract` | "Failed to fetch url" |

All three mean "public page, our client cannot execute the challenge" — not "page
is gone". Recovery:

1. **Read it through your search tool's own index.** The search backend crawls
   independently of this client, so querying for the page returns its text. For a
   listing/column page the returned text gives the whole index (entry titles +
   dates) — often enough to identify the target document even without its exact
   URL.
2. **Take the full body from an authoritative reprint** — a national society, a
   local-government mirror, or official media — and **verify it** before trusting
   it: document number, issuing body, date, and section count / natural ending.
3. **Cite the ORIGINAL URL as provenance** and state in the output that the text
   came from a reprint because the primary site was WAF-gated.

Do not retry-hammer the blocked host; do not burn the browser route first.

## Rule 2 — national standards (GB / GB-T) via openstd

`openstd.samr.gov.cn` (国家标准全文公开系统) is curl-reachable: standard number,
name, status and release date are auto-retrievable, and the 目次/章节结构 come from
the online preview. **The full text does not** — the download endpoint is gated by
a CAPTCHA, and the online preview is a low-resolution tiled collage that must not
be OCR'd as a text source.

Full recipe (endpoints, hcno extraction, image fetching, quality warning):
`references/openstd-national-standards.md`.

Store the verified metadata table in the output and point at the official page for
the text.

## Rule 3 — never bypass a verification gate

CAPTCHA, `verifyCode`, login walls, "add WeChat / scan to get the file": do not
recognise, solve, mock, or simulate them. Cite the official page and let the user
pull the official text themselves. Likewise never send cookies or Authorization
headers through a generic proxy relay.

## Rule 4 — store what you verified, not what you read

When filing such a document anywhere (knowledge base, notes, report):

1. Lead with a **verified-facts block** (number / issuer / date / structure, from
   authoritative sources) in a table.
2. Keep the derived article in a clearly labelled section — e.g.
   `## 原文（自媒体解读，YYYY-MM-DD）`.
3. Flag every unverified specific inline, in the document, at the place it
   appears — not only in your chat reply. A later reader sees the file, not the
   conversation.

## Safety & Security

The procedure is read-only: fetch, compare, cite. It writes nothing outside the
agent workspace / the caller's target directory. No credential handling, no
CAPTCHA or WAF bypass, no submission of forms to gated endpoints, no generic proxy
relays. When a gate blocks access, the correct output is an official link plus a
verified metadata block — not a circumvented fetch.
