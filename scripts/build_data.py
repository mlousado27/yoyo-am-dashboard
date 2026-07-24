"""Rebuild the compact dashboard datasets from the raw Simio exports.

The app ships the derived files (../data/*.parquet), so you only need this if the
Simio exports change. Put the two exports in a `raw/` folder at the repo root
(or set RAW_DIR), then run:  python scripts/build_data.py

Expected raw files (semicolon-delimited, European decimals):
  - *ResponseDetail.csv   (authoritative responses: TotalCost, LeadTime, batchTime, ...)
  - *ResultsDetail.csv    (full pivot detail; large, ~160 MB)

Provenance:
  unit cost  = Simio TotalCost response (annualized system cost per saleable unit),
               mean over the 10 replications.
  lead time  = worst-case order flow time = max(YoYoBatch time-in-system) +
               max(YoYoBody time-in-system), mean over the 10 replications.
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = Path(os.environ.get("RAW_DIR", ROOT / "raw"))
OUT = ROOT / "data"
GATE = 12.0


def find(pattern):
    hits = sorted(RAW.glob(pattern))
    if not hits:
        raise SystemExit(f"Could not find {pattern} in {RAW}. "
                         f"Put the Simio exports there or set RAW_DIR.")
    return hits[0]


def eu(s):
    return pd.to_numeric(s.str.replace(",", ".", regex=False), errors="coerce")


def main():
    RESP = find("*ResponseDetail.csv")
    DET = find("*ResultsDetail.csv")

    # ---- responses (authoritative) ----
    r = pd.read_csv(RESP, sep=";", dtype=str)
    r["Scenario"] = r["Scenario"].str.zfill(3)
    for c in ["TotalCost", "LeadTime", "batchTime", "BodyTime", "SUTime", "NAM"]:
        r[c] = eu(r[c])
    r["lead_h"] = r["LeadTime"] * 60
    r["batch_h"] = r["batchTime"] * 60
    r["body_h"] = r["BodyTime"] * 60
    rep = r.rename(columns={"Replication": "rep", "TotalCost": "unit_cost",
                            "SUTime": "am_util", "NAM": "n_printers"})
    rep = rep[["Scenario", "rep", "unit_cost", "lead_h", "batch_h", "body_h", "am_util", "n_printers"]]
    sc = rep.groupby("Scenario").agg(
        unit_cost=("unit_cost", "mean"), unit_cost_sd=("unit_cost", "std"),
        lead_h=("lead_h", "mean"), lead_h_sd=("lead_h", "std"),
        lead_h_min=("lead_h", "min"), lead_h_max=("lead_h", "max"),
        batch_h=("batch_h", "mean"), body_h=("body_h", "mean"),
        am_util=("am_util", "mean"), n_printers=("n_printers", "mean"),
        n_reps=("rep", "count"), reps_breach=("lead_h", lambda s: int((s >= GATE).sum()))).reset_index()
    sc["n_printers"] = sc["n_printers"].round().astype(int)

    # ---- controls + support (from ResultsDetail) ----
    cols = ["Scenario", "Replication", "Object Name", "Data Source", "Category",
            "Data Item", "Statistic Type", "Value"]
    OBJ = {"AM", "Assembly", "DropTest", "PostProcessing", "AM_Model",
           "YoYoBatch", "YoYoBody", "GoodSink", "NoGoodSink"}
    ITM = {"UnitsScheduled", "ScheduledUtilization", "NumberCreated", "NumberExited",
           "TotalCost", "CapitalCost", "IdleCost", "UsageCostCharged",
           "TimeInSystem", "TimeWaiting", "NumberWaiting"}
    STA = {"Average", "Total", "Percent", "Maximum"}
    parts = []
    for ch in pd.read_csv(DET, sep=";", dtype=str, chunksize=500_000, usecols=cols, engine="c"):
        m = ch["Object Name"].isin(OBJ) & ch["Data Item"].isin(ITM) & ch["Statistic Type"].isin(STA)
        parts.append(ch[m])
    d = pd.concat(parts, ignore_index=True)
    d["Scenario"] = d["Scenario"].str.zfill(3)
    d["val"] = eu(d["Value"])
    d["key"] = d["Object Name"] + "|" + d["Data Source"] + "|" + d["Data Item"] + "|" + d["Statistic Type"]
    w = d.pivot_table(index=["Scenario", "Replication"], columns="key", values="val", aggfunc="first").reset_index()

    def col(name):
        return w[name] if name in w.columns else pd.Series(np.nan, index=w.index)

    w["assembly_cap"] = col("Assembly|[Resource]|UnitsScheduled|Average").round()
    w["qual_cap"] = col("DropTest|[Resource]|UnitsScheduled|Average").round()
    w["postproc_cap"] = col("PostProcessing|[Resource]|UnitsScheduled|Average").round()
    w["batch_size"] = (col("YoYoBody|[Population]|NumberCreated|Total")
                       / col("YoYoBatch|[Population]|NumberCreated|Total")).round()
    w["good_units"] = col("GoodSink|InputBuffer|NumberExited|Total")
    w["scrap_units"] = col("NoGoodSink|InputBuffer|NumberExited|Total")
    w["maxbatch_h"] = col("YoYoBatch|[Population]|TimeInSystem|Maximum")
    w["maxbody_h"] = col("YoYoBody|[Population]|TimeInSystem|Maximum")
    w["maxlead_h"] = w["maxbatch_h"] + w["maxbody_h"]
    for st in ["AM", "Assembly", "DropTest", "PostProcessing"]:
        w[f"{st}_totcost"] = col(f"{st}|[Object]|TotalCost|Total")
        w[f"{st}_capital"] = col(f"{st}|[Object]|CapitalCost|Total")
        w[f"{st}_idle"] = col(f"{st}|[Resource]|IdleCost|Total")
        w[f"{st}_usage"] = col(f"{st}|[Resource]|UsageCostCharged|Total")
        w[f"{st}_util"] = col(f"{st}|[Resource]|ScheduledUtilization|Percent")
        w[f"{st}_qwait_h"] = col(f"{st}|InputBuffer|EntryQueue|TimeWaiting|Average")
    w["sys_totcost"] = col("AM_Model|[Object]|TotalCost|Total")
    aggmap = {c: "mean" for c in w.columns if c not in ("Scenario", "Replication")}
    scd = w.groupby("Scenario").agg(aggmap).reset_index()
    for c in ["assembly_cap", "qual_cap", "postproc_cap", "batch_size"]:
        scd[c] = scd[c].round().astype(int)

    # ---- merge, cross-check, save ----
    S = sc.merge(scd, on="Scenario", how="left")
    resid = (S["lead_h"] - S["maxlead_h"]).abs().max()
    print(f"cross-check lead_h vs max-reconstruction: max residual {resid:.5f} h")
    S["yield_pct"] = 100 * S["good_units"] / (S["good_units"] + S["scrap_units"])
    S["feasible"] = S["lead_h"] < GATE
    OUT.mkdir(exist_ok=True)
    S.to_parquet(OUT / "scenarios.parquet")
    repm = rep.merge(S[["Scenario", "assembly_cap", "qual_cap", "postproc_cap", "batch_size"]],
                     on="Scenario", how="left")
    repm.to_parquet(OUT / "replications.parquet")
    print(f"wrote {OUT/'scenarios.parquet'} {S.shape} and {OUT/'replications.parquet'} {repm.shape}")


if __name__ == "__main__":
    main()
