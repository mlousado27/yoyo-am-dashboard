"""Pure figure builders + stats helpers for the Yo-Yo AM dashboard.

No Streamlit here: every function returns a Plotly figure or a number, so the
same code renders in the app and in the headless QA harness (zero drift).
"""
import itertools
from math import factorial

import numpy as np
import pandas as pd
import plotly.graph_objects as go

import theme as T

GATE = 12.0
CTRLS = ["n_printers", "batch_size", "assembly_cap", "qual_cap", "postproc_cap"]
CTRL_LABEL = {"n_printers": "Printers", "batch_size": "Batch size",
              "assembly_cap": "Assembly cap.", "qual_cap": "Quality cap.",
              "postproc_cap": "Post-proc cap."}


# ---------------------------------------------------------------- stats
def _r2(df, xs, y):
    if not xs:
        return 0.0
    X = df[list(xs)].to_numpy(float)
    Y = df[y].to_numpy(float)
    X = (X - X.mean(0)) / X.std(0)
    Y = (Y - Y.mean()) / Y.std()
    A = np.column_stack([np.ones(len(X)), X])
    coef, *_ = np.linalg.lstsq(A, Y, rcond=None)
    resid = Y - A @ coef
    return 1 - (resid ** 2).sum() / ((Y - Y.mean()) ** 2).sum()


def lmg(df, preds, y):
    """LMG / Shapley relative importance: each control's share of explained
    variance, averaged over every ordering. The shares sum to the model R^2,
    so normalizing gives a clean 100% split of what drives the outcome."""
    n = len(preds)
    contrib = {p: 0.0 for p in preds}
    for p in preds:
        others = [x for x in preds if x != p]
        for k in range(len(others) + 1):
            for subset in itertools.combinations(others, k):
                w = factorial(len(subset)) * factorial(n - len(subset) - 1) / factorial(n)
                contrib[p] += w * (_r2(df, list(subset) + [p], y) - _r2(df, list(subset), y))
    total = sum(contrib.values())
    return {p: contrib[p] / total * 100 for p in preds}, total


def cost_slope(S):
    b = np.polyfit(S.n_printers, S.unit_cost, 1)
    return b[0], np.corrcoef(S.n_printers, S.unit_cost)[0, 1] ** 2


def lead_slope(S):
    b = np.polyfit(S.batch_size, S.lead_h, 1)
    return b[0], np.corrcoef(S.batch_size, S.lead_h)[0, 1] ** 2


def pareto(df):
    d = df.sort_values(["lead_h", "unit_cost"]).reset_index(drop=True)
    keep, best = [], np.inf
    for _, row in d.iterrows():
        if row.unit_cost < best - 1e-9:
            best = row.unit_cost
            keep.append(row)
    return pd.DataFrame(keep)


def _hover(df):
    return [f"Scenario {r.Scenario}<br>Unit cost ${r.unit_cost:.2f} · "
            f"lead {r.lead_h:.1f} h<br>{int(r.n_printers)} printers · batch {int(r.batch_size)}"
            f" · A{int(r.assembly_cap)} Q{int(r.qual_cap)} P{int(r.postproc_cap)}"
            for r in df.itertuples()]


# ---------------------------------------------------------------- figures
def frontier(S, feas, rec, only_feas, color_by, rec_scen):
    d = feas if only_feas else S
    fig = go.Figure()
    if not only_feas:
        fig.add_vrect(x0=GATE, x1=max(S.lead_h.max() * 1.02, GATE + 1),
                      fillcolor=T.MIT_RED_WASH, line_width=0, layer="below")
    if color_by == "Printer count":
        fig.add_trace(go.Scatter(
            x=d.lead_h, y=d.unit_cost, mode="markers", name="scenario", showlegend=False,
            marker=dict(size=9, color=d.n_printers, colorscale=T.BLUE_SCALE,
                        cmin=S.n_printers.min(), cmax=S.n_printers.max(),
                        line=dict(width=1, color="#FFFFFF"),
                        colorbar=dict(title="Printers", thickness=12, len=0.6,
                                      x=1.02, tickvals=list(range(4, 10)), outlinewidth=0)),
            opacity=0.9, text=_hover(d), hovertemplate="%{text}<extra></extra>"))
    else:
        for name, sub, c, op in [("Meets 12 h", d[d.feasible], T.SLATE, 0.9),
                                 ("Misses 12 h", d[~d.feasible], T.SLATE_SOFT, 0.85)]:
            if len(sub):
                fig.add_trace(go.Scatter(
                    x=sub.lead_h, y=sub.unit_cost, mode="markers", name=name,
                    marker=dict(size=9, color=c, line=dict(width=1, color="#FFFFFF")),
                    opacity=op, text=_hover(sub), hovertemplate="%{text}<extra></extra>"))
    pf = pareto(S)
    fig.add_trace(go.Scatter(x=pf.lead_h, y=pf.unit_cost, mode="lines",
                             name="efficient frontier",
                             line=dict(color=T.INK, width=1.6, shape="hv"), hoverinfo="skip"))
    fig.add_vline(x=GATE, line=dict(color=T.MIT_RED, width=1.6, dash="dash"))
    fig.add_annotation(x=GATE, y=S.unit_cost.max(), text="12 h promise", showarrow=False,
                       xanchor="left", xshift=6, font=dict(color=T.MIT_RED, size=12))
    fig.add_trace(go.Scatter(
        x=[rec.lead_h], y=[rec.unit_cost], mode="markers+text",
        name=f"recommended ({rec_scen})", text=[f"  {rec_scen}"], textposition="middle right",
        textfont=dict(color=T.MIT_RED_INK, size=12),
        marker=dict(size=15, color=T.MIT_RED, symbol="diamond", line=dict(width=1.5, color="#FFFFFF")),
        hovertemplate=f"Recommended · {rec_scen}<br>${rec.unit_cost:.2f} · {rec.lead_h:.1f} h<extra></extra>"))
    T.style(fig, height=470, xtitle="Worst-case lead time  (hours)", ytitle="Unit cost  ($ / yo-yo)")
    fig.update_layout(margin=dict(r=84))
    return fig


def cost_scatter(S):
    fig = go.Figure()
    jit = np.random.default_rng(0).uniform(-.12, .12, len(S))
    fig.add_trace(go.Scatter(x=S.n_printers + jit, y=S.unit_cost, mode="markers",
                             name="design", marker=dict(size=6, color=T.SLATE_SOFT),
                             opacity=0.6, hoverinfo="skip"))
    m = S.groupby("n_printers").unit_cost.mean().reset_index()
    fig.add_trace(go.Scatter(x=m.n_printers, y=m.unit_cost, mode="lines+markers+text",
                             name="mean cost", line=dict(color=T.MIT_RED, width=2),
                             marker=dict(size=9, color=T.MIT_RED, line=dict(width=1.5, color="#FFF")),
                             text=[f"${v:.2f}" for v in m.unit_cost], textposition="top center",
                             textfont=dict(color=T.INK, size=11),
                             hovertemplate="%{x} printers<br>mean $%{y:.2f}<extra></extra>"))
    T.style(fig, height=380, xtitle="AM printers", ytitle="Unit cost  ($ / yo-yo)", legend=False)
    fig.update_xaxes(tickvals=list(range(4, 10)))
    fig.update_yaxes(range=[5.8, S.unit_cost.max() * 1.05])
    return fig


def cost_importance(S):
    imp, _ = lmg(S, CTRLS, "unit_cost")
    order = sorted(imp, key=lambda k: imp[k])
    vals = [imp[k] for k in order]
    cols = [T.MIT_RED if k == "n_printers" else T.SLATE for k in order]
    fig = go.Figure(go.Bar(
        x=vals, y=[CTRL_LABEL[k] for k in order], orientation="h",
        marker=dict(color=cols),
        text=[f"{v:.0f}%" if v >= 1 else f"{v:.1f}%" for v in vals], textposition="outside",
        textfont=dict(color=T.INK, size=11),
        hovertemplate="%{y}: %{x:.1f}% of explained cost variation<extra></extra>"))
    T.style(fig, height=380, xtitle="Share of cost variation explained (%)", legend=False)
    fig.update_layout(margin=dict(l=118))
    fig.update_xaxes(range=[0, 108])
    fig.update_yaxes(showgrid=False)
    return fig


def delivery_scatter(S, rec, rec_scen):
    fig = go.Figure()
    jit = np.random.default_rng(1).uniform(-.12, .12, len(S))
    fig.add_trace(go.Scatter(
        x=S.batch_size + jit, y=S.lead_h, mode="markers", name="design",
        marker=dict(size=8, color=S.n_printers, colorscale=T.BLUE_SCALE,
                    cmin=S.n_printers.min(), cmax=S.n_printers.max(),
                    line=dict(width=1, color="#FFFFFF"),
                    colorbar=dict(title="Printers", thickness=12, len=0.6,
                                  x=1.02, tickvals=list(range(4, 10)), outlinewidth=0)),
        opacity=0.85,
        text=[f"Scenario {r.Scenario}<br>batch {int(r.batch_size)} · {int(r.n_printers)} printers"
              f"<br>lead {r.lead_h:.1f} h · ${r.unit_cost:.2f}" for r in S.itertuples()],
        hovertemplate="%{text}<extra></extra>"))
    fig.add_hline(y=GATE, line=dict(color=T.MIT_RED, width=1.6, dash="dash"))
    fig.add_annotation(x=S.batch_size.max(), y=GATE, text="12 h promise", showarrow=False,
                       yanchor="bottom", xanchor="right", font=dict(color=T.MIT_RED, size=12))
    fig.add_trace(go.Scatter(x=[rec.batch_size], y=[rec.lead_h], mode="markers",
                             name=f"recommended ({rec_scen})",
                             marker=dict(size=14, color=T.MIT_RED, symbol="diamond",
                                         line=dict(width=1.5, color="#FFF")),
                             hovertemplate=f"Recommended {rec_scen}<extra></extra>"))
    T.style(fig, height=400, xtitle="Batch size (yo-yos per build)",
            ytitle="Worst-case lead time (h)", legend=False)
    fig.update_layout(margin=dict(r=84))
    fig.update_xaxes(tickvals=list(range(1, 11)))
    return fig


def utilization(src):
    stations = [("AM printers", src["AM_util"]), ("Post-processing", src["PostProcessing_util"]),
                ("Quality (QC)", src["DropTest_util"]), ("Assembly", src["Assembly_util"])]
    stations.sort(key=lambda x: x[1])
    fig = go.Figure(go.Bar(
        x=[v for _, v in stations], y=[n for n, _ in stations], orientation="h",
        marker=dict(color=[T.MIT_RED if n == "AM printers" else T.SLATE for n, _ in stations]),
        text=[f"{v:.0f}%" for _, v in stations], textposition="outside",
        textfont=dict(color=T.INK, size=12), hovertemplate="%{y}: %{x:.1f}% utilized<extra></extra>"))
    T.style(fig, height=360, xtitle="Scheduled utilization (%)", legend=False)
    fig.update_layout(margin=dict(l=118))
    fig.update_xaxes(range=[0, 104])
    fig.update_yaxes(showgrid=False)
    return fig


def cost_composition(S):
    # Grounded in Simio's own cost fields: red = CapitalCost (only the AM bank
    # has one); grey = UsageCostCharged (pay-per-use, billed only while working).
    parts = [("Printer capital", S.AM_capital.mean(), T.MIT_RED),
             ("Printer energy + material", S.AM_usage.mean(), T.SLATE),
             ("Post-processing", S.PostProcessing_totcost.mean(), "#6E7A88"),
             ("Quality", S.DropTest_totcost.mean(), "#98A0AA"),
             ("Assembly", S.Assembly_totcost.mean(), "#BFC4CB")]
    tot = sum(v for _, v, _ in parts)
    fig = go.Figure()
    for name, val, col in parts:
        fig.add_trace(go.Bar(x=[val / tot * 100], y=["cost"], orientation="h", name=name,
                             marker=dict(color=col, line=dict(width=2, color="#FFFFFF")),
                             text=[f"{val/tot*100:.0f}%" if val/tot*100 >= 6 else ""],
                             textposition="inside", insidetextanchor="middle",
                             textfont=dict(color="#FFFFFF", size=12),
                             hovertemplate=f"{name}: %{{x:.1f}}%<extra></extra>"))
    fig.update_layout(barmode="stack")
    T.style(fig, height=360, xtitle="Share of total system cost (%)", legend=True)
    fig.update_yaxes(showgrid=False, showticklabels=False)
    fig.update_xaxes(range=[0, 100])
    return fig, tot
