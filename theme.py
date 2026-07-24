"""Shared visual system for the Yo-Yo AM dashboard.

Minimalist, near-white, MIT-red accent. Palette validated with the dataviz
color checker: red (#A31F34) vs series blue is well separated (CVD dE 24.5);
printer count uses a single-hue blue sequential ramp (light -> dark).
"""
import inspect
import plotly.graph_objects as go
import streamlit as st

# ---- ink & chrome ----
INK      = "#1A1A1A"   # primary text / marks
SECOND   = "#55534E"   # secondary text
MUTED    = "#8A8B8C"   # axis ticks / labels (MIT secondary gray)
GRID     = "#ECEBE7"   # hairline gridlines
AXIS     = "#CFCEC8"   # baseline / axis line
SURFACE  = "#FFFFFF"   # chart surface
PAGE     = "#F6F6F4"

# ---- MIT red accent (reserved: constraint line + recommended config) ----
MIT_RED       = "#A31F34"
MIT_RED_INK   = "#7A1727"
MIT_RED_WASH  = "rgba(163,31,52,0.07)"   # infeasible region / soft fill

# ---- neutral series (de-emphasised marks) ----
SLATE      = "#4A5A6A"
SLATE_SOFT = "#C9CDD2"

FONT = "Segoe UI, system-ui, -apple-system, sans-serif"

# Single-hue blue sequential ramp for printer count (magnitude).
BLUE_SCALE = [
    [0.00, "#9ec5f4"],
    [0.22, "#5598e7"],
    [0.45, "#2a78d6"],
    [0.68, "#1c5cab"],
    [0.85, "#184f95"],
    [1.00, "#0d366b"],
]

PLOTLY_CONFIG = {
    "displayModeBar": False,
    "displaylogo": False,
    "scrollZoom": False,
}

# plotly_chart changed its width API across versions; call it the way this
# installed version supports so no deprecation notice ever reaches the UI.
_HAS_WIDTH = "width" in inspect.signature(st.plotly_chart).parameters


def show(fig, key=None):
    if _HAS_WIDTH:
        st.plotly_chart(fig, width="stretch", config=PLOTLY_CONFIG, key=key)
    else:  # pragma: no cover - older streamlit
        st.plotly_chart(fig, use_container_width=True, config=PLOTLY_CONFIG, key=key)


def style(fig, height=430, xtitle=None, ytitle=None, legend=True):
    """Apply the shared minimalist look to a Plotly figure."""
    fig.update_layout(
        template="none",
        height=height,
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(family=FONT, size=13, color=SECOND),
        margin=dict(l=64, r=24, t=28, b=52),
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=AXIS,
                        font=dict(family=FONT, size=12, color=INK)),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left",
                    x=0, font=dict(color=SECOND, size=12), bgcolor="rgba(0,0,0,0)"),
    )
    axkw = dict(showgrid=True, gridcolor=GRID, gridwidth=1, zeroline=False,
                linecolor=AXIS, linewidth=1, ticks="outside", ticklen=4,
                tickcolor=AXIS, tickfont=dict(color=MUTED, size=12),
                title_font=dict(color=SECOND, size=13))
    fig.update_xaxes(**axkw)
    fig.update_yaxes(**axkw)
    if xtitle is not None:
        fig.update_xaxes(title_text=xtitle)
    if ytitle is not None:
        fig.update_yaxes(title_text=ytitle)
    return fig


# ---- HTML component snippets ------------------------------------------------
CSS = f"""
<style>
  .block-container {{ padding-top: 2.2rem; padding-bottom: 3rem; max-width: 1180px; }}
  h1, h2, h3 {{ color: {INK}; letter-spacing: -0.01em; }}
  h1 {{ font-weight: 700; font-size: 1.9rem; margin-bottom: .1rem; }}
  .subtitle {{ color: {SECOND}; font-size: 1rem; margin: 0 0 .2rem 0; }}
  .rule {{ height: 3px; width: 46px; background: {MIT_RED}; border-radius: 2px; margin: .5rem 0 1.2rem 0; }}
  /* insight callout */
  .insight {{ border-left: 3px solid {MIT_RED}; background: {PAGE};
             padding: .85rem 1.1rem; border-radius: 0 8px 8px 0; margin: .2rem 0 1.3rem 0; }}
  .insight b {{ color: {INK}; }}
  .insight .lead {{ font-size: 1.06rem; color: {INK}; font-weight: 600; line-height: 1.4; }}
  .insight .sub {{ font-size: .9rem; color: {SECOND}; margin-top: .35rem; line-height: 1.5; }}
  /* KPI cards */
  .kpis {{ display: flex; gap: 14px; flex-wrap: wrap; margin: .2rem 0 1rem 0; }}
  .kpi {{ flex: 1 1 150px; border: 1px solid #EAE9E4; border-radius: 12px;
          padding: .85rem 1rem; background: {SURFACE}; }}
  .kpi .l {{ font-size: .72rem; text-transform: uppercase; letter-spacing: .06em; color: {MUTED}; }}
  .kpi .v {{ font-size: 1.7rem; font-weight: 700; color: {INK}; line-height: 1.15; margin-top: .15rem; }}
  .kpi .s {{ font-size: .8rem; color: {SECOND}; margin-top: .1rem; }}
  .kpi.accent {{ border-color: {MIT_RED}; box-shadow: 0 0 0 1px {MIT_RED} inset; }}
  .note {{ color: {SECOND}; font-size: .86rem; line-height: 1.55; }}
  .tag {{ display:inline-block; font-size:.74rem; padding:.12rem .5rem; border-radius:999px;
          background:{MIT_RED_WASH}; color:{MIT_RED_INK}; border:1px solid rgba(163,31,52,.25);
          white-space:nowrap; }}
  /* recommended strip: pill + message + specs, all vertically centered */
  .recbar {{ display:flex; align-items:center; gap:8px 14px; flex-wrap:wrap;
             margin:.15rem 0 1.15rem 0; }}
  .recbar .msg {{ font-size:.96rem; color:{INK}; font-weight:600; }}
  .recbar .spec {{ font-size:.85rem; color:{MUTED}; letter-spacing:.01em; }}
</style>
"""


def kpi_row(items):
    """items: list of (label, value, sub, accent_bool)."""
    cards = []
    for label, value, sub, accent in items:
        cls = "kpi accent" if accent else "kpi"
        cards.append(
            f'<div class="{cls}"><div class="l">{label}</div>'
            f'<div class="v">{value}</div><div class="s">{sub}</div></div>')
    return f'<div class="kpis">{"".join(cards)}</div>'


def insight(lead, sub=""):
    return (f'<div class="insight"><div class="lead">{lead}</div>'
            + (f'<div class="sub">{sub}</div>' if sub else "") + "</div>")
