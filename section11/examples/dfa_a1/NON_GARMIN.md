# DFA a1 — Non-Garmin Platforms

> **Status: Documentation only.** Section 11's DFA a1 features currently work with one source: AlphaHRV on Garmin. This file tracks what other platforms could plausibly support, what's been verified, and what we'd need from a non-Garmin user to confirm.

---

## Why this exists

The DFA a1 Protocol in `SECTION_11.md` requires the [AlphaHRV](https://apps.garmin.com/en-US/apps/40fd5e67-1ed0-457b-944b-19fdb3aae7e7) Connect IQ data field by Marco Altini, recording on a Garmin head unit, syncing directly to Intervals.icu (Strava strips developer fields). Other head units have varying paths to DFA a1 — some plausible, none currently verified end-to-end against the Section 11 pipeline.

This file:

1. Documents the **current support status** per platform, honestly labeled
2. Names **specific verification gaps** for each plausible alternative
3. Provides **discovery commands** that a user on the relevant platform can run and paste back to us
4. Explains how to **contribute** verification or fixes via GitHub issues / PRs

If you're on a non-Garmin platform and want DFA a1 to work, this file is for you. We'd like to help, but we need a user on the relevant device to run the commands — none of the maintainers own Wahoo, Karoo, Coros, or Suunto hardware.

---

## Status by platform

| Platform | Path | Status | Notes |
|---|---|---|---|
| **Garmin** + AlphaHRV | Connect IQ data field → FIT developer field → Intervals.icu `dfa_a1` stream → `sync.py` | ✅ **Supported** | The reference path. Validated end-to-end. See `SECTION_11.md` DFA a1 Protocol §Overview. |
| **Suunto** + Zone Sense (DDFA) | SuuntoPlus app → FIT developer field → ? | ⚠️ **Investigational** | Suunto records DDFA (Dynamic DFA) via Zone Sense / Monicardi partnership. **Different algorithm than DFA a1** — values are not directly comparable, threshold mapping (1.0/0.5) may not apply. Even if Intervals.icu surfaces the field, Section 11 would need a separate protocol section to interpret it. |
| **Hammerhead Karoo** + [veloVigil](https://github.com/velovigil/velovigil-karoo) | Karoo extension (Android sideload) → ? | ⚠️ **Investigational, gaps known** | veloVigil is an open-source Karoo extension (MIT licensed) that connects to Polar H10 over BLE and computes HRV (RMSSD, SDNN, pNN50). **Currently does NOT compute or write DFA a1** — that would require a contribution upstream. Hammerhead's own "log RR to FIT" is on the roadmap but not shipped as of late 2025. |
| **Phone fallback** (FatMaxxer / HRV Logger) + Intervals.icu CSV upload | Phone app records DFA a1 in parallel → CSV → manually merged into Intervals.icu activity stream → ? | ⚠️ **Investigational, paid tier required** | Intervals.icu added CSV stream upload in October 2025, including support for array-valued streams like HRV. **Requires Intervals.icu Supporter subscription** (paid tier). Verification gap: we don't yet know if a user-uploaded `dfa_a1` column lands as a stream named `dfa_a1` (matching AlphaHRV's slot) or under some other name. If yes, `sync.py` works without changes. If no, sync.py needs a stream-name mapping. |
| **Wahoo** (ELEMNT, BOLT, ROAM) | — | ❌ **No current path** | Wahoo's ELEMNT firmware does not log RR intervals to the FIT file, and Wahoo has no third-party app platform analogous to Connect IQ. Multiple users on the Wahoo forum have switched to Garmin specifically for DFA a1. Phone fallback (above) is the only option. |
| **Coros** | — | ❌ **No current path** | Coros watches do not log in-activity HRV/RR. Phone fallback is the only option. |
| **Polar** (head units / watches) | — | ❌ **No current path** | Polar records HRV but does not share it with third-party platforms via API. Phone fallback is the only option. |

---

## Phone fallback workflow

This is the universal path for any platform — works regardless of head unit, but has real costs.

### What you need

- **Android:** [FatMaxxer](https://github.com/IanPeake/FatMaxxer) (Apache 2.0, free, open source). Polar H10 only. [Formally validated against Kubios HRV in EJAP, October 2025.](https://link.springer.com/article/10.1007/s00421-025-06037-0)
- **iOS:** [HRV Logger](https://www.hrv.tools/) by Marco Altini (paid, closed-source — same author as AlphaHRV). Works with any Bluetooth chest strap that broadcasts RR.
- **Intervals.icu Supporter subscription** — required for CSV stream upload.
- A chest strap that broadcasts beat-to-beat RR over Bluetooth (Polar H10 strongly recommended; HRM-Pro Plus works for HRV Logger).
- Your phone, running in parallel with your head unit during the ride.

> **HRV4Training is NOT the right app.** It's a separate (also Marco Altini) app for **resting morning HRV measurements**, not in-activity recording. Use HRV Logger if you're on iOS.

### Workflow (untested end-to-end, plausible)

1. **Record the ride normally** on your head unit.
2. **In parallel**, start FatMaxxer (Android) or HRV Logger (iOS) on your phone with the chest strap paired. Both apps record DFA a1 in real time and export CSV when you stop.
3. **After the ride**, sync the head unit ride to Intervals.icu via your normal path (direct device sync recommended).
4. **Export the FatMaxxer / HRV Logger CSV** from your phone.
5. **In Intervals.icu**, open the activity → Activity Data tab → download the streams CSV.
6. **Align timestamps** between the phone CSV and the streams CSV (this is the manual step — both files have time columns, you join on them).
7. **Add a `dfa_a1` column** to the streams CSV with the aligned values from the phone app.
8. **Re-upload the merged CSV** to Intervals.icu. (Intervals.icu's CSV upload UI: "If the activity has any array valued streams (e.g. HRV or a custom stream using array values) then you need to untick the 'Convert text to numbers, dates and formulas' box.")
9. **Run sync.py** — if the merged column landed under the stream name `dfa_a1`, the existing pipeline picks it up and produces a `dfa` block in `intervals.json` exactly as it would for an AlphaHRV recording.

**Open question that determines whether this works:** does step 9 succeed, or does Intervals.icu store the user-uploaded column under a different stream name? **No one has verified this yet.** If you try the workflow above, please report back via a GitHub issue (see Contribute section below).

### Costs and caveats

- **Two devices recording the same ride.** Real UX cost. Battery, pairing, time-syncing.
- **Manual CSV merging per ride.** Could be scripted (Python or Node), but it's still a per-ride workflow.
- **Intervals.icu Supporter subscription is paid.** No free path for non-Garmin users currently.
- **Algorithmic differences.** FatMaxxer and HRV Logger may produce slightly different DFA a1 values than AlphaHRV at the margins. The protocol's threshold mapping (1.0 ↔ LT1, 0.5 ↔ LT2) is approximately consistent across the three but not bit-identical. Treat phone-recorded DFA a1 with the same protocol thresholds, but expect ±0.05 noise vs the AlphaHRV reference.
- **Polar H10 is the gold-standard strap** for all three apps. Other straps work, but artifact rates climb fast.

---

## Discovery commands

If you're on a non-Garmin platform and want to help verify a path, run the relevant block below and paste the output as a [GitHub issue](https://github.com/CrankAddict/section-11/issues). All commands are read-only.

### Intervals.icu credentials (needed for all platforms)

```bash
# Set these once
ATHLETE=i123456                      # your athlete id (i + digits)
KEY=your_intervals_icu_api_key       # from intervals.icu Settings → Developer Settings
```

### Suunto: does Intervals.icu surface DDFA from Suunto FIT files?

**Goal:** find one recent Suunto-sourced ride where Zone Sense was active, and check whether Intervals.icu exposes any DFA / DDFA / alpha stream or interval field.

```bash
# 1. List recent Suunto activities (look for type=Ride and source=SUUNTO)
curl -s -u "API_KEY:$KEY" "https://intervals.icu/api/v1/athlete/$ATHLETE/activities?limit=10" \
  | python3 -c "
import sys, json
for a in json.load(sys.stdin):
    print(a['id'], a.get('start_date_local','')[:10], 'src=', a.get('source',''), a.get('name',''))
"

# 2. Pick a recent Zone Sense ride and substitute its ID below
ACT=i123456789

# 3. Check stream types — does any contain dfa, alpha, or ddfa?
curl -s -u "API_KEY:$KEY" "https://intervals.icu/api/v1/activity/$ACT/streams" \
  | python3 -c "
import sys, json
for s in json.load(sys.stdin):
    print(s.get('type'), '|', s.get('name'), '| len=', len(s.get('data', []) or []))
"

# 4. Check activity-level fields and intervals for DDFA
curl -s -u "API_KEY:$KEY" "https://intervals.icu/api/v1/activity/$ACT" \
  | python3 -m json.tool | grep -iE 'dfa|alpha|ddfa|hrv'

curl -s -u "API_KEY:$KEY" "https://intervals.icu/api/v1/activity/$ACT/intervals" \
  | python3 -m json.tool | grep -iE 'dfa|alpha|ddfa|hrv' | head -20
```

**What we're looking for in the output:**
- A stream with `type` containing `dfa`, `alpha`, or `ddfa` → Intervals.icu exposes Suunto DDFA, and we know the stream name to use
- A non-null `average_dfa_a1` field on intervals → Intervals.icu maps Suunto DDFA into the same slot as AlphaHRV (unlikely but possible)
- Nothing → Intervals.icu does not currently surface Suunto DDFA. The data is in the FIT file (per Suunto's API docs) but Intervals.icu doesn't expose it via API.

### Karoo: does veloVigil (or any Karoo HRV path) write something Intervals.icu surfaces?

```bash
# 1. List recent Karoo activities
curl -s -u "API_KEY:$KEY" "https://intervals.icu/api/v1/athlete/$ATHLETE/activities?limit=10" \
  | python3 -c "
import sys, json
for a in json.load(sys.stdin):
    src = a.get('source','')
    dev = a.get('device_name','')
    if 'KAROO' in src.upper() or 'KAROO' in dev.upper() or 'HAMMERHEAD' in src.upper():
        print(a['id'], a.get('start_date_local','')[:10], 'src=', src, 'dev=', dev, a.get('name',''))
"

# 2. Pick a Karoo ride (ideally one where veloVigil was running) and substitute below
ACT=i123456789

# 3. Same checks as Suunto: stream types, activity fields, intervals
curl -s -u "API_KEY:$KEY" "https://intervals.icu/api/v1/activity/$ACT/streams" \
  | python3 -c "
import sys, json
for s in json.load(sys.stdin):
    print(s.get('type'), '|', s.get('name'), '| len=', len(s.get('data', []) or []))
"

curl -s -u "API_KEY:$KEY" "https://intervals.icu/api/v1/activity/$ACT" \
  | python3 -m json.tool | grep -iE 'dfa|alpha|hrv|rr_'
```

**What we're looking for:**
- A `hrv` stream → Karoo + veloVigil is writing per-second HRV to the FIT and Intervals.icu picks it up. (This wouldn't be DFA a1 directly — it'd be RMSSD or similar — but it confirms the dev-field path works on Karoo.)
- A `dfa_a1` stream → veloVigil (or another Karoo extension) is writing DFA a1 directly. **If this exists, sync.py works on Karoo with zero changes.**
- Nothing → no Karoo extension is currently writing HRV-related fields that Intervals.icu surfaces. The path is theoretically viable but no app fills it yet.

### Phone fallback: does an uploaded `dfa_a1` CSV column become a `dfa_a1` stream?

This is the verification that determines whether the phone fallback path "just works" with Section 11.

**Prerequisites:** Intervals.icu Supporter subscription, an existing activity, a FatMaxxer or HRV Logger CSV from a parallel recording.

```bash
# 1. Pick a target activity (one you have a phone-app CSV for)
ACT=i123456789

# 2. Download the activity's existing streams CSV from the Intervals.icu UI
#    (Activity → Activity Data tab → "Download CSV")
#    Save as streams.csv

# 3. Merge the phone CSV's dfa_a1 column into streams.csv, aligned by timestamp.
#    A trivial Python script:
python3 << 'PY'
import csv, sys
# Read phone CSV (FatMaxxer or HRV Logger format — adjust column names as needed)
phone_dfa = {}  # timestamp -> dfa_a1 value
with open('phone_export.csv') as f:
    r = csv.DictReader(f)
    for row in r:
        # Adjust 'time' and 'dfa_a1' to match the phone app's actual column names
        ts = int(row['time'])
        phone_dfa[ts] = float(row['dfa_a1'])

# Read streams CSV, add dfa_a1 column, write merged
with open('streams.csv') as fin, open('streams_merged.csv', 'w', newline='') as fout:
    r = csv.DictReader(fin)
    fields = r.fieldnames + ['dfa_a1']
    w = csv.DictWriter(fout, fieldnames=fields)
    w.writeheader()
    for row in r:
        ts = int(float(row['time']))  # streams.csv uses 'time' in seconds-from-start
        row['dfa_a1'] = phone_dfa.get(ts, '')
        w.writerow(row)
print("Wrote streams_merged.csv")
PY

# 4. Upload streams_merged.csv via the Intervals.icu UI:
#    Activity → Activity Data tab → "Upload CSV"
#    UNTICK "Convert text to numbers, dates and formulas" — this is required for array-valued streams.

# 5. After upload, check if a dfa_a1 stream now exists on the activity:
curl -s -u "API_KEY:$KEY" "https://intervals.icu/api/v1/activity/$ACT/streams" \
  | python3 -c "
import sys, json
for s in json.load(sys.stdin):
    t = s.get('type')
    if t in ('dfa_a1', 'dfa', 'alpha1') or 'dfa' in str(t).lower():
        data = [x for x in (s.get('data') or []) if x is not None]
        print('FOUND:', t, '| nonnull=', len(data), '| sample=', data[:5])
        break
else:
    print('NO DFA STREAM. Stream types present:', [s.get('type') for s in json.load(open('/dev/stdin'))])
"
```

**What we're looking for:**
- `FOUND: dfa_a1 | nonnull=N | sample=[...]` → **Phone fallback works end-to-end with Section 11. No code changes needed.** The pipeline treats the merged stream identically to an AlphaHRV recording. This is the headline outcome.
- A different stream name (e.g. `custom_1`, `user_dfa`) → phone fallback works but `sync.py` needs a small mapping change to recognize the alternate name. We'd add the mapping.
- `NO DFA STREAM` → Intervals.icu doesn't ingest user-uploaded array streams the way we hoped. Phone fallback path is dead until Intervals.icu changes its CSV ingest, or we find a different upload route.

---

## Contribute

If you're on Suunto, Karoo, Wahoo, Coros, Polar, or trying the phone fallback, and you want DFA a1 to work in Section 11:

1. **Run the relevant discovery commands above.**
2. **Open a [GitHub issue](https://github.com/CrankAddict/section-11/issues)** with title `DFA a1 verification: <platform>`.
3. **Paste the full command output** (sanitized — no API keys, no athlete IDs you don't want public).
4. **Tell us your setup**: head unit model, strap, app versions, sync path to Intervals.icu (direct or via Strava — direct is required for any of this to work).

If the verification reveals a path that needs a small `sync.py` change (e.g. new stream name to map), we'll do it. If it reveals a contribution upstream is needed (e.g. veloVigil could write DFA a1), we'll either help draft the upstream PR or document what's needed clearly enough for someone else to.

We don't own non-Garmin hardware, so we can't verify any of this ourselves. Your output is the only way these paths get built.

---

## Honesty notes

- **None of the non-Garmin paths are currently verified end-to-end.** Section 11 supports Garmin + AlphaHRV. Everything else in this file is plausible-but-unverified, clearly labeled.
- **The Suunto DDFA path may never produce identical numbers to DFA a1.** Different algorithm. Even if Intervals.icu exposes Suunto DDFA, Section 11 would need a separate `DDFA a1 Protocol` section with its own threshold validation before it could be interpreted. We're not building that speculatively.
- **Phone fallback is paid.** Intervals.icu Supporter is required. There is no free non-Garmin path right now.
- **Wahoo, Coros, and Polar have no path that doesn't go through the phone fallback.** That's a Wahoo/Coros/Polar problem, not a Section 11 problem.
