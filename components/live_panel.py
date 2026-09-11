"""
Live dashboard panel: polls the backend every 3 seconds and redraws the herd
KPIs and trend chart. Only this fragment reruns, so the rest of the page is untouched.
"""

import streamlit as st
from datetime import datetime

from utils.translations import t
from utils.theme import get_palette, ACCENT
from utils.icons import (
    icon_broadcast, icon_thermometer, icon_heart, icon_heart_pulse,
    icon_clock, icon_info,
)
from services.api_client import api_get_all_latest, api_get_cattle_recent
from components.charts import build_live_trend_chart
from components.glass import tokens, stat_card, dot, tile, rgba

REFRESH_SECONDS = 3
TREND_POINTS = 80


def render_live_panel(token: str, cattle_list: list, lang: str, key: str = "dash") -> None:
    """Pause lives outside the fragment so toggling it rebuilds the fragment."""
    if not cattle_list:
        return

    g = tokens()

    head, ctrl = st.columns([4, 1])
    with head:
        st.markdown(
            f"""<div style="display:flex; align-items:center; gap:.65rem; padding-top:.3rem;">
                {tile(icon_broadcast("#FFFFFF", 18), ACCENT["primary"], size=34)}
                <div>
                    <div style="font-size:1.12rem; font-weight:700; color:{g['text']};
                                letter-spacing:-.01em;">{t('live_monitor', lang)}</div>
                    <div style="font-size:.74rem; color:{g['text_dim']}; font-weight:600;
                                letter-spacing:.05em; text-transform:uppercase;">
                        {REFRESH_SECONDS}s {t('auto_refresh', lang)}</div>
                </div></div>""",
            unsafe_allow_html=True,
        )
    with ctrl:
        st.markdown("<div style='height:.65rem;'></div>", unsafe_allow_html=True)
        paused = st.toggle(t("pause", lang), key=f"{key}_live_paused")

    body = st.fragment(run_every=None if paused else REFRESH_SECONDS)(_live_body)
    body(token, cattle_list, lang, key, paused)


def _live_body(token: str, cattle_list: list, lang: str, key: str, paused: bool) -> None:
    p = get_palette()
    g = tokens()

    latest = api_get_all_latest(token) or []
    latest_by_cid = {r["cid"]: r for r in latest if "cid" in r}

    temps, bpms = [], []
    counts = {"healthy": 0, "warning": 0, "critical": 0}
    for c in cattle_list:
        sensor = latest_by_cid.get(c["cid"])
        temp = sensor.get("temperature", 0) if sensor else 0
        bpm = sensor.get("heart", {}).get("bpm", 0) if sensor else 0
        if temp > 0:
            temps.append(temp)
        if bpm > 0:
            bpms.append(bpm)
        counts[classify(temp, bpm)] += 1

    reporting = sum(1 for c in cattle_list if c["cid"] in latest_by_cid)
    avg_temp = f"{sum(temps) / len(temps):.1f}°C" if temps else "—"
    avg_bpm = f"{sum(bpms) / len(bpms):.0f}" if bpms else "—"

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(stat_card(icon_thermometer("#FFFFFF", 19), t("avg_temperature", lang),
                              avg_temp, ACCENT["red"]), unsafe_allow_html=True)
    with k2:
        st.markdown(stat_card(icon_heart("#FFFFFF", 19), t("avg_heart_rate", lang),
                              avg_bpm, ACCENT["green"]), unsafe_allow_html=True)
    with k3:
        st.markdown(stat_card(icon_broadcast("#FFFFFF", 19), t("reporting", lang),
                              f"{reporting}/{len(cattle_list)}", ACCENT["primary"]),
                    unsafe_allow_html=True)
    with k4:
        st.markdown(stat_card(icon_heart_pulse("#FFFFFF", 19), t("herd_health", lang),
                              _health_chips(p, counts), ACCENT["purple"], value_is_html=True),
                    unsafe_allow_html=True)

    sel = st.selectbox(
        t("select_cattle", lang),
        options=[c["cid"] for c in cattle_list],
        format_func=lambda x: f"CID {x} — {next((c.get('name', '') for c in cattle_list if c['cid'] == x), '')}",
        key=f"{key}_live_cid",
    )

    readings = api_get_cattle_recent(token, sel, limit=TREND_POINTS) or []
    readings.reverse()

    if readings:
        st.plotly_chart(build_live_trend_chart(readings), use_container_width=True)
    else:
        st.markdown(
            f"""<div class="cc-row" style="border-left-color:{p['status_info_border']};">
                {icon_info(g['text_dim'], 14)} {t('no_data', lang)}</div>""",
            unsafe_allow_html=True,
        )

    state = t("paused", lang) if paused else t("live", lang)
    state_color = ACCENT["yellow"] if paused else ACCENT["red"]
    mark = dot(state_color, 9) if paused else '<span class="cc-live-ring"></span>'
    st.markdown(
        f"""<div style="display:flex; align-items:center; gap:.4rem; font-size:.76rem;
            color:{g['text_dim']}; margin-top:-.35rem;">
            {mark}
            <span style="font-weight:700; color:{state_color}; letter-spacing:.06em;
                  text-transform:uppercase;">{state}</span>
            <span style="opacity:.55;">·</span>
            {icon_clock(g['text_dim'], 12)}
            <span>{t('last_synced', lang)} {datetime.now().strftime('%H:%M:%S')}</span>
        </div>""",
        unsafe_allow_html=True,
    )
    st.markdown("---")


def classify(temp: float, bpm: float) -> str:
    if temp > 39.5 or (bpm > 100 and bpm > 0) or (0 < bpm < 30):
        return "critical"
    if 0 < temp < 35.0:
        return "warning"
    return "healthy"


def _health_chips(p: dict, counts: dict) -> str:
    chips = [
        (counts["healthy"], p["status_success_border"]),
        (counts["warning"], p["status_warning_border"]),
        (counts["critical"], p["status_danger_border"]),
    ]
    inner = "".join(
        f"""<span class="cc-chip" style="background:{rgba(color, 0.14)}; color:{color};
            border:1px solid {rgba(color, 0.45)};">{dot(color, 8)}{n}</span>"""
        for n, color in chips
    )
    return f'<div style="display:flex; align-items:center; padding-top:2px;">{inner}</div>'
