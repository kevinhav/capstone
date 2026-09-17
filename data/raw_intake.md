<!--
RAW RECIPE INTAKE LOG

Purpose: a low-friction place to drop a recipe the moment you find it, before
it's been parsed into pizza_style_template.csv / bread_style_template.csv.
Paste the recipe as-is (ingredients, instructions, any headnote) - no need to
pre-extract anything by hand.

How to add an entry:
1. Copy the block below.
2. Fill in style_label (your best guess - "unsure" is fine), source (URL or
   citation), and source_type (cookbook / forum-formula / competition / blog).
3. Paste the raw recipe text between the --- markers, verbatim.
4. Append it to the bottom of this file. Do not edit or renumber past entries -
   this file is append-only so parsing can split entries reliably on "## RAW-".

id: unique per entry, format RAW-<sequence number>, zero-padded to 3 digits.

Entries below this comment block will be parsed by a future notebook that
splits on "## RAW-" headers, reads the front-matter lines, and assists in
extracting the structured fields (flour_g, water_g, hydration, etc.) from the
raw text into the CSV templates.
-->

## RAW-001
style_label:
source:
source_type:
---
(paste raw recipe text here)
---
