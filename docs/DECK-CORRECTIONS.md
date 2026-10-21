# Deck corrections — Plumbline Greenfield & Brownfield decks

**Status (2026-10-19): applied** in `Brownfield_Agentic_SDLC_v1.2.pptx` and `PLUMBLINE_Greenfield_v1.2.pptx`.
- **Brownfield:**
  - slides 3–5 now describe Originator → Benchmark → Judge;
  - slide 10 is labelled a self-reported run;
  - new slides 11–14 cover the three stages, monorepo scale, measured results on the OMS, and what we sell.
- **Greenfield:**
  - the factual fixes below are made;
  - a three-stage slide is added at 4;
  - terminal mock-ups are captioned "illustrative";
  - economics is labelled self-reported and the timeline is labelled a projection.

The "not proven at 1,000+ services" point stands for real monorepos. The impact map's scale test is synthetic, and the deck says so.

## Factual fixes

| Deck / slide | Current text | Correct to | Why |
|---|---|---|---|
| Greenfield, slide 10 | "⚠ Cat 3: BigDecimal from double literal" | "⚠ Cat 1: BigDecimal from double literal" | Type rules are Category 1; Category 3 is Lombok |
| Greenfield, slide 10 | "⚠ Cat 8: @Transactional missing on service" | Drop it, or add a rule first | No category checks `@Transactional`; Category 8 is Logging |
| Greenfield, slide 10 | "✓ Cat 3 … / ✓ Cat 8 …" pass lines in the same terminal mock | Renumber to match `loops/spec/dev-eval-loop.md` categories | Same mislabelling as the warnings |
| Greenfield, slide 3 | "Arch Agent … 11-item DoR check" | "15-item DoR check" | Design Completeness items added |
| Greenfield, slides 3, 5 | Self-review shown as the eval loop | "Deterministic gates → isolated critic → fix → verifier" | The agents no longer grade their own work |
| Brownfield, slide 3 | "Critic findings — an independent check" | Keep, but now true in Claude Code; for Copilot only via the CI critic job or a new chat (same-chat = self-attested): the critic runs as a separate subagent **every attempt** (it previously ran in the same context, attempt 1 only) | |
| Greenfield, slide 12 (whole slide) | "$80 total", "$0.77 per story", "$569 saved via prompt caching", "80% tokens saved", "133 stories · 105 PRs", "0 human dev hours" | Label every figure "self-reported, 9-service greenfield POC billing — not reproducible from this repo"; drop "0 human dev hours" | Not measured here, not brownfield, not at scale |
| Greenfield, slide 13 | "Saves 63 days (33%)", "Worst case (+25%)", "Best case (−20%)", 190 vs 127 days | Label the whole chart "projection" and list the assumptions behind each band | A plan comparison, not a measured outcome |
| Greenfield, slides 9–10 | Terminal mock-ups: "JaCoCo 84%", "mvn test 47/47", "DoD 8/8", "PR #89", "SCRUM-36" | Caption "illustrative" unless backed by real logs you can show | Presented as real output |
| Greenfield, slide 2 | "Reduces requirement-to-design cycle by 40–50% (Wissen pilot results)" | Cite the pilot (name, date, sample size, baseline) or remove | No source in this repo; unverifiable as stated |
| Greenfield, slide 2 | "Reduces regression effort by 25–35%" | Cite or remove | No source |
| Brownfield, slide 10 | Heading "measured, not estimated" over "5–6 min", "~57 min" and "Months → Weeks" | Change the heading to "one self-reported run"; label "5–6 min" and "~57 min" as the author's single run (no data in this repo); move "Months → Weeks" under "expected" | Only one unpublished run backs the timings; onboarding duration was never measured |

## New slide: "Measured on our own OMS" (replaces unmeasured claims)

From `eval/RESULTS.md`, 2026-10-13/14, 80 planted defects + 25 clean controls on `broker-dealer`:

| | Held-out PR-sized defects | Single-change defects | False alarms on clean controls |
|---|---|---|---|
| Deterministic gates | 5/30 (gates v2, held out) | 20/50 before tuning (18/23 mechanical) | 0 on controls; 2 false alarms among 6 extra findings |
| Isolated LLM critic | 30/30 | 49/50 | 0 on controls; 2 false alarms among 31 extra findings |

Footnote, mandatory: *"Defects authored by AI in the same model family as the critic; small sample. Customer-authored and historical defects are the next validation step."*

## New slide: "What we sell"

> Whatever AI tool you adopt, we make it safe on your codebase. We provide your rules as enforced gates, a benchmark that re-qualifies every new model, a domain rule pack, and a governance pack with an audit-record schema (wiring into the agents is in progress).

Four columns: **Gates** (`gates/`) · **Benchmark** (`eval/`) · **Domain pack** (`packs/domain-rules/`) · **Governance** (`packs/governance/`).

## Remove or soften

- "0 human dev hours": the governance model now requires named human approvals for every write. Say "humans approve; agents do the work".
- Any implication that the agents are proven at 1,000+ services. They aren't yet.
