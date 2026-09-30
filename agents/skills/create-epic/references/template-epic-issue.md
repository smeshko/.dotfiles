<!--
Fallback for the DESCRIPTION of a Linear epic parent issue (not a file on disk),
used when the workspace has no `Epic` issue template. It mirrors that template;
when the template exists, follow it instead (create-epic Step 3c, 0b).

- Title (set separately): `Epic <NN> — <Epic Title In Title Case>`.
- Opening: one or two sentences — what the epic delivers and why it exists.
- Scope areas: one bullet per area, at epic altitude (what gets built, not phase
  or task detail). Usually two to four.
- Epic file: the repo-relative path of the epic file.
-->

<One or two sentences: what this epic delivers and why it exists.>

* **<Scope area>**: <what gets built, at epic altitude>.
* **<Scope area>**: <…>

Epic file: docs/artifacts/epics/<NN>-<slug>.md
