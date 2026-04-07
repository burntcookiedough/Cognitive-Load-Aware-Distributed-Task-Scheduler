---
name: invention-disclosure
description: >
  Use this skill whenever the user wants to write, draft, or generate an Invention
  Disclosure Format (IDF) document, patent disclosure, IP filing, or any structured
  document describing a novel invention for a university IP cell, technology transfer
  office, or patent office. Trigger on phrases like "write my invention disclosure",
  "generate IDF", "patent document", "IP filing", "draft my patent", "fill the IDF
  form", or when the user describes an invention and wants it formally documented.
  Also trigger when the user uploads notes, a rough draft, or describes a device,
  system, or method and asks for a formal write-up. Always produce a .docx output
  using the IDF-B format. This skill is essential — do not attempt invention
  disclosures without consulting it.
---

# Invention Disclosure Format (IDF-B) Generator

Produces a clean, academically rigorous invention disclosure document in .docx
format, structured for submission to a university IP cell or patent office.
Target length: **7–8 pages**. The document must read like a careful human-written
technical report — not like AI-generated text.

---

## Step 0 — Collect Inputs

Gather the following before writing. The user may provide these as a free-form
description, uploaded notes, or a rough draft. Use whatever is available; ask
only for what is clearly missing — do not ask multiple questions at once.

| # | What to collect |
|---|-----------------|
| 1 | Invention name / working title |
| 2 | Field / technical domain |
| 3 | Problem being solved — what exists, what fails, what gap this fills |
| 4 | The invention — what it is, its key components, how they connect |
| 5 | What makes it different from existing work (novelty) |
| 6 | Experimental results or prototype data, if available |
| 7 | Prior art references the user already knows |
| 8 | What aspects the inventor wants protected |
| 9 | Technology Readiness Level (TRL 1–9), if known |

For prior art gaps, draw on training knowledge to suggest likely references in the
stated field. Mark suggested entries clearly (e.g. with *) and note they need
verification before filing. Do not invent patent numbers or DOIs.

---

## Step 1 — Anti-AI Writing Rules (Critical)

These rules are the most important part of the skill. Read them before writing
a single sentence.

### Words and phrases to never use
leverages, cutting-edge, robust, seamlessly, state-of-the-art, novel approach,
innovative solution, unprecedented, holistic, synergistic, facilitate, utilize
(use "use"), paradigm (unless quoting a source), groundbreaking, comprehensive
solution, addresses the need for, it is worth noting, importantly, significantly
(except with a measured value attached).

### Structural patterns to avoid
- Opening a section with a definition ("X is a field that deals with…")
- Sentences that restate what the previous sentence just said
- Bullet points inside Section 4, 6, or 7 — these sections must be prose
- Padding sentences that exist only to transition between ideas
- Ending a section with a summary of what was just said
- Three-part lists used as rhetorical flourish ("fast, reliable, and efficient")
- Starting sentences with "This invention", "This system", "This work" three or
  more times in a row — vary the subject

### What good writing looks like here
Write the way a careful engineer would write a conference paper — measured,
specific, and willing to name limitations without apologising for them.

**Bad (do not produce):**
> "This cutting-edge invention leverages a robust AI pipeline to seamlessly
> address the significant gap in current healthcare monitoring solutions."

**Good (produce this):**
> "Existing wearable monitors sample physiological data at fixed intervals,
> which introduces detection latency of up to several minutes. The proposed
> system performs continuous on-device inference, reducing this latency to
> under three seconds without transmitting data over a network."

The difference: the good version names the specific failure of prior work,
states the specific improvement, and includes a concrete number. It does not
call anything cutting-edge. Write like this throughout.

### On length and depth
The target is 7–8 pages. Reaching this requires genuine depth in Sections 4,
6, 7, and 8 — not padding. Each of these sections should do real explanatory
work:

- **Section 4** must explain the problem at enough depth that a reviewer who
  knows the domain but not this invention understands why existing solutions
  are insufficient. Four to five substantive paragraphs minimum.
- **Section 6** should describe the working principle as if explaining it to
  a technically competent colleague from an adjacent field — enough detail
  that they understand how the system functions end to end. Three paragraphs.
- **Section 7** is the technical core. Use sub-sections (7.1, 7.2, 7.3…).
  Each sub-section should be at minimum two paragraphs of prose. Name
  components, algorithms, protocols, and parameters specifically. Do not
  describe things in generic terms when specific terms are available.
- **Section 8** should describe each experiment individually — what was
  tested, how, what was found. Include a results table. If the inventor
  provides data, present it accurately. If not, describe the validation
  approach in enough detail that someone could replicate it.

---

## Step 2 — Document Format

The format is fixed. Match it exactly.

### Page layout
- Paper: A4
- Margins: top 0.5 in, bottom 0.625 in, left/right 0.75 in
- Font: Times New Roman, 11pt body (22 half-points in docx-js)
- Body text: justified, line spacing 1.15 (276 twips), 6pt after paragraph

### Header block
The document opens with a table header (not a page header/footer — it is
inline content at the top of page 1 and repeated at the end of the document).

Structure: 4 columns — [Institution name / logo placeholder | Document label |
Issue No / Date | Amd. No / Date]. Use "02-IPR-R003" as the document number.

Do not create a separate title page. The title appears inline as Section 1,
immediately after the header block.

### Section labelling
Every section starts with a bold inline label on the same line as its content:

> **1. Title of the invention:**  [title text continues here on same line]

For longer sections (4, 5, 6, 7, 8, 9, 10), the label is on its own line as
a bold paragraph, and content follows as normal paragraphs beneath it.

Section numbering: 1 through 10. Section 10 is always the TRL table.

### Prior art table columns
S. No | Patent / Publication (Year) | Methodology | Limitations w.r.t. Proposed
Invention | Gap Addressed by This Work

Aim for 6–10 references. Header row shaded `D9E1F2`.

### Section 4 sub-labels
Within Section 4, use inline bold labels for the two parts:
**Summary:**  (first paragraph)
**Background:**  (subsequent paragraphs)

### Section 5 format
Numbered list (1, 2, 3…). Each item is one sentence beginning with an active
verb: "To detect…", "To reduce…", "To enable…". Five to seven items.

### Section 7 sub-sections
Number them 7.1, 7.2, 7.3… as inline bold labels, each followed by prose.
Include figure placeholders: "[Figure N: description — to be inserted by inventor]"
styled in italics/grey.

### Section 9 format
Formal patent claim language. Each claim is a bold inline label followed by
legal prose: "A method for X, comprising: (a) …; (b) …; (c) …"
Minimum five claims. Later claims should reference earlier ones ("The method
of Claim 1, wherein…").

### Section 10 — TRL table
Three-row structure:
- Row 1: Phase headers — Research | Development | Deployment (spanning 3 cols each, shaded)
- Row 2: TRL 1 through TRL 9 labels
- Row 3: Descriptions
- Row 4: Checkmarks (✔) in ticked cells, shaded `E2EFDA`

### End of document
Close with a centred bold line:
`— — — — — — — — END OF THE DOCUMENT — — — — — — — —`

Then repeat the header block table.

---

## Step 3 — docx Production

Use the `docx` npm library. Refer to `/mnt/skills/public/docx/SKILL.md` for
exact API patterns, table construction, list formatting, and validation.

Key reminders relevant to this document:
- Use `WidthType.DXA` for all table widths — never `PERCENTAGE`
- Tables need both `columnWidths` array and `width` on each cell
- Use `ShadingType.CLEAR` — never `SOLID`
- Never use `\n` — use separate `Paragraph` elements
- Run `validate.py` after generating; fix any errors before presenting

After generating, copy to `/mnt/user-data/outputs/` and call `present_files`.

---

## Step 4 — Quality Check Before Presenting

Before presenting the file, verify:

- [ ] Document is 7–8 pages when opened in Word / LibreOffice
- [ ] No section uses bullet points where prose is required (Sections 4, 6, 7)
- [ ] Section 7 has at least 3 sub-sections with 2+ paragraphs each
- [ ] Section 8 includes a results table and per-experiment narrative
- [ ] Section 9 has at least 5 claims in formal patent language
- [ ] No forbidden words appear in the text (leverage, robust, seamlessly, etc.)
- [ ] No sentence opens with "This invention/system/work" more than twice
  consecutively
- [ ] Prior art table has at least 6 rows
- [ ] TRL checkboxes reflect the actual stage of the invention
- [ ] Header block appears at top and bottom of document
- [ ] Validate passes with no errors

If the page count is under 7, expand Sections 4, 7, and 8 with more specific
technical content — do not add padding sentences. Add detail, not filler.

---

## Reference: Section Content Depth Guide

This table summarises minimum content expectations per section to reach 7–8 pages.

| Section | Minimum content | Format |
|---------|----------------|--------|
| 1 | One precise noun phrase | Inline |
| 2 | 2–3 sentences covering domain, sub-domain, contribution type | Inline |
| 3 | 6–10 references in table | Table |
| 4 | 4–5 paragraphs: problem → existing failures → gap → this invention → why now | Prose |
| 5 | 5–7 numbered objectives | Numbered list |
| 6 | 3 paragraphs covering the end-to-end pipeline | Prose |
| 7 | 3–4 sub-sections, 2+ paragraphs each, figure placeholders | Prose + sub-heads |
| 8 | Per-experiment narrative + results table + interpretation | Prose + table |
| 9 | 5+ formal patent claims | Claim language |
| 10 | TRL table with correct boxes ticked | Table |
