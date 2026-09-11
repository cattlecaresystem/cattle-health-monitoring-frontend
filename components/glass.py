"""
Glassmorphic UI primitives shared by the dashboard views.

Colors for the dimensional (3D) icon tiles and status dots are derived in Python
rather than with CSS color-mix so the gradients render identically everywhere.
"""

import streamlit as st
from utils.auth import get_theme


def _hex_to_rgb(value: str) -> tuple:
    value = value.lstrip("#")
    return tuple(int(value[i:i + 2], 16) for i in (0, 2, 4))


def _shade(color: str, amount: float) -> str:
    """Blend toward white (amount > 0) or black (amount < 0). amount in -1..1."""
    r, g, b = _hex_to_rgb(color)
    target = 255 if amount > 0 else 0
    k = abs(amount)
    return "#%02X%02X%02X" % tuple(round(c + (target - c) * k) for c in (r, g, b))


def rgba(color: str, alpha: float) -> str:
    r, g, b = _hex_to_rgb(color)
    return f"rgba({r},{g},{b},{alpha})"


def tokens() -> dict:
    """Theme-aware glass surface tokens."""
    if get_theme() == "dark":
        return {
            "glass": "rgba(22,27,34,0.55)",
            "glass_strong": "rgba(30,36,45,0.74)",
            "border": "rgba(255,255,255,0.10)",
            "border_strong": "rgba(255,255,255,0.18)",
            "shadow": "0 10px 34px rgba(0,0,0,0.42)",
            "inner": "inset 0 1px 0 rgba(255,255,255,0.07)",
            "text": "#E6EDF3",
            "text_dim": "#9BA6B2",
            "ambient": (
                "radial-gradient(920px 520px at 10% -12%, rgba(47,129,247,0.22), transparent 62%),"
                "radial-gradient(780px 460px at 90% -4%, rgba(163,113,247,0.18), transparent 62%),"
                "radial-gradient(720px 520px at 52% 112%, rgba(45,164,78,0.14), transparent 62%)"
            ),
        }
    return {
        "glass": "rgba(255,255,255,0.62)",
        "glass_strong": "rgba(255,255,255,0.82)",
        "border": "rgba(255,255,255,0.70)",
        "border_strong": "rgba(255,255,255,0.90)",
        "shadow": "0 10px 30px rgba(31,35,40,0.10)",
        "inner": "inset 0 1px 0 rgba(255,255,255,0.85)",
        "text": "#1F2328",
        "text_dim": "#57606A",
        "ambient": (
            "radial-gradient(900px 500px at 8% -12%, rgba(9,105,218,0.14), transparent 60%),"
            "radial-gradient(760px 440px at 92% -6%, rgba(130,80,223,0.12), transparent 60%),"
            "radial-gradient(720px 500px at 50% 112%, rgba(26,127,55,0.10), transparent 60%)"
        ),
    }


def inject_glass_css() -> None:
    """Ambient backdrop plus the glass surface, 3D tile and status dot styles."""
    g = tokens()
    st.markdown(
        f"""<style>
        .stApp {{ background-image: {g['ambient']} !important;
                  background-attachment: fixed !important; }}

        .cc-glass {{
            background: {g['glass']};
            backdrop-filter: blur(18px) saturate(150%);
            -webkit-backdrop-filter: blur(18px) saturate(150%);
            border: 1px solid {g['border']};
            border-radius: 16px;
            box-shadow: {g['shadow']}, {g['inner']};
        }}
        .cc-glass-strong {{ background: {g['glass_strong']}; }}

        .cc-stat {{
            display: flex; align-items: center; gap: .8rem;
            padding: .95rem 1.05rem; min-height: 84px;
            transition: transform .18s ease, box-shadow .18s ease, border-color .18s ease;
        }}
        .cc-stat:hover {{
            transform: translateY(-3px);
            border-color: {g['border_strong']};
        }}
        .cc-stat-value {{ font-size: 1.55rem; font-weight: 700; line-height: 1.15;
                          letter-spacing: -.02em; }}
        .cc-stat-label {{ font-size: .74rem; color: {g['text_dim']}; font-weight: 600;
                          letter-spacing: .06em; text-transform: uppercase; margin-top: 2px; }}

        .cc-tile {{
            width: 40px; height: 40px; border-radius: 12px; flex: none;
            display: flex; align-items: center; justify-content: center; color: #fff;
        }}
        .cc-tile svg {{ margin: 0 !important; vertical-align: middle !important; }}

        .cc-dot {{
            display: inline-block; width: 10px; height: 10px; border-radius: 50%;
            vertical-align: middle; margin-right: 6px;
        }}

        .cc-live-ring {{
            display: inline-flex; align-items: center; justify-content: center;
            width: 10px; height: 10px; border-radius: 50%; background: #E5534B;
            margin-right: 8px; animation: cc-pulse 1.5s ease-in-out infinite;
        }}
        @keyframes cc-pulse {{
            0%   {{ box-shadow: 0 0 0 0 rgba(229,83,75,.55); }}
            70%  {{ box-shadow: 0 0 0 8px rgba(229,83,75,0); }}
            100% {{ box-shadow: 0 0 0 0 rgba(229,83,75,0); }}
        }}

        .cc-section {{
            display: flex; align-items: center; gap: .6rem;
            font-size: 1.08rem; font-weight: 700; color: {g['text']};
            letter-spacing: -.01em; margin: .2rem 0 .8rem;
        }}

        .cc-chip {{
            display: inline-flex; align-items: center; padding: 3px 10px;
            border-radius: 999px; font-size: .74rem; font-weight: 700;
            margin-right: 6px; backdrop-filter: blur(6px);
        }}

        .cc-row {{
            padding: .6rem .8rem; margin: .3rem 0; border-radius: 12px;
            font-size: .86rem; color: {g['text']};
            background: {g['glass']};
            backdrop-filter: blur(12px) saturate(140%);
            -webkit-backdrop-filter: blur(12px) saturate(140%);
            border: 1px solid {g['border']};
            border-left-width: 3px;
        }}
        </style>""",
        unsafe_allow_html=True,
    )


def tile(icon_svg: str, color: str, size: int = 40) -> str:
    """A dimensional icon tile: lit from the top, with a colored cast shadow."""
    top, bottom = _shade(color, 0.26), _shade(color, -0.16)
    radius = round(size * 0.3)
    return (
        f'<div class="cc-tile" style="width:{size}px; height:{size}px; border-radius:{radius}px;'
        f'background: linear-gradient(150deg, {top}, {bottom});'
        f'box-shadow: 0 5px 12px {rgba(color, 0.34)},'
        f' inset 0 1px 0 rgba(255,255,255,.45),'
        f' inset 0 -2px 3px rgba(0,0,0,.16);">{icon_svg}</div>'
    )


def dot(color: str, size: int = 10) -> str:
    """A raised status dot, replacing colored emoji circles."""
    return (
        f'<span class="cc-dot" style="width:{size}px; height:{size}px;'
        f'background: radial-gradient(circle at 34% 30%, {_shade(color, 0.55)}, {color} 62%);'
        f'box-shadow: 0 0 0 2px {rgba(color, 0.16)}, 0 1px 3px rgba(0,0,0,.28);"></span>'
    )


def stat_card(icon_svg: str, label: str, value: str, color: str,
              value_is_html: bool = False) -> str:
    """Glass KPI card with a 3D icon tile."""
    body = value if value_is_html else f'<div class="cc-stat-value" style="color:{color};">{value}</div>'
    return f"""
    <div class="cc-glass cc-stat">
        {tile(icon_svg, color)}
        <div style="min-width:0;">
            {body}
            <div class="cc-stat-label">{label}</div>
        </div>
    </div>"""


def section_header(icon_svg: str, title: str, color: str) -> str:
    return f'<div class="cc-section">{tile(icon_svg, color, size=28)}<span>{title}</span></div>'


def row(content: str, accent: str) -> str:
    """Glass list row with a colored left accent — used for alerts and user lists."""
    return f'<div class="cc-row" style="border-left-color:{accent};">{content}</div>'
