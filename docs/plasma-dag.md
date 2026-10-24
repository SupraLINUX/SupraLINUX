# Plasma 6.7.5 executable DAG

Status: **promoted / canonical for package planning**.

The canonical Plasma DAG is `manifests/kde-plasma-dag.json`. It is promoted from the immutable candidate graph at commit `bab176ffbdc83e62f08030506983f28e34335f86` after provider-resolution review PASS.

## Promotion evidence

- Candidate DAG: `manifests/kde-plasma-dag-candidate.json`
- Candidate Git blob: `dc53609dce00ba6ccee178ca00daffb7253cca39`
- Provider-resolution review run: `37088387510`
- Review artifact: `11261258576`
- Artifact digest: `sha256:7f6aa009fcd72086102f5e64a43bddf59a533c2972b2324f02ece6f1a5ce4aff`
- `review.json`: `838c60bbf5e16b72e3e8551b2fd0f77aeff7f82b0c11d269b1067df7146aebe7`
- `result.json`: `1d68c3373990aaa6dfeb614cd1a62d196be00e0208d9ea0c4cc5e7371d114bad`
- Review definition hash: `cf194c5818c88223e219ff56dcd537c0f0592038b5d101f1506621a7aa4354c4`

## Canonical topology

- Nodes: **75**
- Internal edges: **109**
- DAG: **acyclic**
- Levels: **6**
- Level sizes: **34 / 11 / 20 / 1 / 2 / 7**
- KWin: Level 3
- KWin X11 and Plasma Workspace: Level 4
- Plasma Desktop and the remaining final consumers: Level 5

Promotion preserves the candidate topology byte-for-structure: provider review resolves external providers and source-reference context but does not invent or remove internal KDE source edges.

## Execution boundary

`package_execution_authorized=false`.

Promoting the graph does not execute a package, consume an Attempt, or create a package PASS/FAIL. The next gate is `plasma-level0-definition`, where Level 0 package contracts, materialization inputs, retained providers, and execution authorization must be defined before any `sbuild` can count as Plasma Attempt 1.
