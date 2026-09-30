# Global working rules (Ivo)

## Output
- Lead with the outcome; actions at a glance. Bullets over prose; summaries ≤10 lines.
- Never dump a wall of text. For finding/issue lists >5 items: give the count, the top 3-5, and offer the rest.
- When reporting work: what changed, where, what's next — one line each.

## Editing discipline
- Before editing a file this session hasn't touched, run `git diff <file>` first. If it has uncommitted changes I made by hand, preserve them — never revert or overwrite my manual edits.
- Stage explicitly (`git add <paths>`), never `git add -A` or `git add .`.

## Done means demonstrated
- A task/feature is complete only when its behaviour is demonstrated at runtime (test output, screenshot, log excerpt) — not when the code compiles or the diff looks right. If you can't demonstrate it, say what's unverified.

## Quirks
- If a message looks like gibberish but maps to QWERTY-Cyrillic (e.g. "/цлеар" = "/clear"), transliterate it and proceed without comment.
- Never read `.env` files; ask me for the specific value you need.