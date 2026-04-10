# Example JSON Output

Example output from `sync.py` v3.86 for a fictional cyclist in a Build phase. Use these to understand the data schema before running your own sync.

**These are invented data** — realistic values for a ~12h/week multi-sport athlete (cycling + rowing + walks), CTL ~65, FTP 260/270 (indoor/outdoor). Not anonymized real data.

## Files

| File | Description |
|------|-------------|
| `latest.json` | Current 7-day snapshot — activities, wellness, fitness metrics, readiness decision, derived Section 11 values |
| `history.json` | Longitudinal data — daily (90d), weekly (180d), monthly (up to 3y) |
| `intervals.json` | Per-interval segment data for recent structured sessions |
| `routes.json` | Route/terrain data — climbs, descents, course character, polyline for events with GPX/TCX attachments |
| `ftp_history.json` | FTP change tracking for Benchmark Index calculation |

## Schema Version

These examples reflect sync.py v3.86 / Section 11 v11.17. Key fields added since earlier examples:

- `readiness_decision` — pre-computed go/modify/skip recommendation with signal breakdown
- `workout_summary_stats` — planned-vs-actual matching statistics
- `race_calendar` — upcoming races and taper/race-week alerts
- `has_intervals` — boolean flag on activities linking to intervals.json
- `efficiency_factor`, `hrrc` — per-activity capability metrics
- `description` — activity description passthrough
- `chat_notes` — athlete notes extracted from activity description (conditional)
- `wellness_field_scales` — 1-4 scale legend in READ_THIS_FIRST
- Expanded wellness fields (subjective state, vitals, body composition, nutrition, lifestyle, cycle)
- `zone_basis` on all TID/Seiler blocks
- `feel_count`, `avg_rpe`, `rpe_count` in weekly history rows
- `primary_sport`, `primary_sport_tss`, `sport_tss_breakdown` on weekly history rows
- `sport_type` on planned workouts

For the full field reference, see [SECTION_11.md](../../SECTION_11.md) (Derived Metrics table).
