import streamlit as st
import requests
from requests.adapters import HTTPAdapter
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time
from requests.auth import HTTPBasicAuth
from karbon_font import KARBON_FACES
from chuk_logo import CHUK_LOGO

st.set_page_config(
    page_title="CHUK Orders",
    page_icon="https://chuk.in/wp-content/uploads/2022/08/cropped-chuk-favicon-new-192x192.png",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Theme: light / dark ───────────────────────────────────────────────────────
# Read chosen mode early so CSS is injected with the right palette. We read the
# radio's *keyed* widget state ("theme_radio"): a keyed widget's value persists in
# session_state and is already updated at the top of the rerun the click triggers,
# so there's no one-rerun lag.
THEME_MODE = "light" if st.session_state.get("theme_radio") == "Light" else "dark"

# CHUK brand palette (from chuk.in Elementor globals):
#   amber #F3B343 · coral #F46C62 · maroon #942A45 · teal #33A8C3
#   green #95CC2E · kraft #CDB096 · cream #FFF2E0
DARK = dict(  # CHUK night — espresso + maroon, flat solids
    app_bg="#221318", sidebar_bg="#1B0F13", logo_bg="#FFF2E0", logo_pad="8px 14px",
    text="#FFF2E0", muted="#CDB096", val="#FFF8EF", lbl="#B79877",
    card_bg="#2E1B22", card_border="#4A2E36", card_hover="#F3B343", card_shadow="none",
    hero_bg="#F3B343", hero_border="#F3B343", hero_shadow="none",
    hero_title="#3A1620", hero_text="#5A2A18", hero_strong="#3A1620",
    tab_bg="#2E1B22", tab_text="#CDB096",
    df_border="#4A2E36", df_shadow="none",
    btn_bg="#F3B343", btn_border="#F3B343", btn_text="#3A1620",
    chart_font="#E8D6BE", chart_title="#FFF2E0", grid="#3A2630", axis="#5A3E48",
    table_bg="#2A1A20", table_text="#FFF2E0",
)
LIGHT = dict(  # CHUK day — beige + kraft, maroon ink, flat solids
    app_bg="#F5ECD9", sidebar_bg="#EFE4CC", logo_bg="transparent", logo_pad="0",
    text="#942A45", muted="#8A5A45", val="#6E1F33", lbl="#A07A5C",
    card_bg="#FFFFFF", card_border="#EADFCB", card_hover="#F46C62", card_shadow="none",
    hero_bg="#942A45", hero_border="#942A45", hero_shadow="none",
    hero_title="#FFF2E0", hero_text="#F2DABB", hero_strong="#FFFFFF",
    tab_bg="#F2DABB", tab_text="#8A5A45",
    df_border="#EADFCB", df_shadow="none",
    btn_bg="#F3B343", btn_border="#F3B343", btn_text="#3A1620",
    chart_font="#7A3A4A", chart_title="#942A45", grid="#EADFCB", axis="#CBB89E",
    table_bg="#FFFFFF", table_text="#5A1A2C",
)
P = LIGHT if THEME_MODE == "light" else DARK

def build_css(p):
    return f"""
<style>
/* CHUK brand typeface — Karbon, embedded base64 (see karbon_font.py) */
{KARBON_FACES}

.stApp, [data-testid="stAppViewContainer"], [data-testid="stMain"],
section.main, .main .block-container {{ background: {p['app_bg']} !important; }}
[data-testid="stHeader"] {{ background: {p['app_bg']} !important; }}
[data-testid="stSidebar"], [data-testid="stSidebar"] > div {{ background: {p['sidebar_bg']} !important; }}

html, body, [class*="css"], .stMarkdown, p, span, label, div,
h1, h2, h3, h4, h5, h6, button, input, .stButton, .stDownloadButton {{
    font-family: 'Karbon', 'Montserrat', -apple-system, sans-serif !important;
    color: {p['text']};
}}
/* keep Material icon fonts intact (else ligatures show as raw text, e.g. the sidebar arrow) */
[data-testid="stIconMaterial"], .material-icons, .material-icons-outlined,
.material-symbols-rounded, .material-symbols-outlined, span[class*="material-"] {{
    font-family: 'Material Symbols Rounded','Material Symbols Outlined','Material Icons' !important;
}}
/* ---- widgets follow theme (Streamlit base is static light, so force these) ---- */
/* selectbox / text input control */
[data-baseweb="select"] > div, [data-baseweb="input"], [data-baseweb="input"] input,
[data-testid="stTextInput"] input, [data-testid="stNumberInput"] input {{
    background: {p['card_bg']} !important; color: {p['text']} !important;
    border-color: {p['card_border']} !important;
}}
[data-baseweb="select"] div, [data-baseweb="select"] span,
[data-baseweb="select"] input {{ color: {p['text']} !important; }}
[data-baseweb="select"] svg {{ fill: {p['text']} !important; color: {p['text']} !important; }}
input::placeholder {{ color: {p['lbl']} !important; opacity: 1; }}

/* dropdown menu (rendered in a portal at body level) */
[data-baseweb="popover"] [role="listbox"], ul[data-baseweb="menu"],
[data-baseweb="menu"] {{
    background: {p['card_bg']} !important; border: 1px solid {p['card_border']} !important;
}}
li[role="option"], [data-baseweb="menu"] li {{
    background: {p['card_bg']} !important; color: {p['text']} !important;
}}
li[role="option"]:hover, li[aria-selected="true"][role="option"] {{
    background: {p['tab_bg']} !important; color: {p['text']} !important;
}}

/* widget labels + radio/checkbox text */
[data-testid="stWidgetLabel"], [data-testid="stWidgetLabel"] *,
.stRadio label, .stCheckbox label, .stRadio div, .stCheckbox div {{
    color: {p['text']} !important;
}}

.block-container {{ padding: 3rem 1.2rem 3rem !important; max-width: 1240px; }}

.chuk-hero {{
    display: flex; flex-direction: column; align-items: flex-start;
    padding: .4rem 0 1rem; margin-bottom: .6rem;
    border-bottom: 1px solid {p['card_border']};
}}
.chuk-hero .chuk-logo {{
    height: 52px; width: auto; max-width: 100%; box-sizing: content-box;
    display: block; object-fit: contain; margin-bottom: .6rem;
    background: {p['logo_bg']}; padding: {p['logo_pad']}; border-radius: 10px;
}}
.chuk-hero .chuk-hero-meta {{
    font-size: 1.1rem; font-weight: 700; color: {p['text']} !important;
}}
.chuk-hero p {{ margin: .1rem 0 0; font-size: .9rem; color: {p['muted']} !important; }}
.chuk-hero p b {{ color: {p['val']} !important; }}

.kpi {{
    background: {p['card_bg']};
    border: 1px solid {p['card_border']};
    border-radius: 15px; padding: 1.1rem 1.2rem; text-align: left; height: 100%;
}}
.kpi-lbl   {{ font-size: .8rem; font-weight: 500; color: {p['lbl']}; }}
.kpi-val   {{ font-size: 1.9rem; font-weight: 700; color: {p['val']}; line-height: 1.2; margin-top: .15rem; }}

.sec-h {{
    font-size: 1.3rem; font-weight: 700; color: {p['text']};
    margin: 1.2rem 0 .7rem;
}}

[data-testid="stDataFrame"] {{
    border: 1px solid {p['df_border']} !important;
    border-radius: 15px; overflow: hidden;
}}

.stTabs [data-baseweb="tab-list"] {{ gap: 6px; }}
.stTabs [data-baseweb="tab"] {{
    border-radius: 30px; padding: 6px 20px; font-weight: 600;
    background: {p['tab_bg']};
}}
.stTabs [data-baseweb="tab"] p {{ color: {p['tab_text']} !important; font-weight: 600; }}
.stTabs [aria-selected="true"] {{ background: #942A45 !important; }}
.stTabs [aria-selected="true"] p {{ color: #FFFFFF !important; }}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"] {{ background: transparent !important; }}

.stButton button, .stDownloadButton button {{
    border: none !important; border-radius: 30px !important; padding: .4rem 1.4rem !important;
    font-weight: 700 !important; background: {p['btn_bg']} !important; color: {p['btn_text']} !important;
}}
.stButton button:hover, .stDownloadButton button:hover {{ background: #942A45 !important; color: #fff !important; }}

/* plum splash while loading */
.splash {{
    position: fixed; inset: 0; z-index: 99999;
    background: #942A45;
    display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 1.6rem;
}}
.splash-logo {{
    height: 60px; width: auto; box-sizing: content-box;
    background: #FFF2E0; padding: 16px 24px; border-radius: 16px;
    animation: splashpulse 1.4s ease-in-out infinite;
}}
.splash-ring {{
    width: 34px; height: 34px; border-radius: 50%;
    border: 3px solid rgba(255,255,255,0.25); border-top-color: #F3B343;
    animation: splashspin .8s linear infinite;
}}
@keyframes splashpulse {{ 0%,100% {{ opacity: 1; }} 50% {{ opacity: .45; }} }}
@keyframes splashspin {{ to {{ transform: rotate(360deg); }} }}

@media (max-width: 768px) {{
    [data-testid="column"] {{ width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important; }}
    .chuk-hero .chuk-logo {{ height: 36px; }}
    .kpi-val {{ font-size: 1.45rem; }}
    [data-testid="stSidebarNav"] {{ display: none; }}
}}

.status-pending    {{ color: #F3B343; font-weight: 600; }}
.status-processing {{ color: #33A8C3; font-weight: 600; }}
.status-completed  {{ color: #6FA52A; font-weight: 600; }}
.status-cancelled  {{ color: #F46C62; font-weight: 600; }}
.status-on-hold    {{ color: #CDB096; font-weight: 600; }}
.status-refunded   {{ color: #E08A3C; font-weight: 600; }}
.status-failed     {{ color: #942A45; font-weight: 600; }}
</style>
"""

st.markdown(build_css(P), unsafe_allow_html=True)

# ── Password gate ─────────────────────────────────────────────────────────────
# Lets the Streamlit app be PUBLIC (so keep-awake pings reach /_stcore/health)
# while still protecting the order PII behind a password. Set app_password in
# secrets; if unset, the gate is skipped (no lockout).
def check_password():
    if st.session_state.get("auth_ok"):
        return
    pw = st.secrets["app_password"] if "app_password" in st.secrets else None
    if not pw:
        return  # no password configured → open
    st.markdown(
        f'<div style="max-width:340px;margin:12vh auto 1rem;text-align:center">'
        f'<img src="{CHUK_LOGO}" style="height:54px;margin-bottom:1rem"/>'
        f'<div style="font-weight:700;color:{P["text"]}">Orders Dashboard</div></div>',
        unsafe_allow_html=True,
    )
    c = st.columns([1, 2, 1])[1]
    entered = c.text_input("Password", type="password", label_visibility="collapsed",
                           placeholder="Enter password")
    if entered:
        if entered == pw:
            st.session_state["auth_ok"] = True
            st.rerun()
        else:
            c.error("Wrong password.")
    st.stop()

check_password()

# Theme-aware styling for every Plotly figure
def sketchify(fig):
    fig.update_layout(
        font=dict(family="Karbon, Montserrat, sans-serif", size=13, color=P["chart_font"]),
        title_font=dict(family="Karbon, Montserrat, sans-serif", size=15, color=P["chart_title"]),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(color=P["muted"])),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor=P["axis"])
    fig.update_yaxes(showgrid=True, gridcolor=P["grid"], zeroline=False)
    return fig

# ── Auth ──────────────────────────────────────────────────────────────────────
WC_BASE = "https://chuk.in/wp-json/wc/v3"
AUTH = HTTPBasicAuth(
    st.secrets["woocommerce"]["user"],
    st.secrets["woocommerce"]["app_key"],
)

def make_session():
    s = requests.Session()
    s.mount("https://", HTTPAdapter(max_retries=0))
    return s

SESSION = make_session()
TIMEOUT = (10, 45)

def set_order_status(wc_id: int, status: str) -> bool:
    """PUT a new status to a WooCommerce order. Returns True on success."""
    try:
        r = SESSION.put(f"{WC_BASE}/orders/{wc_id}", json={"status": status},
                        auth=AUTH, timeout=TIMEOUT)
        return r.status_code == 200
    except requests.exceptions.RequestException:
        return False

WC_FIELDS = ",".join([
    "id","number","status","date_created",
    "billing","line_items",
    "total","total_tax","shipping_total",
    "payment_method_title",
])

STATE_MAP = {
    "AP":"Andhra Pradesh","AR":"Arunachal Pradesh","AS":"Assam","BR":"Bihar",
    "CT":"Chhattisgarh","GA":"Goa","GJ":"Gujarat","HR":"Haryana","HP":"Himachal Pradesh",
    "JH":"Jharkhand","KA":"Karnataka","KL":"Kerala","MP":"Madhya Pradesh","MH":"Maharashtra",
    "MN":"Manipur","ML":"Meghalaya","MZ":"Mizoram","NL":"Nagaland","OD":"Odisha",
    "PB":"Punjab","RJ":"Rajasthan","SK":"Sikkim","TN":"Tamil Nadu","TS":"Telangana",
    "TR":"Tripura","UP":"Uttar Pradesh","UK":"Uttarakhand","WB":"West Bengal",
    "AN":"Andaman & Nicobar","CH":"Chandigarh","DN":"Dadra & Nagar Haveli","DD":"Daman & Diu",
    "DL":"Delhi","JK":"Jammu & Kashmir","LA":"Ladakh","LD":"Lakshadweep","PY":"Puducherry",
}

# CHUK brand status colors
STATUS_COLOR = {
    "pending":    "#F3B343",  # amber
    "processing": "#33A8C3",  # teal
    "on-hold":    "#CDB096",  # kraft
    "completed":  "#6FA52A",  # green
    "cancelled":  "#F46C62",  # coral
    "refunded":   "#E08A3C",  # burnt amber
    "failed":     "#942A45",  # maroon
}

# Status grouping: Processing vs Failed/Cancelled vs Completed
PROCESSING_STATUSES = {"pending", "processing", "on-hold"}
FAILED_STATUSES     = {"cancelled", "failed", "refunded"}

GROUP_COLOR = {
    "Processing":       "#F3B343",  # amber
    "Completed":        "#6FA52A",  # green
    "Failed/Cancelled": "#F46C62",  # coral
    "Other":            "#CDB096",  # kraft
}

def status_group(s: str) -> str:
    if s in PROCESSING_STATUSES:
        return "Processing"
    if s in FAILED_STATUSES:
        return "Failed/Cancelled"
    if s == "completed":
        return "Completed"
    return "Other"

TEST_MIN_TOTAL = 100.0  # orders below this (₹) treated as test orders

# ── Data fetch ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def fetch_orders(days_back: int) -> pd.DataFrame:
    # Always fetch ALL statuses (one cache per date range); status is filtered
    # client-side. Avoids per-status caches drifting out of sync.
    after = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")
    # _cb busts chuk.in's LiteSpeed server-side cache (it caches REST responses per
    # URL, otherwise brand-new/updated orders don't appear).
    params = {"per_page": 50, "orderby": "date", "order": "desc",
              "after": after, "_fields": WC_FIELDS, "_cb": int(time.time())}

    all_orders, page = [], 1
    while page <= 20:
        params["page"] = page
        try:
            r = SESSION.get(f"{WC_BASE}/orders", params=params, auth=AUTH, timeout=TIMEOUT,
                            headers={"Cache-Control": "no-cache"})
        except requests.exceptions.Timeout:
            st.warning(f"Timeout on page {page} — showing {len(all_orders)} orders.")
            break
        except requests.exceptions.RequestException as e:
            st.error(f"API error: {e}")
            break
        if r.status_code != 200:
            st.error(f"WC API {r.status_code}")
            break
        batch = r.json()
        if not batch:
            break
        all_orders.extend(batch)
        total_pages = int(r.headers.get("X-WP-TotalPages", 1))
        if page >= total_pages or len(batch) < 50:
            break
        page += 1

    if not all_orders:
        return pd.DataFrame()

    rows = []
    for o in all_orders:
        items = o.get("line_items", [])
        is_sample = all("sample kit" in i["name"].lower() for i in items) if items else False
        product_names = "; ".join(f"{i['name']} ×{i['quantity']}" for i in items)
        state_code = o["billing"].get("state", "")
        customer = f"{o['billing'].get('first_name','')} {o['billing'].get('last_name','')}".strip()
        email = o["billing"].get("email", "")
        total = float(o.get("total", 0) or 0)
        # Test order detection: low value OR 'test' in customer/email/products
        blob = f"{customer} {email} {product_names}".lower()
        is_test = (total < TEST_MIN_TOTAL) or ("test" in blob)
        rows.append({
            "Order":     "#" + str(o["number"]),
            "Date":      pd.to_datetime(o["date_created"]),
            "Status":    o["status"],
            "StatusGrp": status_group(o["status"]),
            "Type":      "Sample Kit" if is_sample else "Website Order",
            "IsTest":    is_test,
            "Customer":  customer,
            "Email":     email,
            "Phone":     o["billing"].get("phone", ""),
            "City":      o["billing"].get("city", "").title(),
            "State":     STATE_MAP.get(state_code, state_code),
            "StateCode": state_code,
            "Products":  product_names,
            "Total":     total,
            "Payment":   o.get("payment_method_title", ""),
            "WC_ID":     o["id"],
            "Day":       None,
        })

    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    df["Day"]  = df["Date"].dt.date
    return df


def kpi_card(col, emoji, value, label, color):
    # emoji/color kept in signature for compatibility; intentionally unused (uniform cards)
    col.markdown(
        f'<div class="kpi">'
        f'<div class="kpi-lbl">{label}</div>'
        f'<div class="kpi-val">{value}</div></div>',
        unsafe_allow_html=True,
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### Appearance")
    st.radio("Theme", ["Dark", "Light"], key="theme_radio",
             horizontal=True, label_visibility="collapsed")
    st.markdown("---")
    st.markdown("### Filters")
    days_back     = st.selectbox("Date range", [7, 14, 30, 60, 90, 180, 365], index=2,
                                  format_func=lambda x: f"Last {x} days")
    st.markdown("---")
    hide_tests = st.toggle("Hide test orders (<₹100 / “test”)", value=True)
    auto_refresh  = st.toggle("Auto-refresh (3 min)", value=False)
    if st.button("Refresh now"):
        st.cache_data.clear()
        st.rerun()
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()
    st.caption(f"Updated: {datetime.fromtimestamp(st.session_state.last_refresh).strftime('%H:%M:%S')}")

# ── Splash screen (plum, CHUK logo) while loading ─────────────────────────────
splash = st.empty()
splash.markdown(
    f'<div class="splash"><img class="splash-logo" src="{CHUK_LOGO}" alt="CHUK"/>'
    f'<div class="splash-ring"></div></div>',
    unsafe_allow_html=True,
)

# ── Load ──────────────────────────────────────────────────────────────────────
df_raw = fetch_orders(days_back)

if df_raw.empty:
    splash.empty()
    st.warning("No orders found.")
    st.stop()

test_n = int(df_raw["IsTest"].sum())
df = df_raw[~df_raw["IsTest"]].copy() if hide_tests else df_raw.copy()
# Revenue excludes failed / cancelled / refunded orders
df_rev = df[~df["Status"].isin(FAILED_STATUSES)]
splash.empty()

# ── Hero header ───────────────────────────────────────────────────────────────
hidden_note = f" · {test_n} test hidden" if hide_tests and test_n else ""
st.markdown(
    f'<div class="chuk-hero">'
    f'<img class="chuk-logo" src="{CHUK_LOGO}" alt="CHUK"/>'
    f'<div class="chuk-hero-meta">Orders Dashboard</div>'
    f'<p>chuk.in · last {days_back} days · <b>{len(df)} orders</b>{hidden_note}</p></div>',
    unsafe_allow_html=True,
)

if df.empty:
    st.warning("No orders after filters.")
    st.stop()

# ── Overall KPIs ──────────────────────────────────────────────────────────────
total_rev     = df_rev["Total"].sum()   # excludes failed/cancelled/refunded
processing_n  = int(df["StatusGrp"].eq("Processing").sum())
failed_n      = int(df["StatusGrp"].eq("Failed/Cancelled").sum())
website_n     = int(df["Type"].eq("Website Order").sum())
sample_n      = int(df["Type"].eq("Sample Kit").sum())

r1 = st.columns(3)
kpi_card(r1[0], "🧾", len(df),              "Total Orders",   "#F46C62")
kpi_card(r1[1], "💰", f"₹{total_rev:,.0f}", "Revenue (excl. failed)",  "#6FA52A")
kpi_card(r1[2], "🌐", website_n,            "Website Orders", "#F3B343")
st.write("")
r2 = st.columns(3)
kpi_card(r2[0], "🧪", sample_n,        "Sample Kits",      "#33A8C3")
kpi_card(r2[1], "🟡", processing_n,    "Processing",       "#F3B343")
kpi_card(r2[2], "🔴", failed_n,        "Failed/Cancelled", "#942A45")

st.markdown("---")


# ══════════════════════════════════════════════════════════════════════════════
# Reusable order-section renderer (per Type tab)
# ══════════════════════════════════════════════════════════════════════════════
def color_status(val):
    return f"color:{STATUS_COLOR.get(val,'#6B7280')};font-weight:600"

def render_orders(section_df: pd.DataFrame, key: str):
    if section_df.empty:
        st.info("No orders in this group. 🍃")
        return

    # Status-group segmented filter: Processing vs Failed/Cancelled vs Completed
    grp = st.radio(
        "Show", ["All", "Processing", "Completed", "Failed/Cancelled"],
        horizontal=True, key=f"grp_{key}",
    )
    view = section_df if grp == "All" else section_df[section_df["StatusGrp"] == grp]

    # Mini KPI row for this group
    g1, g2, g3 = st.columns(3)
    kpi_card(g1, "🧾", len(view),                          "Orders",  "#F46C62")
    kpi_card(g2, "💰", f"₹{view['Total'].sum():,.0f}",     "Revenue", "#6FA52A")
    avg = view["Total"].mean() if len(view) else 0
    kpi_card(g3, "📊", f"₹{avg:,.0f}",                     "Avg Order", "#F3B343")
    st.write("")

    search = st.text_input("Search order / customer / city / product",
                           placeholder="Type to filter…", key=f"search_{key}")
    cF1, cF2 = st.columns([1, 1])
    with cF1:
        states = ["All"] + sorted(view["State"].dropna().unique().tolist())
        state_sel = st.selectbox("State", states, key=f"state_{key}")
    with cF2:
        show_contact = st.checkbox("Show email & phone", value=False, key=f"contact_{key}")

    disp = view.copy()
    if search:
        mask = (
            disp["Customer"].str.contains(search, case=False, na=False) |
            disp["City"].str.contains(search, case=False, na=False) |
            disp["Products"].str.contains(search, case=False, na=False) |
            disp["Order"].str.contains(search, case=False, na=False)
        )
        disp = disp[mask]
    if state_sel != "All":
        disp = disp[disp["State"] == state_sel]

    disp = disp.copy()
    disp["Date"]  = disp["Date"].dt.strftime("%d %b %y %H:%M")
    disp["Total"] = disp["Total"].apply(lambda x: f"₹{x:,.0f}")

    cols = ["Order", "Date", "Status", "Customer", "City", "State", "Products", "Total", "Payment"]
    if show_contact:
        cols = ["Order", "Date", "Status", "Customer", "Email", "Phone",
                "City", "State", "Products", "Total", "Payment"]

    # Editable "Done" tick: on → status completed, off → processing (writes to WooCommerce)
    ed = disp[cols + ["WC_ID"]].copy()
    ed.insert(0, "Done", disp["Status"].eq("completed").values)
    ed = ed.reset_index(drop=True)

    edited = st.data_editor(
        ed, key=f"editor_{key}", hide_index=True,
        use_container_width=True, height=420,
        disabled=cols,  # only the Done checkbox is editable
        column_config={
            "Done": st.column_config.CheckboxColumn(
                "✓ Done", help="Tick = mark order completed · untick = back to processing"),
            "WC_ID": None,  # hidden
        },
    )

    # Apply any toggles back to the store
    old_done = ed["Done"]
    new_done = edited["Done"]
    changed = new_done[new_done != old_done].index
    if len(changed):
        msgs = []
        for i in changed:
            wc_id = int(ed.loc[i, "WC_ID"])
            order_no = ed.loc[i, "Order"]
            new_status = "completed" if bool(new_done.loc[i]) else "processing"
            if set_order_status(wc_id, new_status):
                msgs.append(f"{order_no} → {new_status}")
            else:
                st.error(f"Failed to update order {order_no}.")
        if msgs:
            # remember across the rerun so the user sees what happened (order may
            # leave the current status filter and disappear from view)
            st.session_state["last_status_change"] = msgs
            st.session_state.pop("editor_web", None)
            st.session_state.pop("editor_sample", None)
            st.cache_data.clear()
            st.rerun()

    st.caption(f"Showing {len(disp)} of {len(view)} orders · tick ✓ Done to complete an order")

    csv = view.drop(columns=["Day", "WC_ID", "StateCode", "IsTest"]).to_csv(index=False).encode("utf-8")
    st.download_button("Download CSV", data=csv,
                       file_name=f"chuk_{key}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                       mime="text/csv", key=f"csv_{key}")


# ══════════════════════════════════════════════════════════════════════════════
# ORDERS — tabs by Type: Website vs Sample Kit
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-h">Orders</div>', unsafe_allow_html=True)
if st.session_state.get("last_status_change"):
    st.success("Status updated: " + " · ".join(st.session_state.pop("last_status_change"))
               + "  (an order may drop out of view if it no longer matches the Status filter)")
tab_web, tab_sample = st.tabs([f"Website Orders ({website_n})",
                               f"Sample Kits ({sample_n})"])
with tab_web:
    render_orders(df[df["Type"] == "Website Order"], "web")
with tab_sample:
    render_orders(df[df["Type"] == "Sample Kit"], "sample")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-h">Analytics</div>', unsafe_allow_html=True)

daily = df.groupby(["Day","StatusGrp"]).size().reset_index(name="Count")
fig_daily = px.bar(daily, x="Day", y="Count", color="StatusGrp",
                   color_discrete_map=GROUP_COLOR, title="Orders per Day",
                   labels={"Day":"","Count":"Orders","StatusGrp":""}, height=280)
fig_daily.update_layout(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, font_size=11),
    margin=dict(l=0,r=0,t=40,b=0),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(sketchify(fig_daily), use_container_width=True)

ca, cb = st.columns(2)
with ca:
    sg = df["StatusGrp"].value_counts().reset_index()
    sg.columns = ["Group","Count"]
    fig_grp = px.pie(sg, names="Group", values="Count", title="Processing vs Failed/Cancelled",
                     height=280, hole=0.45,
                     color="Group", color_discrete_map=GROUP_COLOR)
    fig_grp.update_layout(showlegend=True, legend=dict(orientation="h", font_size=10),
                          margin=dict(l=0,r=0,t=40,b=0), paper_bgcolor="rgba(0,0,0,0)")
    fig_grp.update_traces(textposition="inside", textinfo="percent", textfont_size=11)
    st.plotly_chart(sketchify(fig_grp), use_container_width=True)

with cb:
    td = df_rev.groupby("Type").agg(Orders=("WC_ID","count"), Revenue=("Total","sum")).reset_index()
    fig_type = px.bar(td, x="Type", y="Revenue", color="Type",
                      color_discrete_map={"Sample Kit":"#33A8C3","Website Order":"#F3B343"},
                      title="Revenue by Type (₹, excl. failed)", labels={"Revenue":"₹","Type":""},
                      height=280, text="Orders")
    fig_type.update_traces(texttemplate="%{text} orders", textposition="outside")
    fig_type.update_layout(showlegend=False, margin=dict(l=0,r=0,t=40,b=0),
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(sketchify(fig_type), use_container_width=True)

state_rev = (df_rev.groupby("State")["Total"].sum()
               .sort_values(ascending=False).head(12).reset_index())
fig_state = px.bar(state_rev, x="Total", y="State", orientation="h",
                   title="Top States by Revenue (₹, excl. failed)",
                   labels={"Total":"₹","State":""},
                   height=320)
fig_state.update_traces(marker_color="#F46C62")
fig_state.update_layout(
    margin=dict(l=0,r=0,t=40,b=0),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(autorange="reversed"),
)
st.plotly_chart(sketchify(fig_state), use_container_width=True)

ce, cf = st.columns(2)
with ce:
    city_d = df.groupby("City").size().sort_values(ascending=False).head(10).reset_index()
    city_d.columns = ["City","Orders"]
    fig_city = px.bar(city_d, x="Orders", y="City", orientation="h",
                      title="Top Cities", labels={"Orders":"","City":""},
                      height=300)
    fig_city.update_traces(marker_color="#33A8C3")
    fig_city.update_layout(
        margin=dict(l=0,r=0,t=40,b=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(sketchify(fig_city), use_container_width=True)

with cf:
    pay_d = (df.groupby("Payment").agg(Orders=("WC_ID","count"))
               .sort_values("Orders", ascending=False).reset_index())
    fig_pay = px.bar(pay_d, x="Payment", y="Orders", title="Payment Method",
                     labels={"Payment":"","Orders":""},
                     height=300, text="Orders")
    fig_pay.update_traces(textposition="outside", marker_color="#F3B343")
    fig_pay.update_layout(showlegend=False, margin=dict(l=0,r=0,t=40,b=0),
                           plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(sketchify(fig_pay), use_container_width=True)

# ── Auto-refresh (non-blocking) ───────────────────────────────────────────────
st.session_state.last_refresh = time.time()
if auto_refresh:
    elapsed = time.time() - st.session_state.get("_auto_ts", 0)
    if elapsed > 180:
        st.session_state["_auto_ts"] = time.time()
        st.cache_data.clear()
        time.sleep(0.3)
        st.rerun()
    else:
        st.caption(f"Auto-refresh in {int(180 - elapsed)}s")
