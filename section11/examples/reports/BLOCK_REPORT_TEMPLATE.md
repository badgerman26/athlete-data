# Block Report Template

**Structure only — no data. Replace `[placeholders]` with actual values.**

Generated at end of each training block (3–5 weeks).

---

## Template Structure

```
Block [X] Report ([date range])
Weeks in block: [3/4/5]
Phase: [Base Build / Threshold Development / Peak / etc.]
Phase Timeline:
  Wk 1: [phase] ([confidence])
  Wk 2: [phase] ([confidence])
  Wk 3: [phase] ([confidence])
  [Wk 4: [phase] ([confidence])]

Volume Progression:
  Wk 1: [XX.X]h / [XXX] TSS | CTL [XX.X]
  Wk 2: [XX.X]h / [XXX] TSS | CTL [XX.X]
  Wk 3: [XX.X]h / [XXX] TSS | CTL [XX.X]
  [Wk 4: deload — [XX.X]h / [XXX] TSS | CTL [XX.X]]
  Block total: [XX.X]h / [XXXX] TSS

Compliance:
  Sessions: [XX/XX] completed ([XX]%)
  Missed/modified: [list with brief reason, or "None"]

Fitness Progression:
  CTL: [XX.X] → [XX.X] (Δ [+/-X.X])
  ATL: [XX.X] → [XX.X]
  TSB: [X.X] → [X.X]
  Avg ramp rate: [X.XX]/week
  FTP: [XXX]W → [XXX]W ([change or "unchanged"])
  eFTP: [XXX]W → [XXX]W

Key Performance Markers:
  Sweetspot power: [XXX]W → [XXX]W (target: [XXX]W — [hit/miss])
  VO2max power: [XXX]W → [XXX]W (target: [XXX]W — [hit/miss])
  Long ride duration: [XhYm] → [XhYm]
  Long ride decoupling trend: [X.X]% → [X.X]% [↑/↓/→]
  Best 20-min power: [XXX]W (week [X])
  Best 5-min power: [XXX]W (week [X])

Polarization (block average):
  Z1+Z2: [XX]%
  Z3 (Grey Zone): [X]% (target <5%)
  Z4+ (Quality): [X]% (target ~20% of intensity sessions)
  TID 28d (block-scale): [Classification] (PI: [X.XX])
  Hard days/week avg: [X.X]

Polarization by Week:
  Wk 1: Z1+Z2 [XX]%, Z3 [X]%, Z4+ [X]%
  Wk 2: Z1+Z2 [XX]%, Z3 [X]%, Z4+ [X]%
  Wk 3: Z1+Z2 [XX]%, Z3 [X]%, Z4+ [X]%
  Wk 4: Z1+Z2 [XX]%, Z3 [X]%, Z4+ [X]%

Durability by Week:
  Wk 1: mean([X]) dec [X.X]%, [X] high-drift
  Wk 2: mean([X]) dec [X.X]%, [X] high-drift
  Wk 3: mean([X]) dec [X.X]%, [X] high-drift
  Wk 4: mean([X]) dec [X.X]%, [X] high-drift
  Block trend: [improving/stable/declining]

Efficiency Factor by Week:
  Wk 1: mean([X]) EF [X.XX]
  Wk 2: mean([X]) EF [X.XX]
  Wk 3: mean([X]) EF [X.XX]
  Wk 4: mean([X]) EF [X.XX]
  Block trend: [improving/stable/declining]

HRRc by Week (omit section if block total < 3 qualifying sessions):
  Wk 1: mean([X]) [XX] bpm [or "— no data" if 0 qualifying]
  Wk 2: mean([X]) [XX] bpm
  Wk 3: mean([X]) [XX] bpm
  Wk 4: mean([X]) [XX] bpm
  Block trend: [improving/stable/declining]

Wellness (block avg vs previous block):
  HRV: [XX] ms (prev block: [XX] ms) [↑/↓/→] [assessment]
  RHR: [XX] bpm (prev block: [XX] bpm) [↑/↓/→] [assessment]
  Sleep: [XhYm] (prev block: [XhYm]) [↑/↓/→] [assessment]
  Avg Feel: [X.X]/5 ([X] sessions) (prev block: [X.X]/5)
  Avg RPE: [X.X]/10 ([X] sessions) (prev block: [X.X]/10)
  Avg RI: [X.XX] (prev block: [X.XX])
  Avg Monotony: [X.XX] ([note])

Section 11 Flags During Block:
  [List each flag with date and resolution, or "None"]

Phase Progression Check:
  Block objective: [what this block was designed to achieve]
  Criteria met: [Y/N — reference Section 11 phase detection triggers]
  Phase recommendation: [Continue current / Progress to next / Extend / Insert recovery]
  Rationale: [1-2 sentences explaining why, based on metrics above]

Interpretation:
[3-5 sentences — did the block achieve its goals? What adapted?
What stalled? Recovery status entering next block. Key wins and
concerns. Block-over-block comparison where relevant.]

Next Block Plan:
  Phase: [planned phase]
  Duration: [X] weeks
  Focus: [primary training objective]
  Key changes: [what's different from this block]
  Targets: [specific metrics to hit — CTL target, FTP test date, etc.]
```

---

## Field Definitions

| Field | Source | Notes |
|-------|--------|-------|
| **Volume Progression** | Weekly hours + TSS + CTL | Week-by-week CTL shows load trajectory, not just endpoints |
| **Compliance** | Planned vs completed across block | Include reasons for misses — illness, fatigue, life |
| **Fitness Progression** | Start vs end of block | CTL delta is the headline number |
| **eFTP** | Intervals.icu estimated FTP | Track alongside formal FTP — catches drift |
| **Performance Markers** | Best efforts + target comparison | Shows whether stimulus is producing adaptation |
| **Decoupling trend** | Long ride aerobic efficiency | Improving decoupling = aerobic base building |
| **Polarization by Week** | Weekly zone distributions | Catches grey zone creep within a block. Append classification + PI only when week diverges from block-scale TID |
| **Durability by Week** | Weekly mean decoupling from steady-state sessions | VI ≤ 1.05, ≥ 90min. Shows aerobic efficiency trajectory across block |
| **Efficiency Factor by Week** | Weekly mean EF from steady-state cycling | VI ≤ 1.05, ≥ 20min. Shows aerobic fitness trajectory across block |
| **HRRc by Week** | Weekly mean HRRc from qualifying sessions | Omit entire section if block has < 3 qualifying sessions total. Weeks with 0 qualifying show "— no data". Shows recovery quality trajectory |
| **Phase Timeline** | `phase_detected` from each weekly_180d row | Shows phase stability across block — did it hold Build the whole time or flip to Overreached? |
| **TID 28d** | Block-scale Seiler classification | 28d window roughly matches block length; confirms or challenges weekly TID |
| **Wellness assessment** | Directional + threshold label | "declining — monitor" / "stable — no concern" / "improving" |
| **Avg Feel** | Activity-level average from `weekly_180d.avg_feel` | 1=Strong to 5=Weak. Omit if 0 sessions across block. Rising feel (higher number) across block = accumulating fatigue |
| **Avg RPE** | Activity-level average from `weekly_180d.avg_rpe` | 1–10 Borg scale. Omit if 0 sessions across block. Rising RPE at constant load = fatigue signal |
| **Phase Progression Check** | Section 11 phase detection criteria | Explicitly states whether block met progression criteria |
| **Section 11 Flags** | All flags triggered during block | With dates and how they were resolved |

## Assessment Labels

### Wellness Direction
| Direction | Threshold | Label |
|-----------|-----------|-------|
| ↑ >5% improvement | HRV up, RHR down | "improving" |
| → <5% change | Stable | "stable — no concern" |
| ↓ 5–10% decline | Mild drift | "declining — monitor" |
| ↓ >10% decline | Significant | "declining — flag" |

### Phase Progression Criteria (Reference)
| Current Phase | Progress When | Stay When | Regress When |
|---------------|---------------|-----------|--------------|
| Base Build | CTL target met, decoupling <5%, compliance >85% | Approaching targets, no flags | HRV declining, compliance <70%, flags triggered |
| Threshold | FTP improved or eFTP trending up, key sessions hit targets | Making progress, manageable fatigue | Stalled power, wellness declining |
| Peak | Race-specific targets met, form (TSB) improving | Still sharpening | Overreached indicators |
| Deload | Hard sessions resume, CTL stabilized, wellness restored | TSS still reduced, wellness not yet recovered | Overreached indicators persist |
| Recovery | RI >0.90, HRV baseline restored, TSB >+10 | Still recovering | N/A — extend until criteria met |
| Overreached | ACWR <1.3, monotony <2.5, wellness improving | ACWR still elevated or monotony still high | N/A — mandatory recovery until resolved |

## Notes

- **Week-by-week CTL** is critical — the trajectory tells a different story than just start/end
- **Polarization by Week** catches grey zone creep that block averages can mask
- **Durability by Week** catches aerobic efficiency regression that single-session decoupling can miss; the block trend is the headline
- **Efficiency Factor by Week** catches aerobic fitness trends that complement durability; rising EF at same intensity = improving fitness
- **HRRc by Week** shows recovery quality trajectory across the block; omit entire section if fewer than 3 qualifying sessions in the block. Individual weeks with 0 qualifying sessions show "— no data". Context-dependent: varies with exercise intensity, type, and recording conditions
- **Phase Timeline** makes phase stability visible across the block — the Phase Progression Check is more meaningful when you can see the phase held steady or oscillated
- **Phase Progression Check** makes the protocol's decision logic transparent to the athlete
- **Next Block Plan** should flow directly from the Phase Progression Check — if criteria aren't met, explain what the next block does differently
- Keep "Interpretation" to coaching interpretation — the data is already presented above
- Block reports are the most detailed report type (~45-60 lines) — this is where the deep analysis lives

## Formatting Rule

- **Durations and sleep:** Always use `_formatted` fields from JSON (e.g., `sleep_formatted`, `duration_formatted`, `total_training_formatted`). Never convert decimal `_hours` fields to display format — the formatted values are pre-calculated from raw seconds and avoid rounding errors.
