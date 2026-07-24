"""
Yo-Yo Additive Manufacturing Line, Challenge 1
Optimization insights from the Simio experiment (300 scenarios x 10 replications).

Headline metrics come straight from Simio's authoritative response export
(unit cost = TotalCost response; lead time = worst-case order flow time).
Every number shown is computed from the data at load time, so text and charts
can never disagree. Figure builders live in charts.py (shared with the QA harness).
"""
from pathlib import Path

import pandas as pd
import streamlit as st

import theme as T
import charts as C

st.set_page_config(page_title="Yo-Yo AM Line · Challenge 1",
                   page_icon="🪀", layout="wide")
st.markdown(T.CSS, unsafe_allow_html=True)

DATA = Path(__file__).parent / "data"
GATE = C.GATE
REC_SCEN = "004"    # slide recommendation = data-optimal cheapest feasible config


@st.cache_data
def load():
    return (pd.read_parquet(DATA / "scenarios.parquet"),
            pd.read_parquet(DATA / "replications.parquet"))


S, R = load()
feas = S[S.feasible]
rec = S[S.Scenario == REC_SCEN].iloc[0]
gmin = S.loc[S.unit_cost.idxmin()]
fmin = feas.loc[feas.unit_cost.idxmin()]
premium = fmin.unit_cost - gmin.unit_cost
within_fleet_swing = (S[S.n_printers == rec.n_printers].unit_cost.max()
                      - S[S.n_printers == rec.n_printers].unit_cost.min())

# ============================ HEADER ========================================
st.markdown("# Yo-Yo AM Line · Challenge 1")
st.markdown('<div class="subtitle">SLS / MJF additive manufacturing · minimize unit '
            'production cost while every order ships in under 12&nbsp;hours · '
            '300 optimization scenarios × 10 replications</div>', unsafe_allow_html=True)
st.markdown('<div class="rule"></div>', unsafe_allow_html=True)

st.markdown(T.kpi_row([
    ("Unit cost", f"${rec.unit_cost:.2f}", "per saleable yo-yo", True),
    ("Worst-case lead time", f"{rec.lead_h:.2f} h", "under the 12 h promise", True),
    ("AM printers", f"{int(rec.n_printers)}", "the launch fleet", False),
    ("Printer utilization", f"{rec.am_util:.0f}%", "the binding constraint", False),
]), unsafe_allow_html=True)
st.markdown(
    f'<div class="recbar">'
    f'<span class="tag">Recommended · {REC_SCEN}</span>'
    f'<span class="msg">Cheapest design that clears the 12&nbsp;hour promise.</span>'
    f'<span class="spec">{int(rec.n_printers)} printers · batch {int(rec.batch_size)} · '
    f'assembly {int(rec.assembly_cap)} · quality {int(rec.qual_cap)} · '
    f'post-proc {int(rec.postproc_cap)}</span>'
    f'</div>', unsafe_allow_html=True)

# ============================ TABS ==========================================
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "  Cost vs delivery  ", "  Cost is a printer story  ",
    "  Delivery is a batch story  ", "  The bottleneck  ", "  Explore  "])

# ---------------------------------------------------------------- FRONTIER
with tab1:
    st.markdown(T.insight(
        f"Meeting the 12-hour promise costs just <b>${premium:.2f} a unit</b> "
        f"(+{premium / gmin.unit_cost * 100:.1f}%).",
        "Cost is set almost entirely by how many printers you own; delivery is set "
        "mainly by batch size. The cheapest design of all runs a huge batch and misses "
        f"the promise at {gmin.lead_h:.0f} h, so holding to 12 h barely moves the cost "
        "floor. The recommended design uses the fewest printers and the largest batch "
        "those printers can still clear in 12 hours."), unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])
    only_feas = c1.toggle("Show only designs that meet the 12 h promise", value=False)
    color_by = c2.radio("Color points by", ["Printer count", "Feasibility"],
                        horizontal=True, label_visibility="collapsed")

    T.show(C.frontier(S, feas, rec, only_feas, color_by, REC_SCEN))
    st.markdown(
        f'<p class="note">Cheapest feasible: scenario {fmin.Scenario} at '
        f'${fmin.unit_cost:.2f} / {fmin.lead_h:.1f} h. Cheapest of all (ignoring the '
        f'promise): scenario {gmin.Scenario} at ${gmin.unit_cost:.2f} but {gmin.lead_h:.1f} h. '
        f'{int(S.feasible.sum())} of 300 designs meet the gate. The recommended design '
        f'clears 12 h on the average of its 10 runs ({rec.lead_h:.2f} h); its worst single '
        f'run reached {rec.lead_h_max:.1f} h, so the margin is real but slim.</p>',
        unsafe_allow_html=True)

# ---------------------------------------------------------------- COST
with tab2:
    slope, r2 = C.cost_slope(S)
    imp, _ = C.lmg(S, C.CTRLS, "unit_cost")
    st.markdown(T.insight(
        f"Unit cost is a staircase in printer count: printers explain "
        f"<b>{imp['n_printers']:.0f}%</b> of all cost variation, at roughly "
        f"<b>+${slope:.2f} a unit per machine</b>.",
        "Output is fixed by demand (about 9,400 good yo-yos in every design), so every "
        "pay-per-use cost is a flat floor. The one cost you actually change is printer "
        "capital, and printers come in whole machines, so cost jumps one lump per printer. "
        "Each added printer costs more capital than the last, so over-provisioning is "
        "punished harder and harder."), unsafe_allow_html=True)

    c1, c2 = st.columns([1.25, 1])
    with c1:
        T.show(C.cost_scatter(S))
        st.markdown(f'<p class="note">Each dot is one design; the red line is the mean at '
                    f'each fleet size. Within a fleet size, everything else combined moves '
                    f'cost by under ${within_fleet_swing:.2f} a unit.</p>',
                    unsafe_allow_html=True)
    with c2:
        T.show(C.cost_importance(S))
        st.markdown('<p class="note">LMG variance decomposition (shares sum to 100%). '
                    'Printer count explains almost all of it; batch size and the labor '
                    'capacities are effectively free to the cost line.</p>',
                    unsafe_allow_html=True)

# ---------------------------------------------------------------- DELIVERY
with tab3:
    ls, lr2 = C.lead_slope(S)
    imp_l, _ = C.lmg(S, C.CTRLS, "lead_h")
    maxb_rec = int(feas[feas.n_printers == rec.n_printers].batch_size.max())
    st.markdown(T.insight(
        f"Batch size sets the clock: it drives <b>{imp_l['batch_size']:.0f}%</b> of the "
        f"lead-time variation, printer count the other <b>{imp_l['n_printers']:.0f}%</b>.",
        "Bigger batches take longer to print, so the worst-case order time climbs; more "
        "printers build batches in parallel and pull it back down. At the launch fleet of "
        f"{int(rec.n_printers)} printers, any batch above {maxb_rec} pushes the worst case "
        f"past 12 h, which is why the optimum runs batch {int(rec.batch_size)}."),
        unsafe_allow_html=True)

    T.show(C.delivery_scatter(S, rec, REC_SCEN))
    st.markdown('<p class="note">Colour is fleet size: within each batch column, designs '
                'with more printers (darker) sit lower. The dashed line is the 12 h promise; '
                'the red diamond is the recommended design.</p>', unsafe_allow_html=True)

# ---------------------------------------------------------------- BOTTLENECK
with tab4:
    st.markdown(T.insight(
        f"The printers are the only capacity you pay to <i>own</i>, and the only real "
        f"constraint: <b>{rec.am_util:.0f}% busy</b> at the optimum while assembly runs at "
        f"<b>{rec.Assembly_util:.0f}%</b>.",
        "Labor is billed only while working, so those idle assembly, quality and "
        "post-processing workers cost nothing; adding capacity there is free but pointless. "
        "Printer capital is the one cost your design controls, which is why the whole problem "
        "reduces to buying as few printers as the 12 h promise allows."), unsafe_allow_html=True)

    c1, c2 = st.columns([1, 1])
    with c1:
        which = st.radio("Utilization for", [f"Recommended ({REC_SCEN})", "Average of all designs"],
                         horizontal=True, label_visibility="collapsed")
        src = rec if which.startswith("Recommended") else S.mean(numeric_only=True)
        T.show(C.utilization(src))
        st.markdown('<p class="note">One unit of capacity = one worker (or one printer). '
                    'The labor stations sit far below full use, but since labor is pay-per-use '
                    'that idleness is costless; it just confirms they are nowhere near the '
                    'constraint.</p>', unsafe_allow_html=True)
    with c2:
        fig, tot = C.cost_composition(S)
        T.show(fig)
        st.markdown(f'<p class="note">Red is Simio\'s <code>CapitalCost</code>, the printer '
                    f'bank\'s fixed investment (it scales only with printer count). Grey is '
                    f'pay-per-use (<code>UsageCostCharged</code>): the printer\'s energy and '
                    f'material, and the stations\' wage, all billed only while working, so it '
                    f'is fixed by the ~9,400 units of demand and near-identical for every '
                    f'design. Only the red slice ({S.AM_capital.mean()/tot*100:.0f}%) responds '
                    f'to your decisions. Yield holds at {S.yield_pct.mean():.0f}% throughout.</p>',
                    unsafe_allow_html=True)

# ---------------------------------------------------------------- EXPLORE
with tab5:
    st.markdown('<p class="note">All 300 designs. Sort any column; toggle the promise filter. '
                'Each row averages the design\'s 10 replications.</p>', unsafe_allow_html=True)
    only = st.toggle("Only designs that meet the 12 h promise", value=False, key="expl")
    view = feas if only else S
    show_cols = {"Scenario": "Scenario", "assembly_cap": "Assembly", "qual_cap": "Quality",
                 "postproc_cap": "Post-proc", "n_printers": "Printers", "batch_size": "Batch",
                 "unit_cost": "Unit cost $", "lead_h": "Lead h", "batch_h": "Batch time h",
                 "am_util": "AM util %", "yield_pct": "Yield %", "feasible": "Meets 12 h"}
    tbl = view[list(show_cols)].rename(columns=show_cols).sort_values("Unit cost $")
    st.dataframe(
        tbl, hide_index=True, height=430,
        column_config={
            "Unit cost $": st.column_config.NumberColumn(format="$%.2f"),
            "Lead h": st.column_config.NumberColumn(format="%.2f"),
            "Batch time h": st.column_config.NumberColumn(format="%.2f"),
            "AM util %": st.column_config.NumberColumn(format="%.0f"),
            "Yield %": st.column_config.NumberColumn(format="%.1f"),
            "Meets 12 h": st.column_config.CheckboxColumn(),
        })
    st.download_button("Download processed scenarios (CSV)",
                       S[list(show_cols)].rename(columns=show_cols).to_csv(index=False),
                       file_name="yoyo_scenarios.csv", mime="text/csv")

# ============================ METHOD NOTE ===================================
with st.expander("Metric definitions & data"):
    st.markdown(
        f'''<p class="note">
        Every design was simulated for one year (240 days × 8 h) and repeated over 10
        replications.<br><br>
        <b>Unit cost</b> is Simio's <code>TotalCost</code> response: total annualized system
        cost per saleable yo-yo, averaged over the 10 replications.<br><br>
        <b>Lead time</b> is the worst-case order flow time. Inside a single replication it is
        the <b>maximum</b> time any order spends in the system (arrival, printing,
        post-processing, assembly, QC), because the "every order under 12 h" promise is a hard
        guarantee, so the slowest order is what must clear the gate. Each scenario value is the
        <b>average of that per-run maximum</b> across the 10 replications.<br><br>
        <b>Feasible</b> means that averaged worst case is below {GATE:.0f} h.<br><br>
        <b>Cost fields.</b> Each object reports <code>CapitalCost</code>,
        <code>UsageCostCharged</code> and <code>IdleCost</code>, which sum exactly to its
        <code>TotalCost</code> (verified for all 300 scenarios). Only the AM printer bank has
        a capital cost, and it scales only with printer count; every usage cost is billed only
        while working. The AM printer's usage is energy plus material; the labor stations are
        wage. This export reports each object's usage as one combined figure, so energy and
        material are shown together, not split.<br><br>
        Data: Simio ResponseDetail + ResultsDetail exports, AM_Model SLS/MJF.
        </p>''', unsafe_allow_html=True)
