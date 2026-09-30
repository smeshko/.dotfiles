---
name: deck-creator
description: Create or edit drawing-sheet HTML decks — single-file, blueprint-styled presentations of a plan, design, glossary, or results with keyboard-navigated sheets and auto-drawn diagrams. This skill should be used when the user asks for a deck or presentation, wants a document turned into sheets/slides, or wants sheets in an existing deck added, reworked, or de-overlapped.
---

# Deck Creator

A deck is one self-contained HTML file styled as a set of engineering drawing sheets: a sheet-index rail on the left, one `<section class="slide">` per sheet, arrow-key navigation, a solid footer with prev/next and a titleblock, and diagrams whose arrows are drawn at runtime from measured element positions. The reader gets a paginated argument, not a scrolling document.

## Creating a deck

1. Copy `assets/deck-template.html` (in this skill's directory) to the destination and replace the placeholders: `<title>`, rail brand, cover, titleblock rev/date/status. The template already carries the shared style, the navigation + diagram script, 1-based sheet numbering, and the footer — never rebuild these from scratch, and never fork the script per deck.
2. Plan the sheets before writing any: one claim per sheet. A sheet title is a sentence that asserts something ("Resume by re-running the function"), never a topic label ("Replay"). Order sheets as an argument: cover → the one overview sheet → detail sheets → a closing register/index only if the material calls for one.
3. Write each sheet as a new `<section class="slide" data-title="...">` before the footer, with an eyebrow `<b>SHEET NN</b> · SECTION LABEL` numbered 1-based in document order. Update the titleblock's `of NN` to the sheet count. Delete the template's example sheet.
4. Before building any diagram, read `references/diagram-edges.md` — it documents the `dg` box-and-edge system, every route and option, and the de-overlap playbook.
5. Verify by rendering, not by reading the source: serve the containing directory (`python3 -m http.server`), open the deck in the browser tools, and screenshot **every sheet** (`location.hash='#n'` jumps to 0-based sheet n). A sheet passes when nothing overlaps, the diagram fits one screen, and the footer reads `N of N` on the last sheet. Fix and re-screenshot until every sheet passes — the deck is done only when each sheet has a clean screenshot, and the handover names what was verified.

## Editing a deck

Renumber eyebrows and the titleblock total whenever sheets are added, removed, or reordered — then re-run the full screenshot pass; a layout that survived one content change is not evidence it survived this one.

Some decks are **generated**: a script builds the HTML from a source of truth (a glossary file, a data set). Recognise these by a sibling `gen-*.py` naming the deck. Edit the source or the generator and regenerate — an edit to the generated HTML is lost on the next run.

## Conventions

Decks are for human readers; these are settled rules, not defaults to revisit.

- **Concrete language.** Name the thing ("72 terms, no synonyms"), never a vague noun ("one word per thing"). Explain or drop insider names — "Temporal" reads as nothing to most readers until "durable-workflow engine" sits beside it. Where a rule is abstract, add a short worked example (a filled-in template beats three sentences about templates).
- **Content only.** No cover meta blocks (decided-in / source-of-truth listings), no "DECIDED"/"OPEN" boxes, no process annotations like "(grilled)" or review dates — state the fact in prose. Retired-vocabulary lists belong on a glossary's index sheet only.
- **Diagram discipline.** An edge label never repeats the word inside the box it points to ("input → becomes the input" reads as noise). One `hi` path per diagram. A produced-set that is really one value plus side files is one highlighted arrow plus a files frame, never three peer arrows.
- **Numbering and chrome.** Sheets display 1-based everywhere and the last sheet reads N of N; the footer is one continuous opaque bar (both already in the template — preserve them). Cross-references in prose ("sheet 12") must track any renumbering.
