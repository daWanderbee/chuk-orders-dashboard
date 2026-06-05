import streamlit as st
import requests
from requests.adapters import HTTPAdapter
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta
import time
from requests.auth import HTTPBasicAuth

st.set_page_config(
    page_title="CHUK Orders",
    page_icon="🧁",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Modern, polished CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

.stApp {
    background: radial-gradient(1200px 600px at 80% -10%, #1c2541 0%, transparent 60%),
                radial-gradient(900px 500px at -10% 10%, #2a1a3a 0%, transparent 55%),
                #0E1117;
}

html, body, [class*="css"], .stMarkdown, p, span, label, div {
    font-family: 'Inter', -apple-system, sans-serif;
}

.block-container { padding: 1.4rem 1.2rem 3rem !important; max-width: 1240px; }

/* Hero banner — gradient glass */
.chuk-hero {
    background: linear-gradient(120deg, rgba(99,102,241,0.18), rgba(236,72,153,0.16));
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 22px;
    padding: 1.5rem 1.8rem;
    margin-bottom: 1.4rem;
    box-shadow: 0 18px 40px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.06);
    backdrop-filter: blur(8px);
}
.chuk-hero h1 {
    margin: 0; font-size: 1.9rem; font-weight: 800; letter-spacing: -.5px;
    background: linear-gradient(90deg, #fff, #c7d2fe);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
}
.chuk-hero p { margin: .35rem 0 0; font-size: .95rem; color: #A8B0C0; }
.chuk-hero p b { color: #E5E7EB; }

/* Glass KPI cards */
.kpi {
    position: relative;
    background: rgba(255,255,255,0.035);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 18px;
    padding: 1rem 1rem .9rem;
    text-align: left;
    box-shadow: 0 8px 24px rgba(0,0,0,0.28);
    height: 100%;
    overflow: hidden;
    transition: transform .15s ease, border-color .15s ease;
}
.kpi:hover { transform: translateY(-3px); border-color: rgba(255,255,255,0.18); }
.kpi::before {
    content:""; position:absolute; left:0; top:0; bottom:0; width:4px;
    background: var(--accent, #6366F1);
}
.kpi-emoji { font-size: 1.2rem; opacity: .9; }
.kpi-val   { font-size: 1.75rem; font-weight: 800; color: #F3F4F6; line-height: 1.15; letter-spacing:-.5px; }
.kpi-lbl   { font-size: .72rem; font-weight: 600; color: #8A91A3; text-transform: uppercase; letter-spacing: .6px; }

/* Section headers */
.sec-h {
    font-size: 1.15rem; font-weight: 700; color: #E5E7EB;
    margin: .4rem 0 .8rem; display: flex; align-items: center; gap: .5rem;
}

/* Dataframe framing */
[data-testid="stDataFrame"] {
    border: 1px solid rgba(255,255,255,0.08) !important;
    border-radius: 16px; overflow: hidden;
    box-shadow: 0 8px 24px rgba(0,0,0,0.25);
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] { gap: 6px; }
.stTabs [data-baseweb="tab"] {
    border-radius: 12px; padding: 8px 16px; font-weight: 600;
    color: #A8B0C0; background: rgba(255,255,255,0.03);
}
.stTabs [aria-selected="true"] {
    background: linear-gradient(120deg, rgba(99,102,241,0.35), rgba(236,72,153,0.30)) !important;
    color: #fff !important;
}

/* Buttons */
.stButton button, .stDownloadButton button {
    border: 1px solid rgba(255,255,255,0.12) !important;
    border-radius: 12px !important; font-weight: 600 !important;
    background: rgba(255,255,255,0.05) !important; color: #E5E7EB !important;
}
.stButton button:hover, .stDownloadButton button:hover {
    border-color: rgba(99,102,241,0.6) !important;
}

@media (max-width: 768px) {
    [data-testid="column"] {
        width: 100% !important; flex: 1 1 100% !important; min-width: 100% !important;
    }
    .chuk-hero h1 { font-size: 1.45rem; }
    .kpi-val { font-size: 1.45rem; }
    [data-testid="stSidebarNav"] { display: none; }
}

.status-pending    { color: #F59E0B; font-weight: 600; }
.status-processing { color: #3B82F6; font-weight: 600; }
.status-completed  { color: #10B981; font-weight: 600; }
.status-cancelled  { color: #EF4444; font-weight: 600; }
.status-on-hold    { color: #8B5CF6; font-weight: 600; }
.status-refunded   { color: #F97316; font-weight: 600; }
.status-failed     { color: #9CA3AF; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# Clean, consistent styling for every Plotly figure (dark theme)
def sketchify(fig):
    fig.update_layout(
        font=dict(family="Inter, sans-serif", size=13, color="#C9CFDB"),
        title_font=dict(family="Inter, sans-serif", size=15, color="#E5E7EB"),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(font=dict(color="#A8B0C0")),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, linecolor="rgba(255,255,255,0.12)")
    fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.06)", zeroline=False)
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

STATUS_COLOR = {
    "pending":    "#F59E0B",
    "processing": "#3B82F6",
    "on-hold":    "#8B5CF6",
    "completed":  "#10B981",
    "cancelled":  "#EF4444",
    "refunded":   "#F97316",
    "failed":     "#6B7280",
}

# Status grouping: Processing vs Failed/Cancelled vs Completed
PROCESSING_STATUSES = {"pending", "processing", "on-hold"}
FAILED_STATUSES     = {"cancelled", "failed", "refunded"}

def status_group(s: str) -> str:
    if s in PROCESSING_STATUSES:
        return "🟡 Processing"
    if s in FAILED_STATUSES:
        return "🔴 Failed/Cancelled"
    if s == "completed":
        return "🟢 Completed"
    return "⚪ Other"

TEST_MIN_TOTAL = 100.0  # orders below this (₹) treated as test orders

# ── Data fetch ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=180)
def fetch_orders(days_back: int, status_filter: str) -> pd.DataFrame:
    after = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")
    params = {"per_page": 50, "orderby": "date", "order": "desc",
              "after": after, "_fields": WC_FIELDS}
    if status_filter != "all":
        params["status"] = status_filter

    all_orders, page = [], 1
    while page <= 20:
        params["page"] = page
        try:
            r = SESSION.get(f"{WC_BASE}/orders", params=params, auth=AUTH, timeout=TIMEOUT)
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
    col.markdown(
        f'<div class="kpi" style="--accent:{color}">'
        f'<div class="kpi-emoji">{emoji}</div>'
        f'<div class="kpi-val">{value}</div>'
        f'<div class="kpi-lbl">{label}</div></div>',
        unsafe_allow_html=True,
    )


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Filters")
    days_back     = st.selectbox("Date range", [7, 14, 30, 60, 90, 180, 365], index=2,
                                  format_func=lambda x: f"Last {x} days")
    status_filter = st.selectbox("Status", ["all","pending","processing","on-hold",
                                             "completed","cancelled","refunded","failed"])
    st.markdown("---")
    hide_tests = st.toggle("🧹 Hide test orders (<₹100 / “test”)", value=True)
    auto_refresh  = st.toggle("Auto-refresh (3 min)", value=False)
    if st.button("🔄 Refresh now"):
        st.cache_data.clear()
        st.rerun()
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()
    st.caption(f"Updated: {datetime.fromtimestamp(st.session_state.last_refresh).strftime('%H:%M:%S')}")

# ── Load ──────────────────────────────────────────────────────────────────────
with st.spinner("Loading orders…"):
    df_raw = fetch_orders(days_back, status_filter)

if df_raw.empty:
    st.warning("No orders found.")
    st.stop()

test_n = int(df_raw["IsTest"].sum())
df = df_raw[~df_raw["IsTest"]].copy() if hide_tests else df_raw.copy()

# ── Hero header ───────────────────────────────────────────────────────────────
hidden_note = f" · 🧹 {test_n} test hidden" if hide_tests and test_n else ""
st.markdown(
    f'<div class="chuk-hero"><h1>🧁 CHUK Orders</h1>'
    f'<p>chuk.in · last {days_back} days · <b>{len(df)} orders</b>{hidden_note}</p></div>',
    unsafe_allow_html=True,
)

if df.empty:
    st.warning("No orders after filters.")
    st.stop()

# ── Overall KPIs ──────────────────────────────────────────────────────────────
total_rev     = df["Total"].sum()
processing_n  = int(df["StatusGrp"].eq("🟡 Processing").sum())
failed_n      = int(df["StatusGrp"].eq("🔴 Failed/Cancelled").sum())
website_n     = int(df["Type"].eq("Website Order").sum())
sample_n      = int(df["Type"].eq("Sample Kit").sum())

r1 = st.columns(3)
kpi_card(r1[0], "🧾", len(df),              "Total Orders",   "#FF6A88")
kpi_card(r1[1], "💰", f"₹{total_rev:,.0f}", "Total Revenue",  "#10B981")
kpi_card(r1[2], "🌐", website_n,            "Website Orders", "#3B82F6")
st.write("")
r2 = st.columns(3)
kpi_card(r2[0], "🧪", sample_n,        "Sample Kits",      "#8B5CF6")
kpi_card(r2[1], "🟡", processing_n,    "Processing",       "#F59E0B")
kpi_card(r2[2], "🔴", failed_n,        "Failed/Cancelled", "#EF4444")

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
        "Show", ["✨ All", "🟡 Processing", "🟢 Completed", "🔴 Failed/Cancelled"],
        horizontal=True, key=f"grp_{key}",
    )
    view = section_df if grp == "✨ All" else section_df[section_df["StatusGrp"] == grp]

    # Mini KPI row for this group
    g1, g2, g3 = st.columns(3)
    kpi_card(g1, "🧾", len(view),                          "Orders",  "#FF6A88")
    kpi_card(g2, "💰", f"₹{view['Total'].sum():,.0f}",     "Revenue", "#10B981")
    avg = view["Total"].mean() if len(view) else 0
    kpi_card(g3, "📊", f"₹{avg:,.0f}",                     "Avg Order", "#3B82F6")
    st.write("")

    search = st.text_input("🔎 Search order / customer / city / product",
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

    styled = disp[cols].style.map(color_status, subset=["Status"])
    st.dataframe(styled, use_container_width=True, height=420, hide_index=True)
    st.caption(f"Showing {len(disp)} of {len(view)} orders")

    csv = view.drop(columns=["Day", "WC_ID", "StateCode", "IsTest"]).to_csv(index=False).encode("utf-8")
    st.download_button("⬇ Download CSV", data=csv,
                       file_name=f"chuk_{key}_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                       mime="text/csv", key=f"csv_{key}")


# ══════════════════════════════════════════════════════════════════════════════
# ORDERS — tabs by Type: Website vs Sample Kit
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-h">🧾 Orders</div>', unsafe_allow_html=True)
tab_web, tab_sample = st.tabs([f"🌐 Website Orders ({website_n})",
                               f"🧪 Sample Kits ({sample_n})"])
with tab_web:
    render_orders(df[df["Type"] == "Website Order"], "web")
with tab_sample:
    render_orders(df[df["Type"] == "Sample Kit"], "sample")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# CHARTS
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="sec-h">📊 Analytics</div>', unsafe_allow_html=True)

daily = df.groupby(["Day","Status"]).size().reset_index(name="Count")
fig_daily = px.bar(daily, x="Day", y="Count", color="Status",
                   color_discrete_map=STATUS_COLOR, title="Orders per Day",
                   labels={"Day":"","Count":"Orders"}, height=280)
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
                     color="Group",
                     color_discrete_map={"🟡 Processing":"#F59E0B","🟢 Completed":"#10B981",
                                         "🔴 Failed/Cancelled":"#EF4444","⚪ Other":"#9CA3AF"})
    fig_grp.update_layout(showlegend=True, legend=dict(orientation="h", font_size=10),
                          margin=dict(l=0,r=0,t=40,b=0), paper_bgcolor="rgba(0,0,0,0)")
    fig_grp.update_traces(textposition="inside", textinfo="percent", textfont_size=11)
    st.plotly_chart(sketchify(fig_grp), use_container_width=True)

with cb:
    td = df.groupby("Type").agg(Orders=("WC_ID","count"), Revenue=("Total","sum")).reset_index()
    fig_type = px.bar(td, x="Type", y="Revenue", color="Type",
                      color_discrete_map={"Sample Kit":"#8B5CF6","Website Order":"#3B82F6"},
                      title="Revenue by Type (₹)", labels={"Revenue":"₹","Type":""},
                      height=280, text="Orders")
    fig_type.update_traces(texttemplate="%{text} orders", textposition="outside")
    fig_type.update_layout(showlegend=False, margin=dict(l=0,r=0,t=40,b=0),
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(sketchify(fig_type), use_container_width=True)

state_rev = (df.groupby("State")["Total"].sum()
               .sort_values(ascending=False).head(12).reset_index())
fig_state = px.bar(state_rev, x="Total", y="State", orientation="h",
                   title="Top States by Revenue (₹)",
                   labels={"Total":"₹","State":""},
                   height=320, color="Total", color_continuous_scale="RdPu")
fig_state.update_layout(
    margin=dict(l=0,r=0,t=40,b=0), coloraxis_showscale=False,
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
                      height=300, color="Orders", color_continuous_scale="Blues")
    fig_city.update_layout(
        margin=dict(l=0,r=0,t=40,b=0), coloraxis_showscale=False,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(sketchify(fig_city), use_container_width=True)

with cf:
    pay_d = (df.groupby("Payment").agg(Orders=("WC_ID","count"))
               .sort_values("Orders", ascending=False).reset_index())
    fig_pay = px.bar(pay_d, x="Payment", y="Orders", title="Payment Method",
                     labels={"Payment":"","Orders":""},
                     height=300, color="Orders", color_continuous_scale="Purples",
                     text="Orders")
    fig_pay.update_traces(textposition="outside")
    fig_pay.update_layout(showlegend=False, margin=dict(l=0,r=0,t=40,b=0),
                           coloraxis_showscale=False,
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
