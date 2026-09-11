"""
Super Admin dashboard - full system overview with Admin > User > Cattle mapping.
"""

import streamlit as st
import pandas as pd
from html import escape as _esc
from utils.translations import t
from utils.auth import get_lang, get_token, get_user, navigate_to
from utils.theme import get_palette, health_color, ACCENT
from utils.icons import (
    icon_shield, icon_users, icon_cattle, icon_bell, icon_map, icon_user,
)
from services.api_client import (
    api_get_cattle_list, api_get_all_latest, api_get_users,
    api_get_recent_alerts,
)
from components.navbar import render_navbar
from components.live_panel import render_live_panel
from components.glass import inject_glass_css, tokens, stat_card, section_header, dot, row


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
            {t('system_overview', lang)} — <span style="color:{ACCENT['primary']};">
            {_esc(user.get('full_name', 'Admin'))}</span></div>""",
        unsafe_allow_html=True,
    )

    cattle_list = api_get_cattle_list(token) or []
    users = api_get_users(token) or []
    latest_data = api_get_all_latest(token) or []
    recent_alerts = api_get_recent_alerts(token, limit=20) or []

    admins = [u for u in users if u.get("role") in ("admin", "super_admin")]
    farmers = [u for u in users if u.get("role") == "user"]

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(stat_card(icon_shield("#FFFFFF", 19), t("total_admins", lang),
                              str(len(admins)), ACCENT["yellow"]), unsafe_allow_html=True)
    with c2:
        st.markdown(stat_card(icon_users("#FFFFFF", 19), t("total_users", lang),
                              str(len(farmers)), ACCENT["purple"]), unsafe_allow_html=True)
    with c3:
        st.markdown(stat_card(icon_cattle("#FFFFFF", 19), t("total_cattle", lang),
                              str(len(cattle_list)), ACCENT["green"]), unsafe_allow_html=True)
    with c4:
        st.markdown(stat_card(icon_bell("#FFFFFF", 19), t("active_alerts", lang),
                              str(len(recent_alerts)),
                              ACCENT["red"] if recent_alerts else ACCENT["green"]),
                    unsafe_allow_html=True)

    st.markdown("---")

    render_live_panel(token, cattle_list, lang, key="super")

    st.markdown(section_header(icon_map("#FFFFFF", 16),
                               f"{t('mapping_view', lang)}: Admin › User › Cattle",
                               ACCENT["teal"]), unsafe_allow_html=True)

    farm_to_admin = {}
    for a in admins:
        for farm in a.get("farm_ids", []):
            farm_to_admin.setdefault(farm, []).append(a)

    farm_to_users = {}
    for u in farmers:
        for farm in u.get("farm_ids", []):
            farm_to_users.setdefault(farm, []).append(u)

    farm_to_cattle = {}
    for c in cattle_list:
        farm = c.get("farm_id", "unassigned")
        farm_to_cattle.setdefault(farm, []).append(c)

    all_farms = sorted(set(list(farm_to_admin.keys()) + list(farm_to_users.keys()) + list(farm_to_cattle.keys())))

    if not all_farms:
        st.info(t("no_data", lang))
    else:
        for farm in all_farms:
            farm_admins = farm_to_admin.get(farm, [])
            farm_users = farm_to_users.get(farm, [])
            farm_cattle = farm_to_cattle.get(farm, [])

            with st.expander(f"**{farm}** — {len(farm_admins)} admin(s), {len(farm_users)} user(s), {len(farm_cattle)} cattle", expanded=True):
                col_a, col_u, col_c = st.columns(3)

                with col_a:
                    st.markdown(section_header(icon_shield("#FFFFFF", 14), t("admin", lang),
                                               ACCENT["yellow"]), unsafe_allow_html=True)
                    for a in farm_admins:
                        color = ACCENT["green"] if a.get("is_active") else ACCENT["red"]
                        st.markdown(
                            f"{dot(color)}{_esc(a.get('full_name', a.get('username', '')))}",
                            unsafe_allow_html=True)

                with col_u:
                    st.markdown(section_header(icon_user("#FFFFFF", 14), t("user", lang),
                                               ACCENT["purple"]), unsafe_allow_html=True)
                    for u in farm_users:
                        color = ACCENT["green"] if u.get("is_active") else ACCENT["red"]
                        st.markdown(
                            f"{dot(color)}{_esc(u.get('full_name', u.get('username', '')))}",
                            unsafe_allow_html=True)

                with col_c:
                    st.markdown(section_header(icon_cattle("#FFFFFF", 14), t("total_cattle", lang),
                                               ACCENT["green"]), unsafe_allow_html=True)
                    for c in farm_cattle:
                        st.markdown(f"CID {c['cid']}: {_esc(c.get('name', ''))}",
                                    unsafe_allow_html=True)

    st.markdown("---")

    col_left, col_right = st.columns([3, 2])

    with col_left:
        st.markdown(section_header(icon_users("#FFFFFF", 16), t("total_users", lang),
                                   ACCENT["purple"]), unsafe_allow_html=True)
        if users:
            table = []
            for u in users:
                u_role = u.get("role", "user")
                if u_role == "super_admin" or (u_role == "admin" and not u.get("farm_ids")):
                    role_label = t("super_admin", lang)
                elif u_role == "admin":
                    role_label = t("admin", lang)
                else:
                    role_label = t("user", lang)
                table.append({
                    t("username", lang): u.get("username", ""),
                    t("full_name", lang): u.get("full_name", ""),
                    t("role", lang): role_label,
                    t("assigned_farms", lang): ", ".join(u.get("farm_ids", [])) or "All",
                    t("status", lang): t("active" if u.get("is_active") else "inactive", lang),
                })
            st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)

    with col_right:
        st.markdown(section_header(icon_bell("#FFFFFF", 16), t("recent_alerts", lang),
                                   ACCENT["red"]), unsafe_allow_html=True)
        if recent_alerts:
            for alert in recent_alerts[:8]:
                level = alert.get("status", "warning")
                color = health_color(level, p)
                st.markdown(
                    row(
                        f"""{dot(color)}<strong>CID {alert.get('cid', '?')}</strong> —
                        {_esc(level.upper())}
                        <br><span style="color:{g['text_dim']}; font-size:.74rem;">
                            {str(alert.get('timestamp', ''))[:19]}</span>""",
                        color,
                    ),
                    unsafe_allow_html=True,
                )
        else:
            st.success(t("no_data", lang))

    st.markdown("---")
    st.markdown(section_header(icon_cattle("#FFFFFF", 16), t("total_cattle", lang),
                               ACCENT["green"]), unsafe_allow_html=True)
    if cattle_list:
        latest_by_cid = {item["cid"]: item for item in (latest_data or [])}
        table = []
        for c in cattle_list:
            cid = c["cid"]
            sensor = latest_by_cid.get(cid, {})
            temp = sensor.get("temperature", 0) if sensor else 0
            bpm = sensor.get("heart", {}).get("bpm", 0) if sensor else 0

            farm = c.get("farm_id", "")
            owners = [u.get("full_name", u.get("username", "")) for u in farmers if farm in u.get("farm_ids", [])]

            table.append({
                "CID": cid,
                t("cattle_name", lang): c.get("name", ""),
                t("farm_id", lang): farm,
                t("owned_by", lang): ", ".join(owners) or "Unassigned",
                f"{t('temperature', lang)} (°C)": f"{temp:.1f}" if temp > 0 else "—",
                t("bpm", lang): f"{bpm:.0f}" if bpm > 0 else "—",
            })
        st.dataframe(pd.DataFrame(table), use_container_width=True, hide_index=True)

        # Cattle detail drill-down
        cid_options = [c["cid"] for c in cattle_list]
        col_sel, col_btn = st.columns([3, 1])
        with col_sel:
            selected_cid = st.selectbox(
                t("select_cattle", lang),
                options=cid_options,
                format_func=lambda x: f"CID {x} — {next((c['name'] for c in cattle_list if c['cid'] == x), '')}",
            )
        with col_btn:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button(t("view_details", lang), type="primary", use_container_width=True):
                navigate_to("cattle_detail", selected_cattle_cid=selected_cid)
                st.rerun()
