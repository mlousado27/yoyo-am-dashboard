# Yo-Yo AM Line — Challenge 1: Context & Results

> Working notes for the Simulation Workshop dashboard. Everything in US English.
> Data source: `Yo-Yo Model_case1 (2)_AM_Model_SLS_MJF_Additive_Copy_ResultsDetail.csv`
> (Simio ResultsDetail export, semicolon-delimited, European decimals `,`).

## 1. The challenge (from `Yoyo_challenge1.pdf`)

Design and optimize a low-volume, high-customization yo-yo manufacturing line built
around **SLS / MJF additive manufacturing**.

Flow: **Source (orders → batches)** → **AM printers (build)** → **Post-processing (Separator:
batch explodes into individual bodies)** → **Assembly** → **Quality / Drop Test** → Good / Scrap sinks.

- Run horizon: **240 working days × 8 h = 1,920 h/year**.
- Orders arrive as **YoYoBatch** entities (one batch = `NNEST` yo-yos); the separator
  explodes each batch into `NNEST` **YoYoBody** entities.
- **Objective:** minimize **unit production cost** subject to a **hard promise: every order
  shipped in under 12 h** (worst-case, not average).

## 2. The five optimization controls (challenge slide → Simio → data)

| Slide parameter | Range | Slide value | Simio control | Reconstructed from ResultsDetail |
|---|---|---|---|---|
| Assembly capacity | 1–5 | 2 | `ASSEMBLYCAP` | `Server Assembly` UnitsScheduled |
| Quality capacity | 1–5 | 2 | `QUALCAP` | `Server DropTest` UnitsScheduled |
| Post-processing capacity | 1–5 | 1 | `POSTPROC_CAP` | `Separator PostProcessing` UnitsScheduled |
| Additional main AM units | 1–5 | 0 | `NMAIN_AM_C` | `Server AM` UnitsScheduled = base(4) + additional |
| Batch size | 1–10 | 4 | `NNEST` | NumberCreated(YoYoBody) / NumberCreated(YoYoBatch) |

Slide reported optimum → **Unit cost 6.31 $**, **Lead time 10.70 h**.

## 3. Experiment structure

- **300 scenarios × 10 replications = 3,000 runs**, 2,139,000 rows.
- All 300 control tuples are **unique** → this is an optimization search (OptQuest-style),
  **not** a balanced factorial. Sensitivity must be treated observationally (regression /
  conditional views), not as orthogonal main effects.
- Control ranges observed: assembly 1–5, qual 1–5, postproc 1–5, batch 1–10,
  total AM printers 4–9 (base 4 + 0–5 additional).
- We report the **mean across the 10 replications** for every scenario (standard practice here).

## 4. Response definitions — REVERSE-ENGINEERED AND VERIFIED

Ground truth from the Simio Design grid (exact, user-provided):

| Scenario | ASSEMBLY | QUAL | POSTPROC | +AM | NNEST | TotalCost | LeadTime | batchTime |
|---|---|---|---|---|---|---|---|---|
| 004 | 2 | 2 | 1 | 0 | 4 | 6.31171 | 10.6977 | 10.3383 |
| 037 | 2 | 1 | 1 | 0 | 4 | 6.31942 | 11.9729 | 11.5556 |
| 014 | 2 | 2 | 1 | 0 | 2 | 6.32588 | 8.01771 | 7.68922 |

**Lead time & batch time — cracked exactly (matches all 3 anchors to 4–5 decimals):**

- `batchTime` = mean over reps of **`YoYoBatch.TimeInSystem.Maximum`**
  (worst-case order time from arrival through printing + post-processing / separation).
- `LeadTime`  = mean over reps of **`YoYoBatch.TimeInSystem.Maximum` + `YoYoBody.TimeInSystem.Maximum`**
  (worst-case full order flow time, incl. assembly + QC).
- **Maximum (not Average) is intentional** — the "under 12 h" promise is a hard guarantee,
  so the worst case is what must clear the gate. Confirmed by user.

**Unit cost (`TotalCost` response) — NOT exactly reconstructable from ResultsDetail:**

- `AM_Model.TotalCost` (system total, ≈ 62,900 $) ÷ good units → 6.74; ÷ all bodies → 6.39.
- Simio's response = 6.31171; implied denominator ≈ 9,969 units, which matches **no** count in
  the export (bodies ≈ 9,840). Gap is a systematic ~1.3%.
- Conclusion: the `TotalCost` response is a **custom experiment expression** (likely tied to the
  Excel cost model / planned demand `NREF`), not a raw ratio of exported metrics.
- **Action:** use the authoritative response values exported from Simio for the three headline
  responses; use ResultsDetail only for the supporting per-station analyses (utilization,
  cost breakdown, queueing).

## 5. Key relationships (scenario-level, Pearson r) — preview of insights

| Control | vs Unit cost | vs Lead time (max) | vs batchTime |
|---|---|---|---|
| Total AM printers | **+0.994** | −0.63 | −0.40 |
| Batch size (NNEST) | −0.17 | **+0.78** | **+0.96** |
| Assembly cap | −0.16 | +0.22 | +0.18 |
| Quality cap | +0.10 | −0.09 | −0.04 |
| Post-proc cap | +0.21 | −0.17 | −0.12 |

Headline reads:
- **Cost is almost entirely a printer story** (r ≈ 0.99 with printer count). Extra printers add
  capital with no cost payback; labor stations (assembly/QC/post-proc) barely move cost.
- **Lead time is a batch-size story** (r ≈ 0.96 with batchTime). Bigger batches → longer
  worst-case order time. This is the core cost ↔ speed tension.
- Assembly / QC / post-processing capacity are **not** the bottleneck — the AM printer bank is
  (per the PDF: "the core of the operation and its constraint").
