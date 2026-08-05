# Athlete Training Dossier & Performance Roadmap

**Dossier Version:** v1.1.1  
**Protocol Compatibility:** Section 11 v11.6+  
**Date:** 2026-03-13  
**Primary Source Systems:** Intervals.icu

This document serves as a reference template for endurance athletes using the deterministic AI-coaching framework defined in Section 11.

---

## Quick Start

1. Fill in your athlete profile (Section 1)
2. Document your equipment (Section 2)
3. Define your training schedule and goals (Section 3)
4. Enter your current performance metrics (Section 4)
5. Set up your nutrition/fueling protocol (Section 5)
6. Link this dossier to your JSON data mirror (see Section 11 for protocol)

---

## 1. Athlete Overview

### Athlete Profile

| Field | Value |
|-------|-------|
| Name | Robin |
| Age | 47 |
| Height | 178cm |
| Current Weight | 71.5kg |
| Target Weight | 70kg |
| Location | Hitchin, UK |

**Weigh-in Protocol:** Once weekly, Friday morning, after bathroom, before food/drink

### Sport Focus

| Type | Description |
|------|-------------|
| Primary | Cycling performance (Endurance) |
| Secondary | Pilates, Walking, Functional Strength |

### Goals

| Goal | Target Date |
|------|-------------|
|  We Ride Flanders| 4th APril 2027 |
| GRALLOCH| 15th May 2027 |

**Current Phase:** Late Base / Build  
**Training Style:** Pyramidal (High-volume)

---

## 2. Equipment & Environment

### Indoor Training Setup

| Component | Details |
|-----------|---------|
| Trainer/Bike | Taxc Neo |
| Platform | MyWhoosh |
| Cooling | [Add fan setup] |
| Sensors | HRM, internal power meter |

### Outdoor Setup

| Component | Details |
|-----------|---------|
| Bike | Trek Madone SL6 & Trek Checkpoint Sl5 |
| Power Meter | SRAM|
| Head Unit | Garmin Edge 104 |

---

## 3. Training Schedule & Framework

### Weekly Volume Target

**Baseline:** 14.8 hours/week  
**Peak phases:** Up to 16 hours (requires ACWR ≤ 1.3, HRV within 10%)

### Recovery Protocol

**Recovery Triggers (Auto-Deload):**
- HRV ↓ > 20% → Prioritize sleep, reduce intensity.
- RHR ↑ ≥ 5 bpm → Cap heart rate at Z2.
- Feel ≥ 4 → Scrub Sweet Spot/Threshold intervals.
- Two+ triggers → Priority 2 Modify or Priority 1 Skip.

**Feel Scale:**
| Score | Meaning |
|-------|---------|
| 1 | Excellent (fully recovered) |
| 2 | Good (normal fatigue) |
| 3 | Moderate (manageable tiredness) |
| 4 | Fatigued (reduced readiness, deload trigger) |
| 5 | Exhausted (complete rest required) |

---

## 4. Performance Metrics

### Current Power Zones (Based on 275W FTP)

| Zone | % of FTP | Power (W) | Notes |
|------|----------|-----------|-------|
| Z1 | 0–55% | 0–151 W | Active Recovery |
| Z2 | 56–75% | 154–206 W | Endurance (Base) |
| Z3 | 76–90% | 209–247 W | Tempo |
| Z4 | 91–105% | 250–288 W | Threshold |
| Z5 | 106–120% | 291–330 W | VO₂max |
| Z6 | 121–150% | 332–412 W | Anaerobic |
| Z7 | 151%+ | 415+ W | Neuromuscular |
| SS | 84–97% | 231–266 W | Sweetspot |

**Current FTP:** 275 W (Indoor: 275 W)  
**Max HR:** 192 bpm  
**Threshold HR (LTHR):** 174 bpm  
**Resting HR Baseline:** 61 bpm

### Current Fitness Markers

| Metric | Value | Notes |
|--------|-------|-------|
| eFTP | 269.8 W | Modeled from recent efforts |
| W' (Anaerobic Capacity) | 23.0 kJ | |
| P-max | 996 W | |
| 7-Day TSS Target | ~480 TSS | |

---

## 5. Nutrition / Fueling

### Fueling by Workout Type

| Workout Type | Duration | CHO Target |
|--------------|----------|------------|
| Recovery / Z1–Z2 | < 1.5 h | 0–30 g/h |
| Endurance | 1.5–3 h | 40–60 g/h |
| Long Endurance | 3–6 h | 60–90 g/h |
| Threshold / SS | 1–2 h | 60–90 g/h |
| VO₂ / High Intensity | 1–1.5 h | 60–90 g/h |

---

## Data Mirror Configuration

**Path:** `latest.json` (data directory root, alongside this dossier)
**History:** `history.json` (data directory root)

This endpoint provides synchronized Intervals.icu metrics for deterministic AI parsing.
