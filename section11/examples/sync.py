#!/usr/bin/env python3
"""
Intervals.icu → GitHub/Local JSON Export
Exports training data for LLM access.
Supports both automated GitHub sync and manual local export.

Version 3.99 - DFA a1 Protocol: per-session dfa block in intervals.json (artifact-filtered avg,
  4-zone TIZ split with HR/power cross-references, drift, LT1/LT2 crossing-band estimates,
  quality gates). New generic streams fetcher infrastructure (_fetch_activity_streams). dfa_a1_profile
  in latest.json capability block (latest_session + trailing_by_sport with confidence + validation
  flags). Always emits dfa block when streams fetched, even if quality.sufficient is False, so the
  AI can distinguish "no AlphaHRV" from "AlphaHRV ran but unusable". Intervals retention 8d → 14d
  to support drift analysis across multiple AlphaHRV sessions. Sport scope: all interval families;
  threshold mapping (1.0/0.5) cycling-validated, other sports flagged validated=False.
  Requires AlphaHRV Connect IQ data field, direct Garmin sync (Strava strips dev fields).

Version 3.98 - Schema rename: derived_metrics.polarisation_index → easy_time_ratio (and _note).
  Disambiguates from Seiler polarization_index (Treff PI). Rename only — no formula or value change.

Version 3.97 - Readiness signal hygiene: low-side ACWR removed from readiness_decision ambers
  and ACWR alerts — low ACWR is a load-state/undertraining context signal, not a fatigue signal,
  and already surfaces via acwr_interpretation. RI amber now requires 2-day persistence (ri<0.7
  today AND yesterday) to filter single-night noise; red still fires on any single day <0.6.
  New derived metric: recovery_index_yesterday. ACWR high-side boundary unified across code and
  docs: >=1.3 amber/caution, >=1.5 red/danger (replaces mixed >/>= usage).

Version 3.96 - Course character fix: elevation_per_km as sole density metric (total elevation
  is distance-blind); absolute elevation thresholds removed. Climb-category upgrade retained for
  "flat with one big climb" cases.

Version 3.95 - Polyline + event metadata: 500m downsampled polyline in terrain_summary for
  weather/wind/pacing lookups. Start time (HH:MM) on events when set. Indoor flag passthrough.

Version 3.94 - Phase detection: live weekly rows from activities_28d. Replaces v3.89 single-week
  overlay with full 4-week bucketing — all weekly rows (TSS, primary_sport_tss, hard_days) computed
  fresh every run. CTL/ATL enriched from history.json as stable background. Eliminates the entire
  class of stale-row bugs (previously, completed weeks snapshotted mid-progress stayed frozen until
  history.json regeneration). recent_activities widened from 7d to 28d (activities_extended) so
  latest.json always covers the full window between history.json regenerations.

Version 3.93 - Route & Terrain Intelligence: GPX/TCX attachments on events parsed into routes.json.
  Climb/descent detection, course character, elevation_per_km. Cached by attachment ID.
  has_terrain flag on planned workouts and race calendar entries. GPX + TCX via stdlib
  xml.etree.ElementTree (zero new deps). FIT format stubbed. Elevation smoothing (50m window).
  Start trimming (2km local gradient) prevents flat approaches inflating climbs. Course character
  uses elevation_per_km + climb category upgrades. Hash-based cache invalidation:
  script_hash (SHA256 of sync.py) on routes.json, intervals.json, history.json — any code change
  auto-invalidates cached files on next run. activity_types order-preserving dedup (was set()).

Version 3.92 - Local-Sync: --update auto-clears history.json + intervals.json when sync.py
  changes. Prevents stale-schema bugs. Full data restored after 2 sync cycles.

Version 3.91 - Sustainability Profile: per-sport power/HR sustainability table for race estimation.
  42-day window, sport-filtered curves (power-curves + hr-curves per sport family). Cycling gets
  three model layers (actual MMP, Coggan duration factors, CP/W' model) with model_divergence_pct.
  Non-cycling power sports get actual MMP only. Indoor/outdoor source flag for cycling (max of
  Ride vs VirtualRide). Per-anchor: watts, W/kg, HR, %LTHR, source, date, recency. Block-level:
  coverage_ratio, ftp_staleness_days (cycling only). Weight fallback chain. capability namespace.

Version 3.90 - Sleep signal simplified: hours only. Sleep quality/score removed from readiness
  classification — they are device-derived composites of HRV + HR during sleep, already captured as
  independent signals. Quality still passes through in signal output as coaching context.

Version 3.89 - Phase detection current-week patch: overlay fresh CTL/TSS/hard_days/ACWR/monotony
  onto the current week's weekly_180d row at runtime, so phase classification always uses live data
  instead of stale history.json snapshot (up to 28 days old). Fixes phase flip caused by stale
  current-week row. Runtime only — does not write back to history.json. Respects week_start_day.

Version 3.88 - HR Curve Delta: max sustained HR comparison at 4 anchor durations (60s/300s/1200s/3600s)
  across two 28-day windows. New hr-curves API call (no sport filter — HR is cross-sport physiological).
  Data key is 'values' (not 'watts'). Rotation index: mean(60s,300s) - mean(1200s,3600s).
  Same capability namespace, same guards, same pattern as power_curve_delta.

Version 3.87–3.85 — Power curve delta, primary sport TSS filtering for phase detection, wellness field expansion
Version 3.84–3.80 — Activity description passthrough, per-sport zone preference, interval-level data, feel removed from readiness, orphan cleanup
Versions 3.7–3.79 — Phase detection v2, readiness decision, HRRc, week alignment, local sync pipeline, hash manifest, feel/RPE fix
Versions 3.3.0–3.6.5 — EF tracking, HR zone fallback, race calendar, durability, TID, alerts, history.json, smart fitness metrics
"""

import requests
import json
import os
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import base64
import math
import statistics
import hashlib
import zipfile
import tempfile
import shutil
import atexit
from collections import defaultdict
from pathlib import Path
import xml.etree.ElementTree as ET


class IntervalsSync:
    """Sync Intervals.icu data to GitHub repository or local file"""
    
    INTERVALS_BASE_URL = "https://intervals.icu/api/v1"
    GITHUB_API_URL = "https://api.github.com"
    FTP_HISTORY_FILE = "ftp_history.json"
    HISTORY_FILE = "history.json"
    UPSTREAM_REPO = "CrankAddict/section-11"
    CHANGELOG_FILE = "changelog.json"
    VERSION = "3.99"
    INTERVALS_FILE = "intervals.json"
    ROUTES_FILE = "routes.json"

    # Sport families eligible for interval-level data extraction.
    # Only structured sessions in these families are worth fetching
    # per-interval detail for. Walk, strength, yoga, other excluded.
    INTERVAL_SPORT_FAMILIES = {"cycling", "run", "ski", "rowing", "swim"}
    INTERVAL_SCAN_HOURS = 72    # Only scan recent activities for new intervals
    INTERVAL_RETENTION_DAYS = 14  # Keep cached intervals for 14 days (DFA drift analysis window)

    # --- DFA a1 Protocol (v3.99) ---
    # Per-session DFA a1 rollups computed from streams when AlphaHRV Connect IQ field
    # has written to the FIT and Intervals.icu surfaces dfa_a1 + artifacts streams.
    # Threshold mapping (1.0 / 0.5) is cycling-validated (Rowlands 2017, Gronwald 2020,
    # Mateo-March 2023). Other sports get rollups but validated=False.
    DFA_LT1 = 1.0                       # DFA a1 above this = below LT1 (true aerobic)
    DFA_LT2 = 0.5                       # DFA a1 below this = above LT2 (supra-threshold)
    DFA_LT1_BAND = 0.05                 # crossing window for LT1 estimate: 0.95-1.05
    DFA_LT2_BAND = 0.05                 # crossing window for LT2 estimate: 0.45-0.55
    DFA_MIN_CROSSING_DWELL_SECS = 60    # min seconds in crossing band to emit threshold estimate
    DFA_ARTIFACT_MAX_PCT = 5.0          # drop seconds where artifacts % exceeds this
    DFA_MIN_VALID_VALUE = 0.01          # exclude AlphaHRV sentinel zeros
    DFA_MIN_DURATION_SECS = 1200        # 20 min minimum valid data for sufficient=True
    DFA_DRIFT_INTERPRETABLE_MAX_LT2_PCT = 15.0  # if >15% time above LT2, drift is structural noise
    DFA_TRAILING_WINDOW_N = 7           # latest N AlphaHRV sessions for trailing window (≥6 needed for 'high' confidence)
    DFA_VALIDATED_SPORTS = {"cycling"}  # sports where 1.0/0.5 mapping is literature-validated

    # Sport family mapping for per-sport monotony calculation
    # Multi-sport athletes get inflated total monotony when cross-training
    # adds a consistent TSS floor across days. Per-sport monotony isolates
    # the actual load variation within each modality.
    SPORT_FAMILIES = {
        "Ride": "cycling",
        "VirtualRide": "cycling",
        "MountainBikeRide": "cycling",
        "GravelRide": "cycling",
        "EBikeRide": "cycling",
        "VirtualSki": "ski",
        "NordicSki": "ski",
        "Walk": "walk",
        "Hike": "walk",
        "Run": "run",
        "VirtualRun": "run",
        "TrailRun": "run",
        "Swim": "swim",
        "Rowing": "rowing",
        "WeightTraining": "strength",
        "Yoga": "other",
        "Workout": "other",
    }
    
    # Activity types that may contain location data in their name
    OUTDOOR_TYPES = {"Ride", "MountainBikeRide", "GravelRide", "EBikeRide",
                     "Run", "TrailRun", "NordicSki", "Walk", "Hike"}
    
    # Training week start day (Python weekday: Mon=0, Tue=1, Wed=2, Thu=3, Fri=4, Sat=5, Sun=6)
    # Default Monday (ISO). Override via .sync_config.json, WEEK_START env var, or --week-start CLI arg.
    WEEK_START_DAY = 0
    
    # --- Sustainability Profile (v3.91) ---
    # Race estimation lookup table: what power/HR is sustainable at each duration?
    SUSTAINABILITY_WINDOW_DAYS = 42
    
    # Per-sport anchor durations (seconds). Cycling covers long events; SkiErg/rowing are shorter.
    SUSTAINABILITY_ANCHORS = {
        "cycling": {"300s": 300, "600s": 600, "1200s": 1200, "1800s": 1800, "3600s": 3600, "5400s": 5400, "7200s": 7200},
        "ski":     {"60s": 60, "120s": 120, "300s": 300, "600s": 600, "1200s": 1200, "1800s": 1800},
        "rowing":  {"60s": 60, "120s": 120, "300s": 300, "600s": 600, "1200s": 1200, "1800s": 1800},
    }
    
    # Coggan duration factors — midpoints of published ranges. Cycling only.
    # Source: Allen & Coggan, Training and Racing with a Power Meter (3rd ed.)
    # Sustainable power as fraction of FTP by duration.
    COGGAN_DURATION_FACTORS = {
        300:  1.06,   # 5min:  ~106% FTP (range 100-112%)
        600:  0.97,   # 10min: ~97% FTP (range 94-100%)
        1200: 0.93,   # 20min: ~93% FTP (range 91-95%)
        1800: 0.90,   # 30min: ~90% FTP (range 88-93%)
        3600: 0.86,   # 60min: ~86% FTP (range 83-90%)
        5400: 0.82,   # 90min: ~82% FTP (range 78-85%)
        7200: 0.78,   # 2h:    ~78% FTP (range 75-82%)
    }
    
    # Activity types for sport-filtered power-curves fetch
    SUSTAINABILITY_POWER_TYPES = {
        "cycling": ["Ride", "VirtualRide"],
        "ski":     ["NordicSki", "VirtualSki"],
        "rowing":  ["Rowing"],
    }
    
    # Activity types for sport-filtered hr-curves fetch
    SUSTAINABILITY_HR_TYPES = {
        "cycling": ["Ride", "VirtualRide"],
        "ski":     ["NordicSki", "VirtualSki"],
        "rowing":  ["Rowing"],
    }
    
    def __init__(self, athlete_id: str, intervals_api_key: str, github_token: str = None, 
                 github_repo: str = None, debug: bool = False, week_start_day: int = None,
                 zone_preference: dict = None):
        self.athlete_id = athlete_id
        self.intervals_auth = base64.b64encode(f"API_KEY:{intervals_api_key}".encode()).decode()
        self.github_token = github_token
        self.github_repo = github_repo
        self.debug = debug
        self.script_dir = Path(__file__).parent
        self.data_dir = Path.cwd()  # Data files (history.json, ftp_history.json) write to caller's working directory
        self.week_start_day = week_start_day if week_start_day is not None else self.WEEK_START_DAY
        self.zone_preference = zone_preference or {}  # {"run": "hr", "cycling": "power", ...}
        self._cached_script_hash = None  # lazy-computed
    
    @property
    def script_hash(self) -> str:
        """SHA256 of sync.py itself. Used to invalidate cached files on any code change."""
        if self._cached_script_hash is None:
            script_path = Path(__file__).resolve()
            h = hashlib.sha256()
            with open(script_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    h.update(chunk)
            self._cached_script_hash = h.hexdigest()[:12]  # short hash, sufficient for change detection
        return self._cached_script_hash
    
    def _intervals_get(self, endpoint: str, params: Dict = None) -> Dict:
        """Fetch from Intervals.icu API"""
        if endpoint:
            url = f"{self.INTERVALS_BASE_URL}/athlete/{self.athlete_id}/{endpoint}"
        else:
            url = f"{self.INTERVALS_BASE_URL}/athlete/{self.athlete_id}"
        headers = {
            "Authorization": f"Basic {self.intervals_auth}",
            "Accept": "application/json"
        }
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return response.json()

    def _get_activity_messages(self, activity_id: str) -> List[str]:
        """Fetch messages/notes for a completed activity. Returns list of text strings."""
        url = f"{self.INTERVALS_BASE_URL}/activity/{activity_id}/messages"
        headers = {
            "Authorization": f"Basic {self.intervals_auth}",
            "Accept": "application/json"
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            messages = response.json()
            if isinstance(messages, list):
                return [m.get("content", m.get("text", "")) for m in messages if (m.get("content") or m.get("text", "")).strip()]
            return []
        except Exception:
            return []
    
    def _fetch_activity_intervals(self, activity_id: str) -> List[Dict]:
        """Fetch interval segments for a single activity. Returns icu_intervals list or empty list on failure."""
        url = f"{self.INTERVALS_BASE_URL}/activity/{activity_id}"
        headers = {
            "Authorization": f"Basic {self.intervals_auth}",
            "Accept": "application/json"
        }
        try:
            response = requests.get(url, headers=headers, params={"intervals": "true"})
            response.raise_for_status()
            data = response.json()
            intervals = data.get("icu_intervals", [])
            if isinstance(intervals, list):
                return intervals
            return []
        except Exception as e:
            if self.debug:
                print(f"    ⚠️  Could not fetch intervals for {activity_id}: {e}")
            return []

    def _fetch_activity_streams(self, activity_id: str, types: List[str]) -> Dict[str, List]:
        """
        Fetch per-second streams for a single activity.

        Generic streams fetcher for any rollup metric that needs second-by-second data.
        Returns a dict keyed by stream type, value is the data list. Streams not present
        in the response are simply absent from the returned dict.

        Returns empty dict on 404/exception. Many activities won't have AlphaHRV-derived
        streams (no Connect IQ field installed, sourced via Strava which strips dev fields,
        wrong sport, etc.) — that's expected and not an error.

        Note on cache invalidation: streams are fetched once per activity. If the underlying
        FIT is reprocessed in AlphaHRV's mobile app and re-uploaded, the cached rollup will
        be stale. Rare in practice; workaround is to delete intervals.json.
        """
        url = f"{self.INTERVALS_BASE_URL}/activity/{activity_id}/streams"
        headers = {
            "Authorization": f"Basic {self.intervals_auth}",
            "Accept": "application/json"
        }
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                return {}
            wanted = set(types)
            out = {}
            for s in data:
                stype = s.get("type")
                if stype in wanted:
                    sdata = s.get("data")
                    if isinstance(sdata, list):
                        out[stype] = sdata
            return out
        except Exception as e:
            if self.debug:
                print(f"    ⚠️  Could not fetch streams for {activity_id}: {e}")
            return {}

    def _compute_dfa_block(self, streams: Dict[str, List]) -> Optional[Dict]:
        """
        Compute per-session DFA a1 rollup from raw streams.

        Inputs: streams dict from _fetch_activity_streams, expected keys:
          dfa_a1, artifacts, heartrate, watts (heartrate/watts optional but degrade output)

        Returns the dfa block dict, or None if dfa_a1 stream is absent entirely
        (i.e. AlphaHRV did not record on this activity).

        When dfa_a1 IS present but data is insufficient to interpret (too short,
        too noisy), returns a block with quality.sufficient=False so the AI can
        distinguish "no AlphaHRV" (None → no dfa key in output) from "AlphaHRV
        ran but unusable" (block present, sufficient=False).

        Filtering rules (in order):
          1. Drop seconds where dfa_a1 < DFA_MIN_VALID_VALUE (AlphaHRV sentinel zeros)
          2. Drop seconds where artifacts > DFA_ARTIFACT_MAX_PCT (5%, Altini convention)
        Both filters applied jointly to dfa_a1, hr, watts so they stay aligned.
        """
        dfa_stream = streams.get("dfa_a1")
        if not dfa_stream:
            return None  # no AlphaHRV recording on this activity

        artifacts_stream = streams.get("artifacts") or [0.0] * len(dfa_stream)
        hr_stream = streams.get("heartrate") or [None] * len(dfa_stream)
        watts_stream = streams.get("watts") or [None] * len(dfa_stream)

        # Align all streams to dfa_a1 length (defensive — should already match)
        n = len(dfa_stream)
        if len(artifacts_stream) != n:
            artifacts_stream = (artifacts_stream + [0.0] * n)[:n]
        if len(hr_stream) != n:
            hr_stream = (hr_stream + [None] * n)[:n]
        if len(watts_stream) != n:
            watts_stream = (watts_stream + [None] * n)[:n]

        # Apply filters
        valid_dfa, valid_hr, valid_watts = [], [], []
        artifact_sum = 0.0
        artifact_count = 0
        for i in range(n):
            d = dfa_stream[i]
            a = artifacts_stream[i]
            if a is not None:
                artifact_sum += a
                artifact_count += 1
            if d is None or d < self.DFA_MIN_VALID_VALUE:
                continue
            if a is not None and a > self.DFA_ARTIFACT_MAX_PCT:
                continue
            valid_dfa.append(d)
            valid_hr.append(hr_stream[i])
            valid_watts.append(watts_stream[i])

        valid_secs = len(valid_dfa)
        total_secs = n
        valid_pct = round(100.0 * valid_secs / total_secs, 1) if total_secs else 0.0
        artifact_rate_avg = round(artifact_sum / artifact_count, 2) if artifact_count else None
        sufficient = valid_secs >= self.DFA_MIN_DURATION_SECS

        quality = {
            "valid_secs": valid_secs,
            "total_secs": total_secs,
            "valid_pct": valid_pct,
            "artifact_rate_avg": artifact_rate_avg,
            "sufficient": sufficient,
        }

        if not sufficient:
            # Emit minimal block — AI sees AlphaHRV ran but data unusable
            return {
                "avg": None,
                "p25": None, "p50": None, "p75": None,
                "tiz_below_lt1": None,
                "tiz_lt1_transition": None,
                "tiz_transition_lt2": None,
                "tiz_above_lt2": None,
                "drift": None,
                "lt1_crossing": None,
                "lt2_crossing": None,
                "quality": quality,
            }

        # Sufficient — full rollup
        sorted_dfa = sorted(valid_dfa)
        avg = round(sum(valid_dfa) / valid_secs, 3)
        p25 = round(sorted_dfa[valid_secs // 4], 3)
        p50 = round(sorted_dfa[valid_secs // 2], 3)
        p75 = round(sorted_dfa[(valid_secs * 3) // 4], 3)

        # 4-band TIZ with HR/power cross-references per band
        def _band_stats(predicate):
            secs = 0
            hr_sum, hr_n = 0, 0
            w_sum, w_n = 0, 0
            for i in range(valid_secs):
                if predicate(valid_dfa[i]):
                    secs += 1
                    if valid_hr[i] is not None:
                        hr_sum += valid_hr[i]
                        hr_n += 1
                    if valid_watts[i] is not None:
                        w_sum += valid_watts[i]
                        w_n += 1
            if secs == 0:
                return None
            return {
                "secs": secs,
                "pct": round(100.0 * secs / valid_secs, 1),
                "avg_hr": round(hr_sum / hr_n) if hr_n else None,
                "avg_watts": round(w_sum / w_n) if w_n else None,
            }

        tiz_below_lt1 = _band_stats(lambda d: d > self.DFA_LT1)
        tiz_lt1_transition = _band_stats(lambda d: 0.75 <= d <= self.DFA_LT1)
        tiz_transition_lt2 = _band_stats(lambda d: self.DFA_LT2 <= d < 0.75)
        tiz_above_lt2 = _band_stats(lambda d: d < self.DFA_LT2)

        # Drift: first-third vs last-third of valid data
        third = valid_secs // 3
        if third >= 60:  # need at least 60s per third for meaningful drift
            first_third = valid_dfa[:third]
            last_third = valid_dfa[-third:]
            first_avg = round(sum(first_third) / len(first_third), 3)
            last_avg = round(sum(last_third) / len(last_third), 3)
            drift_delta = round(last_avg - first_avg, 3)
            # Drift is interpretable only on steady-state work — if significant time
            # was spent above LT2, the session has hard intervals and drift is structural
            above_lt2_pct = tiz_above_lt2["pct"] if tiz_above_lt2 else 0.0
            interpretable = above_lt2_pct <= self.DFA_DRIFT_INTERPRETABLE_MAX_LT2_PCT
            drift = {
                "first_third_avg": first_avg,
                "last_third_avg": last_avg,
                "delta": drift_delta,
                "interpretable": interpretable,
            }
        else:
            drift = None

        # LT1 / LT2 crossing-band estimates (the actually-coachable threshold candidates)
        def _crossing_stats(center, band):
            lo, hi = center - band, center + band
            secs = 0
            hr_sum, hr_n = 0, 0
            w_sum, w_n = 0, 0
            for i in range(valid_secs):
                if lo <= valid_dfa[i] <= hi:
                    secs += 1
                    if valid_hr[i] is not None:
                        hr_sum += valid_hr[i]
                        hr_n += 1
                    if valid_watts[i] is not None:
                        w_sum += valid_watts[i]
                        w_n += 1
            if secs < self.DFA_MIN_CROSSING_DWELL_SECS:
                return {"secs_in_band": secs, "avg_hr": None, "avg_watts": None}
            return {
                "secs_in_band": secs,
                "avg_hr": round(hr_sum / hr_n) if hr_n else None,
                "avg_watts": round(w_sum / w_n) if w_n else None,
            }

        lt1_crossing = _crossing_stats(self.DFA_LT1, self.DFA_LT1_BAND)
        lt2_crossing = _crossing_stats(self.DFA_LT2, self.DFA_LT2_BAND)

        return {
            "avg": avg,
            "p25": p25, "p50": p50, "p75": p75,
            "tiz_below_lt1": tiz_below_lt1,
            "tiz_lt1_transition": tiz_lt1_transition,
            "tiz_transition_lt2": tiz_transition_lt2,
            "tiz_above_lt2": tiz_above_lt2,
            "drift": drift,
            "lt1_crossing": lt1_crossing,
            "lt2_crossing": lt2_crossing,
            "quality": quality,
        }

    
    def _generate_intervals(self, activities: List[Dict], anonymize: bool = False) -> set:
        """
        Generate intervals.json with incremental caching.
        
        First run (no cache): scans full retention window (14 days) to backfill.
        Subsequent runs: scans recent activities (72h) for new sessions only.
        Fetches per-interval data for new qualifying activities, merges
        with cached data, and purges entries older than 14 days.

        DFA a1 (v3.99): for each new qualifying activity, also fetches streams
        (dfa_a1, artifacts, heartrate, watts) and computes a per-session dfa block.
        Attached to the activity entry as 'dfa' key when AlphaHRV recorded.

        Anonymization (v3.99 fix): when anonymize=True, outdoor activity names are
        replaced with "Training Session" matching _format_activities behaviour.
        Without this, intervals.json would leak raw outdoor names while latest.json
        anonymizes them — a privacy consistency bug.

        Returns set of activity IDs that have interval data (for has_intervals flag).
        """
        now = datetime.now()
        retention_cutoff = (now - timedelta(days=self.INTERVAL_RETENTION_DAYS)).strftime("%Y-%m-%d")
        
        # Load existing cache
        intervals_path = self.data_dir / self.INTERVALS_FILE
        cached = {"activities": []}
        first_run = not intervals_path.exists()
        if not first_run:
            try:
                with open(intervals_path, 'r') as f:
                    cached = json.load(f)
                # Invalidate cache if sync.py changed
                if cached.get("script_hash") != self.script_hash:
                    if self.debug:
                        print(f"    🔄 intervals.json stale (sync.py changed), re-scanning all")
                    cached = {"activities": []}
                    first_run = True
            except Exception as e:
                if self.debug:
                    print(f"    ⚠️  Could not read intervals.json: {e}")
                cached = {"activities": []}
                first_run = True
        
        # First run: backfill full retention window (14 days). Subsequent: scan 72h only.
        if first_run:
            scan_cutoff = retention_cutoff
            print("    First run — scanning 14 days for interval data...")
        else:
            scan_cutoff = (now - timedelta(hours=self.INTERVAL_SCAN_HOURS)).strftime("%Y-%m-%d")
        
        cached_ids = {a["activity_id"] for a in cached.get("activities", [])}
        
        # Filter activities to scan window + sport family whitelist.
        # NOTE (v3.99): interval_summary requirement removed. Pure endurance rides
        # without structured intervals are exactly where DFA a1 is most valuable
        # (steady-state drift detection, LT1 calibration). We attempt both intervals
        # AND streams fetches; entry is emitted if either yields data.
        candidates = []
        for act in activities:
            date_str = act.get("start_date_local", "")[:10]
            if date_str < scan_cutoff:
                continue
            act_type = act.get("type", "")
            family = self.SPORT_FAMILIES.get(act_type)
            if family not in self.INTERVAL_SPORT_FAMILIES:
                continue
            act_id = act.get("id")
            if act_id in cached_ids:
                continue
            candidates.append(act)
        
        # Fetch intervals for new qualifying activities
        new_entries = []
        for act in candidates:
            act_id = act.get("id")
            print(f"    Fetching intervals/streams for {act.get('name', act_id)}...")
            raw_intervals = self._fetch_activity_intervals(act_id)
            # raw_intervals may be empty for unstructured endurance rides — that's fine,
            # we still attempt streams below for DFA a1.

            # Format interval segments (empty list if no structured intervals exist)
            segments = []
            for iv in raw_intervals:
                segment = {
                    "type": iv.get("type"),
                    "label": iv.get("group_id"),
                    "duration_secs": iv.get("elapsed_time"),
                    "avg_power": iv.get("average_watts"),
                    "max_power": iv.get("max_watts"),
                    "avg_hr": iv.get("average_heartrate"),
                    "max_hr": iv.get("max_heartrate"),
                    "avg_cadence": iv.get("average_cadence"),
                    "zone": iv.get("zone"),
                    "w_bal": iv.get("w_bal"),
                    "training_load": iv.get("training_load"),
                    "decoupling": iv.get("decoupling"),
                    # Per-interval avg_dfa_a1 is the Intervals.icu-computed value (UNFILTERED).
                    # The session-level dfa.avg below IS artifact-filtered. Don't try to
                    # reconcile the two — they use different denominators by design.
                    "avg_dfa_a1": iv.get("average_dfa_a1"),
                }
                # Strip None values to keep output lean
                segment = {k: v for k, v in segment.items() if v is not None}
                segments.append(segment)

            # DFA a1 session-level rollup (v3.99) — fetch streams, compute block.
            # None means no AlphaHRV recording on this activity (skip dfa key entirely).
            # A block with quality.sufficient=False means AlphaHRV ran but data unusable.
            dfa_block = None
            try:
                streams = self._fetch_activity_streams(
                    act_id, ["dfa_a1", "artifacts", "heartrate", "watts"]
                )
                if streams.get("dfa_a1"):
                    dfa_block = self._compute_dfa_block(streams)
            except Exception as e:
                if self.debug:
                    print(f"    ⚠️  DFA a1 computation failed for {act_id}: {e}")
                dfa_block = None

            # Emit entry if EITHER segments OR dfa block exists.
            # Pure endurance rides with AlphaHRV: no segments, has dfa.
            # Structured intervals without AlphaHRV: has segments, no dfa.
            # Both: full entry. Neither: skip silently.
            if segments or dfa_block is not None:
                entry_name = act.get("name", "")
                if anonymize and act.get("type", "") in self.OUTDOOR_TYPES:
                    entry_name = "Training Session"
                entry = {
                    "activity_id": act_id,
                    "date": act.get("start_date_local", "")[:10],
                    "type": act.get("type", "Unknown"),
                    "name": entry_name,
                    "interval_summary": act.get("interval_summary"),
                    "intervals": segments
                }
                if dfa_block is not None:
                    entry["dfa"] = dfa_block
                new_entries.append(entry)
        
        if new_entries:
            print(f"    ✅ Fetched intervals for {len(new_entries)} new activit{'y' if len(new_entries) == 1 else 'ies'}")
        
        # Merge: keep cached entries within retention window + new entries
        retained = [a for a in cached.get("activities", []) if a.get("date", "") >= retention_cutoff]
        all_entries = retained + new_entries
        
        # Build intervals.json
        self._intervals_data = {
            "generated_at": now.isoformat(),
            "version": self.VERSION,
            "script_hash": self.script_hash,
            "scan_hours": self.INTERVAL_SCAN_HOURS,
            "retention_days": self.INTERVAL_RETENTION_DAYS,
            "activities": all_entries
        }
        
        # Return all activity IDs that have interval data
        return {a["activity_id"] for a in all_entries}
    
    # ── Route & Terrain Intelligence (v3.93) ─────────────────────────────
    
    def _generate_terrain(self, events: List[Dict]) -> Dict:
        """
        Parse GPX/TCX attachments on events into routes.json.
        
        Scans all events for attachments, downloads and parses route files,
        produces terrain_summary with climb/descent detection. Caches by
        attachment ID to avoid re-downloading unchanged files.
        
        Returns dict of event_id → terrain_summary for has_terrain flags.
        """
        routes_path = self.data_dir / self.ROUTES_FILE
        
        # Load existing cache
        cached = {"events": []}
        if routes_path.exists():
            try:
                with open(routes_path, 'r') as f:
                    cached = json.load(f)
                # Invalidate cache if sync.py changed (schema may differ)
                if cached.get("script_hash") != self.script_hash:
                    if self.debug:
                        print(f"    🔄 routes.json stale (sync.py changed), re-parsing all")
                    cached = {"events": []}
            except Exception as e:
                if self.debug:
                    print(f"    ⚠️  Could not read routes.json: {e}")
                cached = {"events": []}
        
        # Build lookup of cached attachment_id → terrain entry
        cached_by_attachment = {}
        for entry in cached.get("events", []):
            aid = entry.get("attachment_id")
            if aid:
                cached_by_attachment[aid] = entry
        
        # Scan events for attachments
        new_entries = []
        for evt in events:
            attachments = evt.get("attachments")
            if not attachments:
                continue
            
            evt_id = evt.get("id")
            evt_name = evt.get("name", "Unnamed")
            evt_date = (evt.get("start_date_local") or "")[:10]
            evt_category = evt.get("category", "")
            
            # Start time: HH:MM when set (not midnight)
            evt_start_time = None
            raw_start = evt.get("start_date_local") or ""
            if "T" in raw_start:
                time_part = raw_start.split("T")[1][:5]
                if time_part != "00:00":
                    evt_start_time = time_part
            
            for att in attachments:
                att_id = att.get("id")
                filename = att.get("filename", "")
                url = att.get("url", "")
                
                if not att_id or not url:
                    continue
                
                # Skip non-route files by extension
                ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
                if ext not in ("gpx", "tcx", "fit"):
                    continue
                
                # Check cache — reuse if attachment ID unchanged
                if att_id in cached_by_attachment:
                    entry = cached_by_attachment[att_id].copy()
                    # Update event metadata (name/date may change)
                    entry["event_id"] = evt_id
                    entry["event_name"] = evt_name
                    entry["event_date"] = evt_date
                    entry["category"] = evt_category
                    if evt_start_time:
                        entry["start_time"] = evt_start_time
                    else:
                        entry.pop("start_time", None)
                    new_entries.append(entry)
                    if self.debug:
                        print(f"    ✓ Cached terrain: {evt_name} ({filename})")
                    continue
                
                # Download and parse
                if self.debug:
                    print(f"    ↓ Downloading: {filename} for {evt_name}")
                
                terrain_summary = self._download_and_parse_route(url, filename)
                
                entry = {
                    "event_id": evt_id,
                    "event_name": evt_name,
                    "event_date": evt_date,
                    "category": evt_category,
                    "attachment_id": att_id,
                    "filename": filename,
                    "terrain_summary": terrain_summary
                }
                if evt_start_time:
                    entry["start_time"] = evt_start_time
                new_entries.append(entry)
        
        # Build routes.json
        self._routes_data = {
            "generated_at": datetime.now().isoformat(),
            "sync_version": self.VERSION,
            "script_hash": self.script_hash,
            "events": new_entries
        }
        
        # Return event_id → True for has_terrain flags
        return {e["event_id"] for e in new_entries if e.get("terrain_summary")}
    
    def _download_and_parse_route(self, url: str, filename: str) -> Optional[Dict]:
        """Download a route file attachment and parse it into a terrain_summary."""
        try:
            response = requests.get(url, timeout=30)
            if response.status_code != 200:
                return {"error": f"download failed (HTTP {response.status_code})"}
            content = response.content
        except Exception as e:
            return {"error": f"download failed: {str(e)[:100]}"}
        
        if not content or len(content) < 50:
            return {"error": "empty or invalid file"}
        
        return self._parse_route_file(content, filename)
    
    def _parse_route_file(self, content: bytes, filename: str) -> Optional[Dict]:
        """Detect route file format and dispatch to parser."""
        text_start = content[:200].decode("utf-8", errors="ignore").strip()
        
        if text_start.startswith("<?xml") or text_start.startswith("<gpx") or "<gpx" in text_start[:500]:
            return self._parse_gpx(content)
        elif "<TrainingCenterDatabase" in text_start or "TrainingCenterDatabase" in content[:500].decode("utf-8", errors="ignore"):
            return self._parse_tcx(content)
        elif content[:2] == b'.F' or content[:4] == b'\x0e\x10\xd9\x07':
            # FIT binary magic bytes
            return {"error": "FIT format not yet supported"}
        else:
            # Fall back to extension
            ext = filename.lower().rsplit(".", 1)[-1] if "." in filename else ""
            if ext == "gpx":
                return self._parse_gpx(content)
            elif ext == "tcx":
                return self._parse_tcx(content)
            elif ext == "fit":
                return {"error": "FIT format not yet supported"}
            return {"error": f"unrecognized route file format"}
    
    def _parse_gpx(self, content: bytes) -> Optional[Dict]:
        """Parse GPX file into trackpoints, then analyze terrain."""
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            return {"error": f"GPX parse error: {str(e)[:100]}"}
        
        # Handle namespace
        ns = ""
        tag = root.tag
        if "}" in tag:
            ns = tag[:tag.index("}") + 1]
        
        trackpoints = []
        for trkpt in root.iter(f"{ns}trkpt"):
            lat = trkpt.get("lat")
            lon = trkpt.get("lon")
            ele_elem = trkpt.find(f"{ns}ele")
            if lat and lon:
                tp = {"lat": float(lat), "lon": float(lon)}
                if ele_elem is not None and ele_elem.text:
                    try:
                        tp["ele"] = float(ele_elem.text)
                    except ValueError:
                        pass
                trackpoints.append(tp)
        
        if len(trackpoints) < 2:
            return {"error": "insufficient trackpoints"}
        
        return self._analyze_terrain(trackpoints)
    
    def _parse_tcx(self, content: bytes) -> Optional[Dict]:
        """Parse TCX file into trackpoints, then analyze terrain."""
        try:
            root = ET.fromstring(content)
        except ET.ParseError as e:
            return {"error": f"TCX parse error: {str(e)[:100]}"}
        
        # Handle namespace
        ns = ""
        tag = root.tag
        if "}" in tag:
            ns = tag[:tag.index("}") + 1]
        
        trackpoints = []
        for tp_elem in root.iter(f"{ns}Trackpoint"):
            pos = tp_elem.find(f"{ns}Position")
            if pos is None:
                continue
            lat_elem = pos.find(f"{ns}LatitudeDegrees")
            lon_elem = pos.find(f"{ns}LongitudeDegrees")
            alt_elem = tp_elem.find(f"{ns}AltitudeMeters")
            
            if lat_elem is not None and lon_elem is not None:
                try:
                    tp = {"lat": float(lat_elem.text), "lon": float(lon_elem.text)}
                    if alt_elem is not None and alt_elem.text:
                        tp["ele"] = float(alt_elem.text)
                    trackpoints.append(tp)
                except (ValueError, TypeError):
                    continue
        
        if len(trackpoints) < 2:
            return {"error": "insufficient trackpoints"}
        
        return self._analyze_terrain(trackpoints)
    
    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Haversine distance in meters between two GPS coordinates."""
        R = 6371000  # Earth radius in meters
        phi1, phi2 = math.radians(lat1), math.radians(lat2)
        dphi = math.radians(lat2 - lat1)
        dlam = math.radians(lon2 - lon1)
        a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
        return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    
    def _analyze_terrain(self, trackpoints: List[Dict]) -> Dict:
        """
        Analyze trackpoints into terrain_summary.
        
        Computes: total distance, total elevation gain, climb/descent detection,
        course character, elevation_per_km. Elevation smoothed with rolling
        window (~50m) before gradient calculation to reduce GPS jitter.
        """
        has_elevation = any("ele" in tp for tp in trackpoints)
        
        # Compute cumulative distance and collect elevation
        cum_dist = [0.0]  # cumulative distance in meters
        for i in range(1, len(trackpoints)):
            d = self._haversine(
                trackpoints[i - 1]["lat"], trackpoints[i - 1]["lon"],
                trackpoints[i]["lat"], trackpoints[i]["lon"]
            )
            cum_dist.append(cum_dist[-1] + d)
        
        total_distance_m = cum_dist[-1]
        total_distance_km = round(total_distance_m / 1000, 1)
        
        if not has_elevation or total_distance_m < 100:
            return {
                "source": "gpx_attachment" if has_elevation else "gpx_attachment_no_elevation",
                "total_distance_km": total_distance_km,
                "total_elevation_m": 0,
                "elevation_per_km": 0.0,
                "course_character": "flat",
                "climbs": [],
                "descents": []
            } if not has_elevation else None
        
        # Smooth elevation: rolling window ~50m of distance
        raw_ele = [tp.get("ele", 0.0) for tp in trackpoints]
        smoothed_ele = list(raw_ele)  # copy
        SMOOTH_WINDOW_M = 50.0
        
        for i in range(len(trackpoints)):
            # Find indices within ±SMOOTH_WINDOW_M/2 of current point
            lo, hi = i, i
            while lo > 0 and cum_dist[i] - cum_dist[lo - 1] < SMOOTH_WINDOW_M / 2:
                lo -= 1
            while hi < len(trackpoints) - 1 and cum_dist[hi + 1] - cum_dist[i] < SMOOTH_WINDOW_M / 2:
                hi += 1
            if lo < hi:
                smoothed_ele[i] = sum(raw_ele[lo:hi + 1]) / (hi - lo + 1)
        
        # Total elevation gain (from smoothed)
        total_gain = 0.0
        for i in range(1, len(smoothed_ele)):
            diff = smoothed_ele[i] - smoothed_ele[i - 1]
            if diff > 0:
                total_gain += diff
        total_elevation_m = round(total_gain)
        
        elevation_per_km = round(total_elevation_m / total_distance_km, 1) if total_distance_km > 0 else 0.0
        
        # Detect climbs and descents
        # Entry gradient is low (1.5%) to catch long gradual climbs like Brocken.
        # Post-filter by elevation gain: segments with <100m gain AND <3% avg are
        # filtered out to avoid detecting gentle inclines as "climbs."
        raw_climbs = self._detect_segments(trackpoints, cum_dist, smoothed_ele, min_gradient=1.5, min_distance=500.0, ascending=True)
        climbs = [c for c in raw_climbs if c["elevation_m"] >= 100 or c["avg_gradient_pct"] >= 3.0]
        raw_descents = self._detect_segments(trackpoints, cum_dist, smoothed_ele, min_gradient=1.5, min_distance=500.0, ascending=False)
        descents = [d for d in raw_descents if abs(d["elevation_m"]) >= 100 or abs(d["avg_gradient_pct"]) >= 3.0]
        
        # Course character — elevation density (m/km) only.
        # Total elevation is distance-blind: 2000m over 300km is rolling,
        # not hilly. Climb category upgrades handle "flat with one big climb."
        if elevation_per_km >= 30:
            course_character = "mountain"
        elif elevation_per_km >= 20:
            course_character = "hilly"
        elif elevation_per_km >= 5:
            course_character = "rolling"
        else:
            course_character = "flat"
        
        # Upgrade based on climb severity
        max_category = None
        for c in climbs:
            cat = c.get("category")
            if cat in ("HC", "Cat 1", "Cat 2"):
                max_category = "hilly"
                break
        if max_category == "hilly" and course_character in ("flat", "rolling"):
            course_character = "hilly"
        
        # Downsample trackpoints at 500m intervals for polyline
        POLYLINE_INTERVAL_M = 500.0
        polyline = []
        next_threshold = 0.0
        for i, tp in enumerate(trackpoints):
            if cum_dist[i] >= next_threshold or i == 0 or i == len(trackpoints) - 1:
                km = round(cum_dist[i] / 1000, 1)
                pt = [km, round(tp["lat"], 5), round(tp["lon"], 5)]
                if has_elevation:
                    pt.append(round(smoothed_ele[i]))
                polyline.append(pt)
                if i == 0:
                    next_threshold = POLYLINE_INTERVAL_M
                else:
                    next_threshold = cum_dist[i] + POLYLINE_INTERVAL_M
        
        return {
            "source": "gpx_attachment",
            "total_distance_km": total_distance_km,
            "total_elevation_m": total_elevation_m,
            "elevation_per_km": elevation_per_km,
            "course_character": course_character,
            "climbs": climbs,
            "descents": descents,
            "polyline": polyline
        }
    
    def _detect_segments(self, trackpoints: List[Dict], cum_dist: List[float],
                         smoothed_ele: List[float], min_gradient: float,
                         min_distance: float, ascending: bool) -> List[Dict]:
        """
        Detect sustained climb or descent segments using chunk-based analysis.
        
        Divides route into ~200m chunks, classifies each by gradient, then finds
        contiguous climbing/descending runs. Tolerates brief flats and small dips
        within a climb (real climbs have false flats and switchbacks). A climb ends
        when elevation drops >50m from the local high water mark, indicating a
        genuine descent, not a brief dip.
        """
        CHUNK_M = 200  # chunk size for gradient classification
        DIP_TOLERANCE_M = 50  # max elevation loss before ending a climb
        
        n = len(trackpoints)
        if n < 2 or cum_dist[-1] < CHUNK_M:
            return []
        
        # Build chunks: each has start_idx, end_idx, gradient, distance, ele_change
        chunks = []
        ci = 0
        while ci < n - 1:
            cj = ci + 1
            while cj < n and cum_dist[cj] - cum_dist[ci] < CHUNK_M:
                cj += 1
            if cj >= n:
                cj = n - 1
            if cj <= ci:
                break
            
            chunk_dist = cum_dist[cj] - cum_dist[ci]
            chunk_ele = smoothed_ele[cj] - smoothed_ele[ci]
            chunk_grad = (chunk_ele / chunk_dist * 100) if chunk_dist > 10 else 0
            
            chunks.append({
                "si": ci, "ei": cj,
                "dist": chunk_dist, "ele": chunk_ele, "grad": chunk_grad
            })
            ci = cj
        
        if not chunks:
            return []
        
        # Find climbing or descending segments using high-water-mark logic
        segments = []
        i = 0
        
        while i < len(chunks):
            c = chunks[i]
            
            # Look for start of a potential segment
            if ascending and c["grad"] < 1.0:
                i += 1
                continue
            elif not ascending and c["grad"] > -1.0:
                i += 1
                continue
            
            # Start tracking a segment
            seg_start_idx = c["si"]
            seg_start_ele = smoothed_ele[seg_start_idx]
            
            if ascending:
                high_mark = seg_start_ele
                high_mark_chunk = i
            else:
                low_mark = seg_start_ele
                low_mark_chunk = i
            
            j = i
            while j < len(chunks):
                current_ele = smoothed_ele[chunks[j]["ei"]]
                
                if ascending:
                    if current_ele > high_mark:
                        high_mark = current_ele
                        high_mark_chunk = j
                    # End if we've dropped too far from high water mark
                    if high_mark - current_ele > DIP_TOLERANCE_M:
                        break
                else:
                    if current_ele < low_mark:
                        low_mark = current_ele
                        low_mark_chunk = j
                    # End if we've risen too far from low water mark
                    if current_ele - low_mark > DIP_TOLERANCE_M:
                        break
                j += 1
            
            # Determine segment boundaries
            if ascending:
                seg_end_idx = chunks[high_mark_chunk]["ei"]
            else:
                seg_end_idx = chunks[low_mark_chunk]["ei"]
            
            # Trim flat approach: advance start until the LOCAL gradient
            # (over the next ~1km) shows sustained climbing. Prevents valley
            # roads with slight uphill trend being included in mountain climbs.
            LOCAL_TRIM_DIST = 2000  # look 2km ahead for local gradient check
            LOCAL_TRIM_GRAD = 2.5   # minimum local gradient to start the climb
            if ascending:
                for t in range(i, min(high_mark_chunk, len(chunks))):
                    t_start = chunks[t]["si"]
                    # Find point ~1km ahead
                    ahead_idx = t_start
                    for ai in range(t_start + 1, min(chunks[high_mark_chunk]["ei"] + 1, len(cum_dist))):
                        if cum_dist[ai] - cum_dist[t_start] >= LOCAL_TRIM_DIST:
                            ahead_idx = ai
                            break
                    if ahead_idx > t_start:
                        local_dist = cum_dist[ahead_idx] - cum_dist[t_start]
                        local_ele = smoothed_ele[ahead_idx] - smoothed_ele[t_start]
                        if local_dist > 0 and (local_ele / local_dist * 100) >= LOCAL_TRIM_GRAD:
                            seg_start_idx = t_start
                            break
            elif not ascending:
                end_chunk = low_mark_chunk
                for t in range(i, min(end_chunk, len(chunks))):
                    t_start = chunks[t]["si"]
                    ahead_idx = t_start
                    for ai in range(t_start + 1, min(chunks[end_chunk]["ei"] + 1, len(cum_dist))):
                        if cum_dist[ai] - cum_dist[t_start] >= LOCAL_TRIM_DIST:
                            ahead_idx = ai
                            break
                    if ahead_idx > t_start:
                        local_dist = cum_dist[ahead_idx] - cum_dist[t_start]
                        local_ele = smoothed_ele[ahead_idx] - smoothed_ele[t_start]
                        if local_dist > 0 and (local_ele / local_dist * 100) <= -LOCAL_TRIM_GRAD:
                            seg_start_idx = t_start
                            break
            
            seg_dist = cum_dist[seg_end_idx] - cum_dist[seg_start_idx]
            seg_ele = smoothed_ele[seg_end_idx] - smoothed_ele[seg_start_idx]
            
            # Check minimum criteria
            if seg_dist >= min_distance and abs(seg_ele) >= 50:
                avg_gradient = (seg_ele / seg_dist) * 100 if seg_dist > 0 else 0
                
                if (ascending and avg_gradient >= min_gradient) or \
                   (not ascending and avg_gradient <= -min_gradient):
                    
                    position_km = round(cum_dist[seg_start_idx] / 1000, 1)
                    distance_km = round(seg_dist / 1000, 1)
                    elevation_m = round(abs(seg_ele))
                    
                    segment = {
                        "position_km": position_km,
                        "distance_km": distance_km,
                        "elevation_m": elevation_m if ascending else -elevation_m,
                        "avg_gradient_pct": round(abs(avg_gradient), 1),
                        "start_coords": [round(trackpoints[seg_start_idx]["lat"], 5),
                                         round(trackpoints[seg_start_idx]["lon"], 5)],
                        "end_coords": [round(trackpoints[seg_end_idx]["lat"], 5),
                                       round(trackpoints[seg_end_idx]["lon"], 5)]
                    }
                    
                    if ascending:
                        # Max gradient over 200m subsections
                        max_grad = 0.0
                        for k in range(seg_start_idx, seg_end_idx):
                            for m in range(k + 1, seg_end_idx + 1):
                                sub_dist = cum_dist[m] - cum_dist[k]
                                if sub_dist >= 200:
                                    sub_grad = abs((smoothed_ele[m] - smoothed_ele[k]) / sub_dist * 100)
                                    max_grad = max(max_grad, sub_grad)
                                    break
                        segment["max_gradient_pct"] = round(max_grad, 1) if max_grad > 0 else segment["avg_gradient_pct"]
                        
                        # UCI-derived climb category
                        if elevation_m >= 1000:
                            segment["category"] = "HC"
                        elif elevation_m >= 650:
                            segment["category"] = "Cat 1"
                        elif elevation_m >= 400:
                            segment["category"] = "Cat 2"
                        elif elevation_m >= 200:
                            segment["category"] = "Cat 3"
                        elif elevation_m >= 100:
                            segment["category"] = "Cat 4"
                        else:
                            segment["category"] = None  # uncategorized — below Cat 4 threshold
                    else:
                        segment["avg_gradient_pct"] = -segment["avg_gradient_pct"]
                    
                    segments.append(segment)
            
            # Advance past this segment
            if ascending:
                i = high_mark_chunk + 1
            else:
                i = low_mark_chunk + 1
        
        return segments
    
    def _fetch_today_wellness(self) -> Dict:
        """
        Fetch today's wellness data which contains:
        - CTL, ATL, rampRate (but these include planned workouts!)
        - sportInfo with eFTP, W', P-max (accurate live estimates)
        - VO2max, sleep quality/hours, etc.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        try:
            data = self._intervals_get(f"wellness/{today}")
            return data
        except Exception as e:
            if self.debug:
                print(f"  Could not fetch today's wellness: {e}")
            return {}
    
    def _extract_power_model_from_wellness(self, wellness_data: Dict) -> Dict:
        """
        Extract eFTP, W', P-max from wellness.sportInfo.
        These are the accurate live estimates that match the Intervals.icu UI.
        """
        sport_info = wellness_data.get("sportInfo", [])
        
        # Find cycling sport info
        cycling_info = None
        for sport in sport_info:
            if sport.get("type") == "Ride":
                cycling_info = sport
                break
        
        if not cycling_info:
            return {
                "eftp": None,
                "w_prime": None,
                "w_prime_kj": None,
                "p_max": None,
                "source": "unavailable"
            }
        
        eftp = cycling_info.get("eftp")
        w_prime = cycling_info.get("wPrime")
        p_max = cycling_info.get("pMax")
        
        if self.debug and eftp:
            print(f"  eFTP: {round(eftp)}W, W': {round(w_prime) if w_prime else 'N/A'}J, P-max: {round(p_max) if p_max else 'N/A'}W")
        
        return {
            "eftp": round(eftp, 1) if eftp else None,
            "w_prime": round(w_prime) if w_prime else None,
            "w_prime_kj": round(w_prime / 1000, 1) if w_prime else None,
            "p_max": round(p_max) if p_max else None,
            "source": "wellness.sportInfo"
        }
    
    def _load_ftp_history(self) -> Dict[str, Dict[str, int]]:
        """
        Load FTP history from local JSON file.
        
        Returns dict with structure:
        {
            "indoor": {"2026-01-01": 270, "2026-02-01": 275},
            "outdoor": {"2026-01-01": 280, "2026-02-01": 287}
        }
        """
        ftp_history_path = self.data_dir / self.FTP_HISTORY_FILE
        
        if ftp_history_path.exists():
            try:
                with open(ftp_history_path, 'r') as f:
                    data = json.load(f)
                    # Handle legacy format (flat dict) -> convert to new format
                    if data and not ("indoor" in data or "outdoor" in data):
                        if self.debug:
                            print(f"  Converting legacy FTP history format...")
                        return {"indoor": {}, "outdoor": data}
                    return data
            except Exception as e:
                if self.debug:
                    print(f"  Could not load FTP history: {e}")
                return {"indoor": {}, "outdoor": {}}
        return {"indoor": {}, "outdoor": {}}
    
    def _save_ftp_history(self, history: Dict[str, Dict[str, int]], 
                          current_ftp_indoor: int, current_ftp_outdoor: int) -> Dict[str, Dict[str, int]]:
        """
        Save current FTPs to history file.
        Tracks indoor and outdoor FTP separately.
        Only adds entry if FTP changed from most recent entry.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        
        # Ensure structure exists
        if "indoor" not in history:
            history["indoor"] = {}
        if "outdoor" not in history:
            history["outdoor"] = {}
        
        # Update indoor FTP if changed
        if current_ftp_indoor:
            indoor_history = history["indoor"]
            if indoor_history:
                sorted_dates = sorted(indoor_history.keys(), reverse=True)
                most_recent = indoor_history[sorted_dates[0]]
                if current_ftp_indoor != most_recent:
                    history["indoor"][today] = current_ftp_indoor
                    if self.debug:
                        print(f"  Indoor FTP changed: {most_recent} → {current_ftp_indoor}")
            else:
                history["indoor"][today] = current_ftp_indoor
                if self.debug:
                    print(f"  Indoor FTP recorded: {current_ftp_indoor}")
        
        # Update outdoor FTP if changed
        if current_ftp_outdoor:
            outdoor_history = history["outdoor"]
            if outdoor_history:
                sorted_dates = sorted(outdoor_history.keys(), reverse=True)
                most_recent = outdoor_history[sorted_dates[0]]
                if current_ftp_outdoor != most_recent:
                    history["outdoor"][today] = current_ftp_outdoor
                    if self.debug:
                        print(f"  Outdoor FTP changed: {most_recent} → {current_ftp_outdoor}")
            else:
                history["outdoor"][today] = current_ftp_outdoor
                if self.debug:
                    print(f"  Outdoor FTP recorded: {current_ftp_outdoor}")
        
        # Save to file
        ftp_history_path = self.data_dir / self.FTP_HISTORY_FILE
        try:
            with open(ftp_history_path, 'w') as f:
                json.dump(history, f, indent=2, sort_keys=True)
            if self.debug:
                print(f"  FTP history saved to {ftp_history_path}")
        except Exception as e:
            if self.debug:
                print(f"  Could not save FTP history: {e}")
        
        return history
    
    def _calculate_benchmark_index(self, current_ftp: int, ftp_history: Dict[str, int], 
                                    ftp_type: str = "indoor") -> Tuple[Optional[float], Optional[int]]:
        """
        Calculate Benchmark Index = (FTP_current / FTP_8_weeks_ago) - 1
        
        Returns (benchmark_index, ftp_8_weeks_ago)
        """
        if not current_ftp or not ftp_history:
            return None, None
        
        # Find FTP from ~8 weeks ago (56 days, with ±7 day tolerance)
        target_date = datetime.now() - timedelta(days=56)
        earliest_acceptable = target_date - timedelta(days=7)
        latest_acceptable = target_date + timedelta(days=7)
        
        # Find the closest FTP entry to 8 weeks ago
        best_match_date = None
        best_match_diff = float('inf')
        
        for date_str, ftp in ftp_history.items():
            try:
                entry_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if earliest_acceptable <= entry_date <= latest_acceptable:
                    diff = abs((entry_date - target_date).days)
                    if diff < best_match_diff:
                        best_match_diff = diff
                        best_match_date = date_str
            except:
                continue
        
        if best_match_date:
            ftp_8_weeks_ago = ftp_history[best_match_date]
            benchmark_index = round((current_ftp / ftp_8_weeks_ago) - 1, 3)
            
            if self.debug:
                print(f"  Benchmark Index ({ftp_type}): {benchmark_index:+.1%} (FTP {ftp_8_weeks_ago} → {current_ftp})")
            
            return benchmark_index, ftp_8_weeks_ago
        
        # No data from 8 weeks ago
        if self.debug:
            sorted_dates = sorted(ftp_history.keys())
            if sorted_dates:
                oldest_date = datetime.strptime(sorted_dates[0], "%Y-%m-%d")
                days_of_history = (datetime.now() - oldest_date).days
                print(f"  Benchmark Index ({ftp_type}) unavailable: only {days_of_history} days of history (need ~56)")
        
        return None, None
    
    def collect_training_data(self, days_back: int = 7, anonymize: bool = False) -> Dict:
        """Collect all training data for LLM analysis"""
        # Extended range for ACWR calculation (need 28 days minimum)
        days_for_acwr = 28
        oldest_extended = (datetime.now() - timedelta(days=days_for_acwr - 1)).strftime("%Y-%m-%d")
        oldest_display = (datetime.now() - timedelta(days=days_back - 1)).strftime("%Y-%m-%d")
        newest = datetime.now().strftime("%Y-%m-%d")
        today = datetime.now().strftime("%Y-%m-%d")
        
        print("Fetching athlete data...")
        athlete = self._intervals_get("")
        
        # Extract per-sport-family thesholds from user settings
        sport_settings = self._build_sport_thresholds(athlete)
        
        # Fetch extended activity range for ACWR
        print(f"Fetching activities (extended {days_for_acwr} days for ACWR)...")
        activities_extended = self._intervals_get("activities", {"oldest": oldest_extended, "newest": newest})
        
        # Filter to display range for recent_activities
        activities_display = [a for a in activities_extended 
                              if a.get("start_date_local", "")[:10] >= oldest_display]
        
        print("Fetching wellness data...")
        wellness = self._intervals_get("wellness", {"oldest": oldest_display, "newest": newest})
        
        # Extended wellness for baselines (use full 28 days if available)
        wellness_extended = self._intervals_get("wellness", {"oldest": oldest_extended, "newest": newest})
        
        # Fetch today's wellness for live estimates (eFTP, W', P-max, VO2max, etc.)
        print("Fetching today's wellness (eFTP, W', P-max, VO2max)...")
        today_wellness = self._fetch_today_wellness()
        
        # Extract power model from wellness (accurate live estimates)
        power_model = self._extract_power_model_from_wellness(today_wellness)
        
        # Extract additional metrics from today's wellness
        vo2max = today_wellness.get("vo2max")
        
        # Get API values for fitness metrics (these include planned workouts!)
        api_ctl = today_wellness.get("ctl")
        api_atl = today_wellness.get("atl")
        api_ramp_rate = today_wellness.get("rampRate")
        
        # Fetch yesterday's wellness for decay fallback
        print("Fetching fitness metrics...")
        try:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            yesterday_wellness = self._intervals_get("wellness", {"oldest": yesterday, "newest": yesterday})
            yesterday_data = yesterday_wellness[0] if yesterday_wellness else {}
            
            # PMC decay constants
            ctl_decay = math.exp(-1/42)  # ~0.9765
            atl_decay = math.exp(-1/7)   # ~0.8668
            
            yesterday_ctl = yesterday_data.get("ctl")
            yesterday_atl = yesterday_data.get("atl")
            yesterday_ramp = yesterday_data.get("rampRate")
            
            # Decayed values = what fitness looks like with zero training today
            decayed_ctl = round(yesterday_ctl * ctl_decay, 2) if yesterday_ctl else None
            decayed_atl = round(yesterday_atl * atl_decay, 2) if yesterday_atl else None
            decayed_ramp = round(yesterday_ramp * ctl_decay, 2) if yesterday_ramp else None
        except:
            decayed_ctl = None
            decayed_atl = None
            decayed_ramp = None
            yesterday_ramp = None
        
        latest_wellness = wellness[-1] if wellness else {}
        
        # Fetch planned workouts (EXTENDED: include past 7 days for Consistency Index, 90 days ahead for race calendar)
        print("Fetching planned workouts (past + future for Consistency Index + race calendar)...")
        oldest_events = (datetime.now() - timedelta(days=days_back - 1)).strftime("%Y-%m-%d")
        newest_ahead = (datetime.now() + timedelta(days=90)).strftime("%Y-%m-%d")
        events = self._intervals_get("events", {"oldest": oldest_events, "newest": newest_ahead, "resolve": "true"})
        
        # Split events into past (for consistency), near future (for planned workouts display), and all future (for race calendar)
        past_events = [e for e in events if e.get("start_date_local", "")[:10] <= today]
        future_events = [e for e in events if e.get("start_date_local", "")[:10] >= today]
        near_future_events = [e for e in future_events if e.get("start_date_local", "")[:10] <= (datetime.now() + timedelta(days=42)).strftime("%Y-%m-%d")]
        
        # Smart fitness metrics: same logic for CTL, ATL, TSB, and ramp rate
        # API values include planned workouts → inflated if not yet completed
        # Decayed values = yesterday × decay → accurate baseline before any training today
        todays_planned = [e for e in events if e.get("start_date_local", "")[:10] == today]
        todays_activities = [a for a in activities_display if a.get("start_date_local", "")[:10] == today]
        
        if todays_planned and not todays_activities:
            # Planned workouts exist but nothing completed → decay (API values are inflated)
            ctl = decayed_ctl
            atl = decayed_atl
            smart_ramp_rate = decayed_ramp if decayed_ramp else api_ramp_rate
            fitness_source = "Decayed from yesterday (today's planned workouts not yet completed)"
        else:
            # No planned workouts OR workouts completed → API values are accurate
            ctl = round(api_ctl, 2) if api_ctl else decayed_ctl
            atl = round(api_atl, 2) if api_atl else decayed_atl
            smart_ramp_rate = round(api_ramp_rate, 2) if api_ramp_rate else decayed_ramp
            fitness_source = "From Intervals.icu API (reflects completed workouts)"
        
        tsb = round(ctl - atl, 2) if (ctl is not None and atl is not None) else None
        
        # Get both FTP values for cycling (user-set, not estimated)
        cycling = sport_settings.get("cycling", {})
        current_ftp_indoor = cycling.get("ftp_indoor")
        current_ftp_outdoor = cycling.get("ftp")
        
        # Load and update FTP history (tracks both indoor and outdoor)
        print("Updating FTP history...")
        ftp_history = self._load_ftp_history()
        ftp_history = self._save_ftp_history(ftp_history, current_ftp_indoor, current_ftp_outdoor)
        
        # Calculate Benchmark Index for both
        benchmark_index_indoor, ftp_8_weeks_ago_indoor = self._calculate_benchmark_index(
            current_ftp_indoor, ftp_history.get("indoor", {}), "indoor"
        )
        benchmark_index_outdoor, ftp_8_weeks_ago_outdoor = self._calculate_benchmark_index(
            current_ftp_outdoor, ftp_history.get("outdoor", {}), "outdoor"
        )
        
        # Generate routes.json from GPX/TCX attachments (v3.93)
        print("Scanning events for route attachments...")
        terrain_event_ids = self._generate_terrain(events)
        self._terrain_event_ids = terrain_event_ids
        if terrain_event_ids:
            print(f"    🗺️  Route data for {len(terrain_event_ids)} event(s)")
        
        # Build race calendar (v3.5.0) — moved before derived metrics for phase detection
        print("Building race calendar...")
        race_calendar = self._build_race_calendar(
            future_events=future_events,
            current_ctl=ctl,
            current_atl=atl,
            current_tsb=tsb,
            activities_7d=activities_display,
            today=today
        )
        
        # Format planned workouts — used by both phase detection and output
        formatted_planned_workouts = self._format_events(near_future_events, anonymize, today=today)
        
        # Fetch power curves for delta analysis (two 28-day windows)
        print("Fetching power curves...")
        power_curve_data = None
        pc_dates = None
        try:
            pc_end1 = today
            pc_start1 = (datetime.now() - timedelta(days=27)).strftime("%Y-%m-%d")
            pc_end2 = (datetime.now() - timedelta(days=28)).strftime("%Y-%m-%d")
            pc_start2 = (datetime.now() - timedelta(days=55)).strftime("%Y-%m-%d")
            pc_dates = (pc_start1, pc_end1, pc_start2, pc_end2)
            power_curve_data = self._intervals_get("power-curves", {
                "type": "Ride",
                "curves": f"r.{pc_start1}.{pc_end1},r.{pc_start2}.{pc_end2}"
            })
        except Exception as e:
            if self.debug:
                print(f"  ⚠️  Power curve fetch failed: {e}")
        
        # Fetch HR curves for delta analysis (same windows, no sport filter)
        print("Fetching HR curves...")
        hr_curve_data = None
        try:
            hr_curve_data = self._intervals_get("hr-curves", {
                "curves": f"r.{pc_dates[0]}.{pc_dates[1]},r.{pc_dates[2]}.{pc_dates[3]}"
            }) if pc_dates else None
        except Exception as e:
            if self.debug:
                print(f"  ⚠️  HR curve fetch failed: {e}")
        
        # Fetch sustainability curves (v3.91) — sport-filtered power + HR, single 42d window
        print("Fetching sustainability curves...")
        sustainability_curves = {}
        sus_end = today
        sus_start = (datetime.now() - timedelta(days=self.SUSTAINABILITY_WINDOW_DAYS - 1)).strftime("%Y-%m-%d")
        sus_window = (sus_start, sus_end)
        
        # Determine which sport families have recent activity data
        active_sport_families = set()
        for a in activities_extended:
            sf = self.SPORT_FAMILIES.get(a.get("type", ""), None)
            if sf and sf in self.SUSTAINABILITY_ANCHORS:
                active_sport_families.add(sf)
        
        for sport_family in active_sport_families:
            sport_curves = {"power": {}, "hr": {}}
            
            # Power curves — one fetch per activity type (cycling: Ride + VirtualRide)
            power_types = self.SUSTAINABILITY_POWER_TYPES.get(sport_family, [])
            for ptype in power_types:
                try:
                    data = self._intervals_get("power-curves", {
                        "type": ptype,
                        "curves": f"r.{sus_start}.{sus_end}"
                    })
                    sport_curves["power"][ptype] = data
                except Exception as e:
                    if self.debug:
                        print(f"  ⚠️  Sustainability power-curves ({ptype}) failed: {e}")
            
            # HR curves — one fetch per activity type
            hr_types = self.SUSTAINABILITY_HR_TYPES.get(sport_family, [])
            for htype in hr_types:
                try:
                    data = self._intervals_get("hr-curves", {
                        "type": htype,
                        "curves": f"r.{sus_start}.{sus_end}"
                    })
                    sport_curves["hr"][htype] = data
                except Exception as e:
                    if self.debug:
                        print(f"  ⚠️  Sustainability hr-curves ({htype}) failed: {e}")
            
            sustainability_curves[sport_family] = sport_curves
        
        if sustainability_curves:
            print(f"  📊 Sustainability curves fetched for: {', '.join(sorted(sustainability_curves.keys()))}")
        else:
            print("  📊 No sport families with sustainability data")
        
        # Generate interval-level data (v3.82, expanded v3.99)
        # Uses the already-fetched activity list — no extra listing API calls.
        # Pre-filters by sport family whitelist; no longer requires interval_summary.
        # Incremental: only fetches intervals for new qualifying activities.
        # MUST run before _calculate_derived_metrics so self._intervals_data is
        # populated when _calculate_dfa_a1_profile reads it (v3.99 fix).
        print("Checking for interval data...")
        interval_activity_ids = self._generate_intervals(activities_display, anonymize)
        if interval_activity_ids:
            print(f"  📊 {len(interval_activity_ids)} activit{'y' if len(interval_activity_ids) == 1 else 'ies'} with interval data")
        
        # Calculate derived metrics for Section 11 compliance
        print("Calculating derived metrics...")
        derived_metrics = self._calculate_derived_metrics(
            activities_7d=activities_display,
            activities_28d=activities_extended,
            wellness_7d=wellness,
            wellness_extended=wellness_extended,
            current_ctl=ctl,
            current_atl=atl,
            current_tsb=tsb,
            past_events=past_events,
            activities_for_consistency=activities_display,
            power_model=power_model,
            benchmark_indoor=(benchmark_index_indoor, ftp_8_weeks_ago_indoor, current_ftp_indoor),
            benchmark_outdoor=(benchmark_index_outdoor, ftp_8_weeks_ago_outdoor, current_ftp_outdoor),
            vo2max=vo2max,
            formatted_planned_workouts=formatted_planned_workouts,
            race_calendar=race_calendar,
            power_curve_data=power_curve_data,
            power_curve_dates=pc_dates,
            hr_curve_data=hr_curve_data,
            sustainability_curves=sustainability_curves,
            sustainability_window=sus_window,
            sport_settings=sport_settings,
            icu_weight=athlete.get("icu_weight")
        )
        
        # Generate alerts array (v3.3.0)
        print("Evaluating alert thresholds...")
        alerts = self._generate_alerts(
            derived_metrics=derived_metrics,
            wellness_7d=wellness,
            tss_7d_total=derived_metrics.get("tss_7d_total", 0),
            tss_28d_total=derived_metrics.get("tss_28d_total", 0)
        )
        
        if alerts:
            alarm_count = sum(1 for a in alerts if a["severity"] == "alarm")
            warning_count = sum(1 for a in alerts if a["severity"] == "warning")
            print(f"  ⚠️  {len(alerts)} alerts: {alarm_count} alarm, {warning_count} warning")
        else:
            print("  ✅ No alerts — green light")
        
        # Add race-specific alerts
        race_alerts = self._generate_race_alerts(race_calendar)
        if race_alerts:
            alerts.extend(race_alerts)
            print(f"  🏁 {len(race_alerts)} race alert(s) added")
        
        if race_calendar.get("race_week", {}).get("active"):
            rw = race_calendar["race_week"]
            print(f"  🏁 Race week ACTIVE: {rw['current_day']} of '{rw['event_name']}'")
        elif race_calendar.get("taper_alert", {}).get("active"):
            nr = race_calendar.get("next_race", {})
            print(f"  🏁 Taper alert: '{nr.get('name', '?')}' in {nr.get('days_until', '?')} days")
        elif race_calendar.get("next_race"):
            nr = race_calendar["next_race"]
            print(f"  🏁 Next race: '{nr.get('name', '?')}' in {nr.get('days_until', '?')} days")
        else:
            print("  🏁 No races in 90-day window")
        
        # Compute readiness decision (v3.72)
        print("Computing readiness decision...")
        readiness_decision = self._compute_readiness_decision(
            derived_metrics=derived_metrics,
            alerts=alerts,
            latest_wellness=latest_wellness,
            activities=activities_extended,
            race_calendar=race_calendar,
            current_tsb=tsb
        )
        rd_rec = readiness_decision["recommendation"].upper()
        rd_pri = readiness_decision["priority"]
        print(f"  {'🟢' if rd_rec == 'GO' else '🟡' if rd_rec == 'MODIFY' else '🔴'} Readiness: {rd_rec} (P{rd_pri})")
        
        # History confidence (v3.3.0)
        history_info = self._get_history_confidence()
        
        data = {
            "READ_THIS_FIRST": {
                "instruction_for_ai": "DO NOT calculate totals from individual activities. Use the pre-calculated values in 'summary', 'weekly_summary', and 'derived_metrics' sections below. These are already computed accurately from the API data.",
                "display_formatting": "For durations and sleep, always display the '_formatted' fields (e.g., sleep_formatted, duration_formatted, total_training_formatted) instead of converting decimal '_hours' values. The formatted fields are pre-calculated from raw seconds and avoid rounding errors.",
                "data_period": f"Last {days_back} days (including today)",
                "extended_data_note": f"ACWR and baselines calculated from {days_for_acwr} days of data",
                "capability_metrics_note": "The 'capability' block in derived_metrics contains durability trend (aggregate decoupling 7d/28d), efficiency factor trend (aggregate EF 7d/28d), HRRc trend (heart rate recovery 7d/28d), TID comparison (7d vs 28d distribution drift), power curve delta (MMP shift at anchor durations across 28d windows — energy system adaptation direction), HR curve delta (max sustained HR shift at anchor durations — cardiac adaptation, cross-sport), sustainability profile (per-sport power/HR sustainability table for race estimation — 42d window, sport-filtered), and DFA a1 profile (per-session non-linear HRV index from AlphaHRV Connect IQ field — latest_session + trailing_by_sport with crossing-band LT1/LT2 estimates). These measure HOW the athlete expresses fitness, not just load. Use these for coaching context alongside traditional load metrics. Durability and EF trend direction matters more than absolute values. HRRc is display only — higher = better parasympathetic recovery. Power curve delta rotation_index reveals whether gains are sprint-biased (positive) or endurance-biased (negative). HR curve delta is ambiguous — rising max sustained HR may indicate fitness or fatigue; cross-reference with resting HRV/HR and RPE. Sustainability profile provides race estimation lookup: actual MMP, Coggan predicted (cycling only), CP/W' model (cycling only), model_divergence_pct (actual vs CP — divergence IS the coaching signal). CP/W' is primary for durations ≤20min; Coggan duration factors are the established reference for ≥60min. Source flag (observed_outdoor/observed_indoor) matters for cycling race estimation — indoor MMP is typically 3-5% lower. DFA a1 profile: thresholds (1.0 ≈ LT1, 0.5 ≈ LT2) cycling-validated only — non-cycling sports get rollups but validated=False. Crossing-band estimates (avg HR/watts in narrow bands around each threshold) are provisional at confidence='low' (suppressed for calibration delta surfacing) and usable at 'moderate' or 'high'. DFA a1 is a Tier-2 interpretive signal — does NOT enter readiness P0–P3 ladder, does NOT auto-update dossier zones; surfaces calibration deltas only. Quality gate: refuse to interpret when latest_session.sufficient=false or trailing confidence=null. See SECTION_11.md DFA a1 Protocol for full interpretation rules.",
                "readiness_decision_note": "The 'readiness_decision' block contains a pre-computed go/modify/skip recommendation with priority level (P0=safety, P1=overload, P2=fatigue, P3=green), individual signal statuses, phase-adjusted thresholds, and structured modification guidance. Use this as the baseline for pre-workout recommendations. Override with explanation in the coach note if the AI's contextual judgment disagrees.",
                "zone_preference": self.zone_preference if self.zone_preference else "default (power preferred, HR fallback)",
                "wellness_field_scales": {
                    "note": "All categorical wellness fields use a 1-4 positional scale where 1 = best state, 4 = worst state. Labels differ per field but direction is consistent. Fields are null when not reported.",
                    "sleep_quality": {"1": "GREAT", "2": "OK", "3": "POOR", "4": "WORST"},
                    "fatigue": {"1": "None", "2": "Some", "3": "High", "4": "Extreme", "ui_note": "Labeled 'Pre training' in Intervals.icu"},
                    "soreness": {"1": "None", "2": "Some", "3": "High", "4": "Extreme", "ui_note": "Labeled 'Pre training' in Intervals.icu"},
                    "stress": {"1": "LOW", "2": "AVG", "3": "HIGH", "4": "EXTREME"},
                    "mood": {"1": "GREAT", "2": "GOOD", "3": "OK", "4": "GRUMPY"},
                    "motivation": {"1": "EXTREME", "2": "HIGH", "3": "AVG", "4": "LOW"},
                    "injury": {"1": "NONE", "2": "NIGGLE", "3": "POOR", "4": "INJURED"},
                    "hydration": {"1": "GOOD", "2": "OK", "3": "POOR", "4": "BAD"},
                    "menstrual": "menstrual_phase and menstrual_phase_predicted are not on the 1-4 scale. Values: PERIOD, FOLLICULAR, OVULATION, LUTEAL, etc."
                },
                "quick_stats": {
                    "total_training_hours": round(sum(act.get("moving_time", 0) for act in activities_display) / 3600, 2),
                    "total_training_formatted": self._format_duration(int(sum(act.get("moving_time", 0) for act in activities_display)) // 60 * 60),
                    "total_activities": len(activities_display),
                    "total_tss": round(sum(act.get("icu_training_load", 0) for act in activities_display if act.get("icu_training_load")), 0)
                }
            },
            "metadata": {
                "athlete_id": "REDACTED" if anonymize else self.athlete_id,
                "last_updated": datetime.now().isoformat(),
                "data_range_days": days_back,
                "extended_range_days": days_for_acwr,
                "version": self.VERSION
            },
            "alerts": alerts,
            "readiness_decision": readiness_decision,
            "history": history_info,
            "summary": self._compute_activity_summary(activities_display, days_back),
            "current_status": {
                "fitness": {
                    "ctl": ctl,
                    "atl": atl,
                    "tsb": tsb,
                    "ramp_rate": smart_ramp_rate,
                    "fitness_source": fitness_source
                },
                "thresholds": {
                    "eftp": power_model.get("eftp"),
                    "w_prime": power_model.get("w_prime"),
                    "w_prime_kj": power_model.get("w_prime_kj"),
                    "p_max": power_model.get("p_max"),
                    "vo2max": vo2max,                    
                    "sports": sport_settings
                },
                "current_metrics": {
                    "weight_kg": latest_wellness.get("weight") or athlete.get("icu_weight"),
                    "resting_hr": latest_wellness.get("restingHR") or athlete.get("icu_resting_hr"),
                    "hrv": latest_wellness.get("hrv"),
                    "sleep_quality": latest_wellness.get("sleepQuality"),
                    "sleep_hours": round(latest_wellness.get("sleepSecs", 0) / 3600, 2) if latest_wellness.get("sleepSecs") else None,
                    "sleep_formatted": self._format_duration(int(latest_wellness.get("sleepSecs", 0)) // 60 * 60) if latest_wellness.get("sleepSecs") else None,
                    "sleep_score": latest_wellness.get("sleepScore"),
                    # Subjective state (categorical 1-4, see wellness_field_scales in READ_THIS_FIRST)
                    "fatigue": latest_wellness.get("fatigue"),
                    "soreness": latest_wellness.get("soreness"),
                    "stress": latest_wellness.get("stress"),
                    "mood": latest_wellness.get("mood"),
                    "motivation": latest_wellness.get("motivation"),
                    "injury": latest_wellness.get("injury"),
                    "hydration": latest_wellness.get("hydration"),
                    # Vitals
                    "spO2": latest_wellness.get("spO2"),
                    "blood_glucose": latest_wellness.get("bloodGlucose"),
                    "systolic": latest_wellness.get("systolic"),
                    "diastolic": latest_wellness.get("diastolic"),
                    "baevsky_si": latest_wellness.get("baevskySI"),
                    "lactate": latest_wellness.get("lactate"),
                    "respiration": latest_wellness.get("respiration"),
                    # Body composition
                    "body_fat_pct": latest_wellness.get("bodyFat"),
                    "abdomen_cm": latest_wellness.get("abdomen"),
                    # Lifestyle / nutrition
                    "steps": latest_wellness.get("steps"),
                    "hydration_volume_l": latest_wellness.get("hydrationVolume"),
                    "kcal_consumed": latest_wellness.get("kcalConsumed"),
                    "carbohydrates_g": latest_wellness.get("carbohydrates"),
                    "protein_g": latest_wellness.get("protein"),
                    "fat_g": latest_wellness.get("fatTotal"),
                    # Cycle
                    "menstrual_phase": latest_wellness.get("menstrualPhase"),
                    "menstrual_phase_predicted": latest_wellness.get("menstrualPhasePredicted"),
                    # Platform
                    "readiness": latest_wellness.get("readiness")
                }
            },
            "derived_metrics": derived_metrics,
            "recent_activities": self._format_activities(activities_extended, anonymize, interval_activity_ids),
            "wellness_data": self._format_wellness(wellness),
            "planned_workouts": formatted_planned_workouts,
            "workout_summary_stats": getattr(self, '_summary_stats', {}),
            "weekly_summary": self._compute_weekly_summary(activities_display, wellness),
            "race_calendar": race_calendar
        }
        
        return data