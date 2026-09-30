# Deck diagrams: the `dg` system

A deck diagram is plain HTML laid out with flexbox, plus SVG arrows drawn at runtime from the *measured* positions of elements. Author boxes and rows; the script draws the edges. Arrows re-draw on resize, font load, and sheet change, so layout stays fluid.

## Anatomy

```html
<figure class="scroll">                        <!-- horizontal scroll if wide -->
  <div class="dg" role="img" aria-label="One-sentence description of the whole diagram."
       data-edges='[["id-a","id-b",{"label":"verb"}], ...]'>
    ...HTML boxes, each edge endpoint carrying an id...
    <svg class="edges"></svg>                  <!-- required, empty; script fills it -->
  </div>
  <figcaption>One monospace sentence stating what the diagram showed.</figcaption>
</figure>
```

## Building blocks

| Element | Use |
|---|---|
| `<div class="row">` / `row top` | horizontal group (top-aligns children) — control spacing with inline `style="gap:Npx"` |
| `<div class="col left|center">` | vertical group |
| `<div class="node">` | a box: `<b>title</b><span>detail line</span>...` — spans are the small grey lines |
| node colour classes | `agent` amber (model work) · `script` blue (deterministic) · `engine` green (infrastructure) · `human` purple dashed (people) · `hi` accent border (the focal box) · `dim` faded (secondary/deferred) · `left` left-aligns text |
| `<div class="frame">` + `<span class="title">` | dashed container that groups nodes under an uppercase label |
| `<div class="bar">` | full-width green banner: `<b>label</b><span>line</span>...` — one item per span, one span per line |
| `<span class="caption">` (+`wrap`, `hi`) | small annotation text beside/below nodes |
| spacer | an invisible clone aligns a second row's columns: `<div class="node" style="visibility:hidden">…same content…</div>` |

## Edges

`data-edges` is a JSON array of `[fromId, toId, options?]`. Endpoints are any elements with matching `id`s inside the `.dg`.

**Routes** (`"route"` option; omitted = auto-picked from relative position — right→`h`, left→`hl`, below→`v`, above→`up`):

| route | path |
|---|---|
| `h` | A's right edge → B's left edge, elbow at midpoint if rows differ |
| `hl` | leftward version of `h` |
| `v` | A's bottom → B's top (snaps to one straight x when boxes overlap horizontally) |
| `up` | A's top → B's bottom (same snap) |
| `hv` | A's right → across to B's centre x → vertically into B |
| `hv2` | A's right → out to mid x → vertical → into B's left (for skipping past boxes) |
| `over` | loop-back: up out of A's top, across, down into B's top — for retry/feedback loops |

**Options:**

| option | effect |
|---|---|
| `cls` | `"hi"` accent (the one path the eye should follow — use once per diagram) · `"faint"` dashed grey (secondary) |
| `label` | text on the edge — a verb phrase; it must never repeat the word already inside the target box |
| `lift` | `over` only: how far above the boxes the loop rises (default 26) |
| `dx` | `v`/`up`: shift the line's x |
| `dy` / `sdy` | `h`/`hl`/`hv2`: shift the endpoint / start-point y — stagger several edges entering one box (e.g. −14 / 0 / +14) |
| `frac` | `h`/`hl`/`hv2`: where the elbow sits, 0–1 (default .5) — give converging edges distinct fracs (.66/.5/.34) so their verticals don't stack |
| `dx2` | `h`/`hl`: shift the endpoint x — `-12` stops the arrowhead just before a box's text |
| `dlx` / `dly` | nudge the label after placement — stagger overlapping labels of parallel edges |
| `noArrow` | `true` drops the arrowhead |

## De-overlap playbook

Screenshot first, then fix what the screenshot shows:

- **Converging edges stack their verticals** → distinct `frac` per edge + `dy` stagger on the shared target.
- **Parallel `up`/`v` labels collide** → `dly` stagger (−14 / 0 / +14), or shorten the labels.
- **Label wider than the gap it sits in** → widen the row `gap`, or shorten the label; labels knock out the line behind them (paper-coloured stroke) but not other text.
- **Arrowhead lands on text** → `dx2:-12`, or target the containing box instead of the inner span.
- **Loop-back crosses a title** → raise `lift`.
- **Loop-back clipped at the top** → the arc needs headroom inside the `dg`: give the first row/col `style="padding-top:Npx"` with N ≥ `lift` + 14.
- **Diagram wider than one screen** → shrink gaps and node text first; `figure.scroll` scrolling is the last resort, not the plan.
- **Diagram much wider than tall** → grow vertically instead: stack a flow top-to-bottom, or serpentine a long pipeline into 2–3 rows. Presenters zoom to the diagram's width, so a wide flat strip ends up tiny; a square-ish diagram fills the screen.

## Non-diagram blocks that pair with `dg`

`grid2`/`grid3` of `.card` (+ colour class) · `.cols`/`.cols.even`/`.cols.wide` two-column layout · `<pre>` code with `<span class="c|k|s|a|y">` highlighting · `.tree` for file trees / aligned monospace examples (`<span class="d">` dims, `<span class="a">` accents) · `table` · `.pill` chips · `.stamp` for a rotated rubber-stamp accent · `.legend` colour key. Deck-specific one-off styles go into the deck's own `<style>` block, never inline into the shared base rules.
