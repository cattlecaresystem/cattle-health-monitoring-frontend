"""
Live-updating dashboard panel: auto-refreshing herd KPIs and a per-cattle trend chart.
"""

import streamlit as st
from datetime import datetime

from utils.translations import t
from utils.theme import get_palette, ACCENT
from services.api_client import api_get_all_latest, api_get_cattle_recent
from components.charts import build_live_trend_chart

REFRESH_CHOICES = [5, 10, 30, 60]


def inject_dashboard_css() -> None:
    """Card hover lift and the pulsing live indicator used across dashboards."""
    st.markdown(
        """<style>
        .cc-card { transition: transform .15s ease, box-shadow .15s ease; }
        .cc-card:hover { transform: translateY(-3px); }
        @keyframes cc-pulse {
            0%   { opacity: 1;   transform: scale(1); }
            50%  { opacity: .30; transform: scale(.78); }
            100% { opacity: 1;   transform: scale(1); }
        }
        .cc-live-dot {
            display: inline-block; width: 9px; height: 9px; border-radius: 50%;
            background: #CF222E; margin-right: 7px;
            animation: cc-pulse 1.4s ease-in-out infinite;
        }
        .cc-chip {
            display: inline-block; padding: 2px 10px; border-radius: 999px;
            font-size: .75rem; font-weight: 600; margin-right: 6px;
        }
        </style>""",
        unsafe_allow_html=True,
    )


def render_live_panel(token: str, cattle_list: list, lang: str, key: str = "dash") -> None:
    """Auto-refreshing herd overview. Controls live outside the fragment so that
    changing them rebuilds the fragment with a new refresh interval."""
    if not cattle_list:
        return

    p = get_palette()

    head, ctrl_int, ctrl_pause = st.columns([3, 1, 1])
    with head:
        st.markdown(
            f"""<div style="display:flex; align-items:center; font-size:1.25rem;
                font-weight:700; color:{p['text']}; padding-top:.35rem;">
                <span class="cc-live-dot"></span>{t('live_monitor', lang)}</div>""",
            unsafe_allow_html=True,
        )
    with ctrl_int:
        interval = st.selectbox(
            t("refresh_interval", lang),
            options=REFRESH_CHOICES,
            index=1,
            format_func=lambda s: f"{s}s",
            key=f"{key}_live_interval",
        )
    with ctrl_pause:
        st.markdown("<div style='height:1.7rem;'></div>", unsafe_allow_html=True)
        paused = st.toggle(t("pause", lang), key=f"{key}_live_paused")

    body = st.fragment(run_every=None if paused else interval)(_live_body)
    body(token, cattle_list, lang, key, paused)


def _live_body(token: str, cattle_list: list, lang: str, key: str, paused: bool) -> None:
    p = get_palette()

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
        counts[_classify(temp, bpm)] += 1

    reporting = sum(1 for c in cattle_list if c["cid"] in latest_by_cid)
    avg_temp = f"{sum(temps) / len(temps):.1f}°C" if temps else "—"
    avg_bpm = f"{sum(bpms) / len(bpms):.0f}" if bpms else "—"

    k1, k2, k3, k4 = st.columns(4)
    with k1:
        st.markdown(_kpi(p, "🌡️", t("avg_temperature", lang), avg_temp, ACCENT["red"]),
                    unsafe_allow_html=True)
    with k2:
        st.markdown(_kpi(p, "❤️", t("avg_heart_rate", lang), avg_bpm, ACCENT["green"]),
                    unsafe_allow_html=True)
    with k3:
        st.markdown(_kpi(p, "📡", t("reporting", lang), f"{reporting}/{len(cattle_list)}",
                         ACCENT["primary"]), unsafe_allow_html=True)
    with k4:
        st.markdown(_kpi(p, "🩺", t("herd_health", lang), _health_chips(p, counts),
                         ACCENT["purple"], raw_value=True), unsafe_allow_html=True)

    sel = st.selectbox(
        t("select_cattle", lang),
        options=[c["cid"] for c in cattle_list],
        format_func=lambda x: f"CID {x} — {next((c.get('name', '') for c in cattle_list if c['cid'] == x), '')}",
        key=f"{key}_live_cid",
    )

    readings = api_get_cattle_recent(token, sel, limit=120) or []
    readings.reverse()

    if readings:
        st.plotly_chart(build_live_trend_chart(readings), use_container_width=True)
    else:
        st.info(f"ℹ️ {t('no_data', lang)}")

    state = t("paused", lang) if paused else t("live", lang)
    st.caption(f"⟳ {t('last_synced', lang)}: {datetime.now().strftime('%H:%M:%S')} · {state}")
    st.markdown("---")


def _classify(temp: float, bpm: float) -> str:
    if temp > 39.5 or (bpm > 100 and bpm > 0) or (0 < bpm < 30):
        return "critical"
    if 0 < temp < 35.0:
        return "warning"
    return "healthy"


def _health_chips(p: dict, counts: dict) -> str:
    chips = [
        ("healthy", counts["healthy"], p["status_success_bg"], p["status_success_border"]),
        ("warning", counts["warning"], p["status_warning_bg"], p["status_warning_border"]),
        ("critical", counts["critical"], p["status_danger_bg"], p["status_danger_border"]),
    ]
    return "".join(
        f"""<span class="cc-chip" style="background:{bg}; color:{fg}; border:1px solid {fg};">
            {n}</span>"""
        for _, n, bg, fg in chips
    )


def _kpi(p: dict, icon: str, label: str, value: str, color: str, raw_value: bool = False) -> str:
    value_html = (
        value if raw_value
        else f'<div style="font-size:1.6rem; font-weight:700; color:{color};">{value}</div>'
    )
    return f"""
    <div class="cc-card" style="background: {p['card_bg']}; border: 1px solid {p['card_border']};
                border-top: 3px solid {color}; border-radius: 10px; padding: .9rem;
                text-align: center; box-shadow: 0 1px 3px {p['card_shadow']};">
        <div style="font-size: 1.1rem;">{icon}</div>
        <div style="min-height: 2.1rem; display: flex; align-items: center;
                    justify-content: center;">{value_html}</div>
        <div style="color: {p['text_secondary']}; font-size: .78rem;">{label}</div>
    </div>"""
