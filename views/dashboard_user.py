"""
User dashboard - farmer's view: their cattle with health status.
"""

import streamlit as st
from html import escape as _esc
from utils.translations import t
from utils.auth import get_lang, get_token, get_user, navigate_to
from utils.theme import get_palette, health_color, ACCENT
from utils.icons import (
    icon_cattle, icon_check_circle, icon_bell, icon_thermometer, icon_heart,
)
from services.api_client import api_get_cattle_list, api_get_all_latest, api_get_recent_health_events
from components.navbar import render_navbar
from components.live_panel import render_live_panel, classify
from components.glass import inject_glass_css, tokens, stat_card, section_header, dot, row, rgba


def render():
    lang = get_lang()
    token = get_token()
    user = get_user()
    p = get_palette()

    render_navbar()
    inject_glass_css()
    g = tokens()

    st.markdown(
        f"""<div style="font-size:1.45rem; font-weight:700; color:{g['text']};
            letter-spacing:-.02em; margin:.2rem 0 1rem;">
            {t('welcome', lang)}, <span style="color:{ACCENT['primary']};">
            {_esc(user.get('full_name', 'User'))}</span></div>""",
        unsafe_allow_html=True,
    )

    cattle_list = api_get_cattle_list(token) or []
    latest_data = api_get_all_latest(token) or []
    recent_events = api_get_recent_health_events(token, limit=10) or []

    latest_by_cid = {item["cid"]: item for item in latest_data}

    total = len(cattle_list)
    active = sum(1 for c in cattle_list if c.get("status") == "active")
    alert_count = len(recent_events)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(stat_card(icon_cattle("#FFFFFF", 19), t("my_cattle", lang), str(total),
                              ACCENT["primary"]), unsafe_allow_html=True)
    with col2:
        st.markdown(stat_card(icon_check_circle("#FFFFFF", 19), t("active", lang), str(active),
                              ACCENT["green"]), unsafe_allow_html=True)
    with col3:
        st.markdown(stat_card(icon_bell("#FFFFFF", 19), t("active_alerts", lang), str(alert_count),
                              ACCENT["red"] if alert_count > 0 else ACCENT["green"]),
                    unsafe_allow_html=True)

    st.markdown("---")

    render_live_panel(token, cattle_list, lang, key="user")

    st.markdown(section_header(icon_cattle("#FFFFFF", 16), t("my_cattle", lang),
                               ACCENT["primary"]), unsafe_allow_html=True)

    if not cattle_list:
        st.info(t("no_data", lang))
        return

    search = st.text_input(f"{t('search', lang)}", placeholder=f"{t('search', lang)}...",
                           label_visibility="collapsed")
    filtered = cattle_list
    if search:
        s = search.lower()
        filtered = [c for c in cattle_list if s in c.get("name", "").lower() or s in c.get("breed", "").lower()]

    cols_per_row = 3
    for i in range(0, len(filtered), cols_per_row):
        cols = st.columns(cols_per_row)
        for j, col in enumerate(cols):
            idx = i + j
            if idx >= len(filtered):
                break
            cattle = filtered[idx]
            cid = cattle["cid"]
            sensor = latest_by_cid.get(cid)

            with col:
                _render_cattle_card(cattle, sensor, lang, p)

    if recent_events:
        st.markdown("---")
        st.markdown(section_header(icon_bell("#FFFFFF", 16), t("recent_alerts", lang),
                                   ACCENT["red"]), unsafe_allow_html=True)
        for event in recent_events[:5]:
            level = event.get("status", "warning")
            color = health_color(level, p)
            st.markdown(
                row(
                    f"""{dot(color)}<strong>CID {event.get('cid', '?')}</strong> —
                    {_esc(str(event.get('event', event.get('status', 'Alert'))))}
                    <span style="color:{g['text_dim']}; font-size:.76rem; float:right;">
                        {str(event.get('timestamp', ''))[:19]}</span>""",
                    color,
                ),
                unsafe_allow_html=True,
            )


def _render_cattle_card(cattle: dict, sensor: dict | None, lang: str, p: dict):
    g = tokens()
    cid = cattle["cid"]
    name = _esc(cattle.get("name", f"Cattle {cid}"))
    breed = _esc(cattle.get("breed", "Unknown"))
    age = cattle.get("age", 0)

    temp = sensor.get("temperature", 0) if sensor else 0
    bpm = sensor.get("heart", {}).get("bpm", 0) if sensor else 0

    h_status = classify(temp, bpm)
    h_color = health_color(h_status, p)
    h_label = t(h_status, lang)

    temp_str = f"{temp:.1f}°C" if temp > 0 else "—"
    bpm_str = f"{bpm:.0f}" if bpm > 0 else "—"
    ts = str(sensor.get("timestamp_iso", ""))[:16] if sensor else t("no_data", lang)

    st.markdown(
        f"""<div class="cc-glass" style="padding:1rem; margin-bottom:.75rem;">
            <div style="display:flex; justify-content:space-between; align-items:center;">
                <span style="font-weight:700; font-size:1.05rem; color:{g['text']};
                      letter-spacing:-.01em;">{name}</span>
                <span style="display:inline-flex; align-items:center; background:{rgba(h_color, 0.14)};
                      color:{h_color}; border:1px solid {rgba(h_color, 0.45)}; padding:2px 10px;
                      border-radius:999px; font-size:.72rem; font-weight:700;">
                      {dot(h_color, 7)}{h_label}</span></div>
            <div style="color:{g['text_dim']}; font-size:.82rem; margin-top:.45rem;">
                {breed} · {age} {t('years', lang)}</div>
            <div style="display:flex; gap:.6rem; margin-top:.8rem;">
                <div style="flex:1; text-align:center; background:{rgba(ACCENT['red'], 0.09)};
                     border:1px solid {rgba(ACCENT['red'], 0.20)}; padding:.5rem; border-radius:10px;">
                    <div style="font-size:.68rem; color:{g['text_dim']}; font-weight:600;
                         letter-spacing:.05em;">{icon_thermometer(g['text_dim'], 12)}
                         {t('temperature', lang).upper()}</div>
                    <div style="font-weight:700; color:{g['text']}; margin-top:2px;">{temp_str}</div></div>
                <div style="flex:1; text-align:center; background:{rgba(ACCENT['green'], 0.09)};
                     border:1px solid {rgba(ACCENT['green'], 0.20)}; padding:.5rem; border-radius:10px;">
                    <div style="font-size:.68rem; color:{g['text_dim']}; font-weight:600;
                         letter-spacing:.05em;">{icon_heart(g['text_dim'], 12)}
                         {t('bpm', lang).upper()}</div>
                    <div style="font-weight:700; color:{g['text']}; margin-top:2px;">{bpm_str}</div></div></div>
            <div style="color:{g['text_dim']}; font-size:.7rem; margin-top:.6rem;">
                {t('last_updated', lang)}: {ts}</div></div>""",
        unsafe_allow_html=True,
    )

    if st.button(f"{t('view_details', lang)}", key=f"view_{cid}", use_container_width=True):
        navigate_to("cattle_detail", selected_cattle_cid=cid)
        st.rerun()
