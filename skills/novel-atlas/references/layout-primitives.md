# Layout primitives

Layout is derived from **how the story is built**, not from what shelf it sits on. Genre is a prior that biases the feature read — it never decides the layout.

## Step 1 — Read four structural features

Answer each from the text, with a one-line justification quoting chapter numbers. If a feature is genuinely ambiguous, pick the dominant mode and say so.

| Feature | Values | What it changes |
|---|---|---|
| **Time continuity** | `strong` — mostly linear with clear span<br>`weak` — heavy flashback, multiple eras, nested narrative | Whether a spine can carry the canvas, or whether time must be scattered |
| **Causal chain** | `short` — episodic, event-driven, local consequences<br>`long` — long-fuse setups paid off much later | Whether events are points on a line or nodes in a web |
| **Centrality** | `single` — one protagonist's arc organises everything<br>`ensemble` — power distributed across a cast | Whether a centre exists to orbit, or whether peers must be networked |
| **Information asymmetry** | `none` — reader and characters learn together<br>`present` — reader knows more, or less, than a character | Whether the canvas needs a second channel (what reader knows vs what cast knows) |

Do not score by feel. A "romance" with long-fuse setups and ensemble cast is not a relationship diagram; it is a web with a spine. Read the features, not the tag.

## Step 2 — Select primitives

Seven primitives. Each has a geometry, a natural reading direction, and things it is bad at. Pick 1 primary, 0–2 secondary.

### `timeline_spine`
Long dominant axis, nodes hung off it, direction implied by spacing.
- **Good at**: causal progress, escalation, "how far we have come"
- **Bad at**: simultaneity; parallel threads read as sequential
- **Adjacency**: everything can attach; give it a full canvas edge or the centre line

### `relational_web`
Nodes with weighted edges, no start or end, centrality shown by degree and size.
- **Good at**: who is bound to whom, alliances, betrayals, love triangles
- **Bad at**: chronology — a web has no "before"
- **Adjacency**: requires open space around every node; label leaders must not cross

### `genealogy_tree`
Rooted hierarchy, layered ranks, branches.
- **Good at**: family lines, sects, factions, inheritance
- **Bad at**: horizontal relationships and cross-branch love; those edges cut across the whole tree
- **Adjacency**: reserve a vertical band for each generation layer

### `event_cloud`
Points scattered in space, meaning carried by density and clustering, not by sequence.
- **Good at**: fragmented or nonlinear structure, atmosphere, "many small things happened"
- **Bad at**: consequence; nothing looks like it caused anything
- **Adjacency**: dense centre, thinning edges; needs a hard frame or it leaks

### `concentric_rings`
Nested circles, importance decreasing outward from a centre.
- **Good at**: single protagonist with satellites, siege, isolation, "the world closes in"
- **Bad at**: peer relationships; rings imply hierarchy that may not exist
- **Adjacency**: spokes read as routes — only use spokes where a route exists

### `confrontation_board`
Two opposed halves with a contested middle.
- **Good at**: factions, sieges, trials, duels, escalating standoffs
- **Bad at**: anything with a third side or with internal dissent
- **Adjacency**: the midline is the strongest element on the canvas; put the decisive event there

### `parallel_tracks`
Two or more lanes running side by side, not touching until a specified node.
- **Good at**: dual protagonists, before/after, known vs unknown, two cities
- **Bad at**: convergence of many threads; two lanes are the practical limit
- **Adjacency**: every crossing point must be an event with a label, never accidental

## Step 3 — Compose

1. **One primary primitive owns more than half the canvas.** A canvas split evenly between two primitives reads as two pictures glued together.
2. **Secondary primitives nest inside zones, not beside them.** A web lives inside one zone of a spine; it does not get its own half.
3. **Directions must not fight.** A spine running left-to-right next to a web is fine; a spine running left-to-right above another spine running right-to-left is not.
4. **Every seam needs a physical reason** — wall, door, road, river, blank band, spine itself. No reason means the zones were cut wrong.
5. **Grid is rectangular, spans allowed.** Zones are unions of whole cells. No polygons, no arbitrary masks — stitching must stay a paste operation.
6. **Zone count 6–16.** Under 6, tiles get so large that single-tile composition breaks down. Over 16, each tile is too small to hold a readable figure at final resolution.

## Worked derivation A — mystery

Read: time continuity `weak` (crime interleaved with investigation, one core flashback), causal chain `long` (the trick is planted early and paid at the end), centrality `single` (investigator), information asymmetry `present` (reader follows the detective but misses one clue).

- Primary: `confrontation_board` — the case is structurally two sides with a contested truth in the middle.
- Secondary: `parallel_tracks` inside the board — what the reader has been shown vs what the detective has pieced together, converging only at the reveal zone.
- Secondary: `timeline_spine` as a thin ribbon along one edge, carrying the flashback in position rather than in time.
- Result: a two-half canvas, the middle column reserved for the reveal, the spine as a marginal ribbon. The trick is readable as *spatial adjacency* — the planted clue sits directly across a seam from its payoff, which is the whole point.

Note what genre alone would have produced: "mystery = spatial trick, nodes fore and aft." That gets the reveal into the middle by luck, and gives no channel for the reader/detective gap.

## Worked derivation B — relationship drama

Read: time continuity `strong` (linear, seasons), causal chain `short` (each rupture local), centrality `ensemble` (three co-equal), information asymmetry `none`.

- Primary: `relational_web` — three co-equal nodes, edges carrying the whole story.
- Secondary: `timeline_spine` as the canvas's vertical axis, so the web is *hung* at different heights as relationships change. The web is redrawn, not moved: the same nodes appear at three altitudes, with edge types changing.
- Result: a vertical spine, three nodes recurring down it, edges thickening, breaking, reversing. Growth reads as vertical displacement; rupture reads as a snapped edge.

Note the trap: a pure web would have been correct about the cast and silent about time, which for this book is half the story. The spine is not decoration — it is the second channel.

## Failure signatures

| Symptom | Likely cause |
|---|---|
| Canvas feels like several pictures glued together | Two primitives of equal weight; no primary |
| User cannot say where to start looking | No reading direction; primitives with conflicting axes |
| Zone 7 is empty while zone 3 is overloaded | Tier assignment done by feel, not by hit rate |
| Labels collide across a seam | Label positions placed in zone coordinates without checking the neighbouring zone's margin |
| Reveal feels arbitrary | Long causal chain laid out on a spine — the distance between setup and payoff was compressed to zero |
