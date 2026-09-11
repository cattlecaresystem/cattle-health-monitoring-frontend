"""
Admin dashboard - scoped to their farms: their users, cattle, and alerts.
"""

import streamlit as st
import pandas as pd
from html import escape as _esc
from utils.translations import t
from utils.auth import get_lang, get_token, get_user, navigate_to
from utils.theme import get_palette, health_color, ACCENT
from utils.icons import icon_cattle, icon_users, icon_farm, icon_bell
from services.api_client import (
    api_get_cattle_list, api_get_all_latest, api_get_users,
    api_get_recent_alerts, api_get_recent_health_events,
)
from components.navbar import render_navbar
from components.live_panel import render_live_panel, classify
from components.glass import inject_glass_css, tokens, stat_card, section_header, dot, row


def render():
    lang = get_lang()
    token = get_token()
    user = get_user()
    my_farms = user.get("farm_ids", [])
    p = get_palette()

    render_navbar()
    inject_glass_css()
    g = tokens()

    st.markdown(
        f"""<div style="font-size:1.45rem; font-weight:700; color:{g['text']};
            letter-spacing:-.02em; margin:.2rem 0 1rem;">
            {t('welcome', lang)}, <span style="color:{ACCENT['primary']};">
            Dr. {_esc(user.get('full_name', 'Admin'))}</span></div>""",
        unsafe_allow_html=True,
    )

    all_cattle = api_get_cattle_list(token) or []
    latest_data = api_get_all_latest(token) or []
    all_users = api_get_users(token) or []
    recent_alerts = api_get_recent_alerts(token, limit=20) or []

    my_cattle = [c for c in all_cattle if c.get("farm_id") in my_farms]
    my_users = [u for u in all_users if u.get("role") == "user" and
                any(f in my_farms for f in u.get("farm_ids", []))]
    latest_by_cid = {item["cid"]: item for item in (latest_data or [])}

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(stat_card(icon_cattle("#FFFFFF", 19), t("total_cattle", lang),
                              str(len(my_cattle)), ACCENT["green"]), unsafe_allow_html=True)
    with c2:
        st.markdown(stat_card(icon_users("#FFFFFF", 19), t("total_users", lang),
                              str(len(my_users)), ACCENT["primary"]), unsafe_allow_html=True)
    with c3:
        st.markdown(stat_card(icon_farm("#FFFFFF", 19), t("assigned_farms", lang),
                              str(len(my_farms)), ACCENT["purple"]), unsafe_allow_html=True)
    with c4:
        st.markdown(stat_card(icon_bell("#FFFFFF", 19), t("active_alerts", lang),
                              str(len(recent_alerts)),
                              ACCENT["red"] if recent_alerts else ACCENT["green"]),
                    unsafe_allow_html=True)

    st.markdown("---")

    render_live_panel(token, my_cattle, lang, key="admin")

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown(section_header(icon_cattle("#FFFFFF", 16), t("total_cattle", lang),
                                   ACCENT["green"]), unsafe_allow_html=True)
        if my_cattle:
            table = []
            for c in my_cattle:
                cid = c["cid"]
                sensor = latest_by_cid.get(cid, {})
                temp = sensor.get("temperature", 0) if sensor else 0
                bpm = sensor.get("heart", {}).get("bpm", 0) if sensor else 0

                farm = c.get("farm_id", "")
                owners = [u for u in my_users if farm in u.get("farm_ids", [])]
                owner_name = owners[0].get("full_name", "") if owners else "Unassigned"

                table.append({
                    "CID": cid,
                    t("cattle_name", lang): c.get("name", ""),
                    t("owned_by", lang): owner_name,
                    f"{t('temperature', lang)} (°C)": f"{temp:.1f}" if temp > 0 else "—",
                    t("bpm", lang): f"{bpm:.0f}" if bpm > 0 else "—",
                    t("status", lang): t(classify(temp, bpm), lang),
                })

            st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)

            selected = st.selectbox(
                f"{t('view_details', lang)}",
                options=[c["cid"] for c in my_cattle],
                format_func=lambda x: f"CID {x} — {next((c['name'] for c in my_cattle if c['cid'] == x), '')}",
            )
            if st.button(f"{t('view_details', lang)}", key="admin_view"):
                navigate_to("cattle_detail", selected_cattle_cid=selected)
                st.rerun()
        else:
            st.info(t("no_data", lang))

    with col_right:
        st.markdown(section_header(icon_bell("#FFFFFF", 16), t("recent_alerts", lang),
                                   ACCENT["red"]), unsafe_allow_html=True)
        if recent_alerts:
            for alert in recent_alerts[:8]:
                level = alert.get("status", "warning")
                color = health_color(level, p)
                cid = alert.get("cid", "?")

                cattle = next((c for c in my_cattle if c["cid"] == cid), None)
                owner = ""
                if cattle:
                    farm = cattle.get("farm_id", "")
                    owners = [u for u in my_users if farm in u.get("farm_ids", [])]
                    owner = owners[0].get("full_name", "") if owners else ""

                st.markdown(
                    row(
                        f"""{dot(color)}<strong>CID {cid}</strong> — {_esc(level.upper())}
                        {f'<br><span style="color:{g["text_dim"]};">{_esc(owner)}</span>' if owner else ''}
                        <br><span style="color:{g['text_dim']}; font-size:.74rem;">
                            {str(alert.get('timestamp', ''))[:19]}</span>""",
                        color,
                    ),
                    unsafe_allow_html=True,
                )
        else:
            st.success(t("no_data", lang))

        st.markdown("---")
        st.markdown(section_header(icon_users("#FFFFFF", 16), t("total_users", lang),
                                   ACCENT["primary"]), unsafe_allow_html=True)
        if my_users:
            for u in my_users:
                color = ACCENT["green"] if u.get("is_active") else ACCENT["red"]
                st.markdown(
                    row(
                        f"""{dot(color)}<strong>{_esc(u.get('full_name', ''))}</strong>
                        <span style="color:{g['text_dim']};"> — {_esc(u.get('email', ''))}</span>""",
                        color,
                    ),
                    unsafe_allow_html=True,
                )
        else:
            st.info(t("no_data", lang))
