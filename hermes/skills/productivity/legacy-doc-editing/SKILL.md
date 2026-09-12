---
name: legacy-doc-editing
description: "Use when editing legacy .doc or CJK forms in Word."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [word, doc, docx, libreoffice, official-forms, cjk]
    category: productivity
---

# Legacy Word Document Editing（旧版 .doc / 中文公文表格）

Fills the gap the bundled `docx` skill explicitly excludes ("Not for: .doc") and that `hybrid-office` doesn't cover (it targets new documents). Use this when the user hands over an **existing** Word file — especially a legacy `.doc` or a Chinese official form (征求意见表、自查评价表、公文) — to fill in or modify.

## Core Workflow (verified)

```bash
# 1. Round-trip into docx (python-docx cannot open .doc)
soffice --headless --convert-to docx in.doc --outdir work/

# 2. Edit the .docx with python-docx (form-surgery techniques below)

# 3. If the deliverable must stay .doc (Word 97 circulation is common in 公文 workflows):
soffice --headless --convert-to doc out.docx --outdir work/
```

**Always verify the round-trip**: convert the final `.doc` back to `.docx`, re-read with python-docx, and confirm every filled cell and deletion survived before delivering. If unsure which format the recipient needs, deliver both.

Full worked recipe (table row cloning, run deletion, CJK fonts) in [references/roundtrip-recipe.md](references/roundtrip-recipe.md).

## Pitfalls (form surgery on converted docs)

- **Merged cells repeat in `row.cells`.** A horizontally merged cell returns the same `_tc` for every spanned column index. Dedupe by `id(c._tc)` before editing runs, or you'll apply a change N times / edit the wrong copy.
- **Adding rows to complex tables:** never use `add_row()` on heavily formatted tables — it drops borders/widths. Deepcopy an existing empty row's XML (`copy.deepcopy(row._tr)`) and append to `table._tbl`; this preserves the original formatting exactly.
- **Deleting a specific run** (editor residue like "（删句号）", struck-through words, leftover annotations): iterate `tc.iter(qn('w:r'))`, join each run's `w:t` texts, remove the matching `<w:r>`. After LibreOffice conversion, strikethrough often lives in a character style (`w:rStyle`) rather than an explicit `w:strike` — match by **text content**, not by strike flag.
- **CJK new text needs the eastAsia font.** Setting only `run.font.name` is not enough; also set `w:eastAsia` on the run's rPr (e.g. 宋体), or Word renders with a default font that clashes with surrounding body text.
- **Editor residue in official forms is normal, not content.** Chinese government drafts circulate with inline edit notes ("（删句号）", strikethroughs). When asked to "fill the form", scan for and clean these up too — but mention it in the delivery message so the user knows what was touched.
- **Infer institution names from local data, then confirm.** For 公文 forms needing 单位/机构全称, search the user's local databases (HRMS, patient rosters) for candidate names first, then ask ONE confirmation question with the inferred name as recommended option — don't start from a blank slate.

## Verification Checklist

- [ ] Final .doc re-converted to .docx and re-read: filled cells present, deletions gone
- [ ] No editor residue left (search for 删/改/注 style annotations)
- [ ] New CJK text uses the document's body font (宋体 etc.)
- [ ] Both formats delivered when recipient format is unknown
