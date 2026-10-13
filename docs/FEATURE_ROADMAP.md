# Vault author tooling roadmap

Research date: 2026-10-14 (Asia/Singapore).

## Selected: read-only graph health report

The exporter adds folder membership edges to all published notes. Those edges
help the public viewer but conceal notes with no authored note connections.
The current unresolved-link checklist addresses targets that do not exist; it
does not identify isolated existing notes or disconnected study clusters.

[Obsidian Graph view](https://obsidian.md/help/plugins/graph) describes existing
files, orphan notes and link directions. This report follows those concepts for
the exported corpus rather than claiming full Obsidian parser compatibility.
Disconnected notes are observations, not judgments about study quality or
instructions to create links. The 26 pending stub decisions remain owner work.

Acceptance:

- `python3 tools/report_graph_health.py` prints isolated notes, notes without
  incoming links, notes without outgoing links, and connected components.
- `--json` returns `schemaVersion: 1`, `scope`, `counts`, `isolated`,
  `withoutIncoming`, `withoutOutgoing`, `components`, and `notes`.
  `notes` records contain `path`, `incoming`, `outgoing`, `canvasMentions` arrays.
- Connectivity uses distinct directed wikilink/Markdown neighbor pairs between
  published notes. Components treat those edges as undirected. Self links,
  missing targets, folder membership and canvas edges do not connect notes.
- Canvas mentions are reported separately; they do not hide isolated notes.
- Drafts and other export exclusions are omitted, including their filenames.
  Report output contains no note bodies or unresolved stub references.
- Paths, lists, components and output order are deterministic. Both human and
  JSON modes write only stdout. Invalid sources fail visibly before output.
- Synthetic directed, duplicate, excluded, canvas and empty fixtures plus
  read-only file snapshots protect these rules. Existing exports stay identical.

The roadmap itself is maintenance metadata and must not enter the study export.

## Next priorities

1. Owner review of the pending stub decisions; apply only approved content edits.
2. Add an optional note-centered neighborhood report using these same graph
   semantics, once author use establishes the desired depth and workflow.
3. Consider comparing graph health across committed exports for review, with
   explicit added/removed-note handling and no automatic link suggestions.
