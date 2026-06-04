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
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Mobile-first CSS ──────────────────────────────────────────────────────────
st.markdown("""
<style>
/* Tighten padding on mobile */
.block-container { padding: 1rem 1rem 2rem !important; }

/* Stack all st.columns on mobile */
@media (max-width: 768px) {
    [data-testid="column"] {
        width: 100% !important;
        flex: 1 1 100% !important;
        min-width: 100% !important;
    }
    /* Smaller metric font */
    [data-testid="metric-container"] {
        padding: 0.4rem !important;
    }
    [data-testid="metric-container"] label {
        font-size: 0.7rem !important;
    }
    [data-testid="metric-container"] [data-testid="stMetricValue"] {
        font-size: 1.2rem !important;
    }
    /* Full-width sidebar toggle */
    [data-testid="stSidebarNav"] { display: none; }
}

/* Status badge colours in table */
.status-pending    { color: #F59E0B; font-weight: 600; }
.status-processing { color: #3B82F6; font-weight: 600; }
.status-completed  { color: #10B981; font-weight: 600; }
.status-cancelled  { color: #EF4444; font-weight: 600; }
.status-on-hold    { color: #8B5CF6; font-weight: 600; }
.status-refunded   { color: #F97316; font-weight: 600; }
.status-failed     { color: #6B7280; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

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
TIMEOUT = (8, 20)

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

# ── Data fetch ────────────────────────────────────────────────────────────────
@st.cache_data(ttl=180)
def fetch_orders(days_back: int, status_filter: str) -> pd.DataFrame:
    after = (datetime.now() - timedelta(days=days_back)).strftime("%Y-%m-%dT00:00:00")
    params = {"per_page": 50, "orderby": "date", "order": "desc", "after": after}
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
        rows.append({
            "Order":    "#" + str(o["number"]),
            "Date":     pd.to_datetime(o["date_created"]),
            "Status":   o["status"],
            "Type":     "Sample Kit" if is_sample else "Website Order",
            "Customer": f"{o['billing'].get('first_name','')} {o['billing'].get('last_name','')}".strip(),
            "Email":    o["billing"].get("email", ""),
            "Phone":    o["billing"].get("phone", ""),
            "City":     o["billing"].get("city", "").title(),
            "State":    STATE_MAP.get(state_code, state_code),
            "StateCode":state_code,
            "Products": product_names,
            "Total":    float(o.get("total", 0) or 0),
            "Payment":  o.get("payment_method_title", ""),
            "WC_ID":    o["id"],
            "Day":      None,
        })

    df = pd.DataFrame(rows)
    df["Date"] = pd.to_datetime(df["Date"]).dt.tz_localize(None)
    df["Day"]  = df["Date"].dt.date
    return df


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### ⚙️ Filters")
    days_back     = st.selectbox("Date range", [7, 14, 30, 60, 90, 180, 365], index=2,
                                  format_func=lambda x: f"Last {x} days")
    status_filter = st.selectbox("Status", ["all","pending","processing","on-hold",
                                             "completed","cancelled","refunded","failed"])
    order_type    = st.selectbox("Order type", ["All", "Sample Kit", "Website Order"])
    st.markdown("---")
    auto_refresh  = st.toggle("Auto-refresh (3 min)", value=False)
    if st.button("🔄 Refresh now"):
        st.cache_data.clear()
        st.rerun()
    if "last_refresh" not in st.session_state:
        st.session_state.last_refresh = time.time()
    st.caption(f"Updated: {datetime.fromtimestamp(st.session_state.last_refresh).strftime('%H:%M:%S')}")

# ── Load ──────────────────────────────────────────────────────────────────────
with st.spinner("Loading orders…"):
    df = fetch_orders(days_back, status_filter)

if df.empty:
    st.warning("No orders found.")
    st.stop()

if order_type != "All":
    df = df[df["Type"] == order_type]

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("## 📦 CHUK Orders")
st.caption(f"chuk.in · last {days_back} days · **{len(df)} orders**")

# ── KPIs ──────────────────────────────────────────────────────────────────────
total_rev     = df["Total"].sum()
completed_rev = df[df["Status"] == "completed"]["Total"].sum()
processing_n  = int((df["Status"] == "processing").sum())
pending_n     = int((df["Status"] == "pending").sum())
sample_n      = int((df["Type"] == "Sample Kit").sum())
website_n     = int((df["Type"] == "Website Order").sum())

c1, c2, c3 = st.columns(3)
c1.metric("Total Orders",   len(df))
c2.metric("Total Revenue",  f"₹{total_rev:,.0f}")
c3.metric("Completed Rev",  f"₹{completed_rev:,.0f}")

c4, c5, c6 = st.columns(3)
c4.metric("Processing",  processing_n)
c5.metric("Pending",     pending_n)
c6.metric("Sample Kits", sample_n)

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# ORDERS TABLE — first, before charts
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 🧾 All Orders")

search    = st.text_input("Search order / customer / city / product", placeholder="Type to filter…")
state_list = ["All"] + sorted(df["State"].dropna().unique().tolist())

col_f1, col_f2 = st.columns([1, 1])
with col_f1:
    state_sel  = st.selectbox("State", state_list)
with col_f2:
    show_contact = st.checkbox("Show email & phone", value=False)

display = df.copy()
if search:
    mask = (
        display["Customer"].str.contains(search, case=False, na=False) |
        display["City"].str.contains(search, case=False, na=False) |
        display["Products"].str.contains(search, case=False, na=False) |
        display["Order"].str.contains(search, case=False, na=False)
    )
    display = display[mask]
if state_sel != "All":
    display = display[display["State"] == state_sel]

display = display.copy()
display["Date"]  = display["Date"].dt.strftime("%d %b %y %H:%M")
display["Total"] = display["Total"].apply(lambda x: f"₹{x:,.0f}")

base_cols = ["Order", "Date", "Status", "Type", "Customer", "City", "State", "Products", "Total", "Payment"]
if show_contact:
    base_cols = ["Order", "Date", "Status", "Type", "Customer", "Email", "Phone",
                 "City", "State", "Products", "Total", "Payment"]

def color_status(val):
    return f"color:{STATUS_COLOR.get(val,'#6B7280')};font-weight:600"

styled = display[base_cols].style.map(color_status, subset=["Status"])
st.dataframe(styled, use_container_width=True, height=420, hide_index=True)
st.caption(f"Showing {len(display)} of {len(df)} orders")

csv = df.drop(columns=["Day","WC_ID","StateCode"]).to_csv(index=False).encode("utf-8")
st.download_button("⬇ Download CSV", data=csv,
                   file_name=f"chuk_orders_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                   mime="text/csv")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# CHARTS — single column on mobile (CSS handles stacking), 2-col on desktop
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("### 📊 Analytics")

# Chart 1: Orders per day (full width)
daily = df.groupby(["Day","Status"]).size().reset_index(name="Count")
fig_daily = px.bar(daily, x="Day", y="Count", color="Status",
                   color_discrete_map=STATUS_COLOR, title="Orders per Day",
                   labels={"Day":"","Count":"Orders"}, height=280)
fig_daily.update_layout(
    legend=dict(orientation="h", yanchor="bottom", y=1.02, font_size=11),
    margin=dict(l=0,r=0,t=40,b=0),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
)
st.plotly_chart(fig_daily, use_container_width=True)

# Chart 2+3: Status donut | Order type — stacks on mobile
ca, cb = st.columns(2)
with ca:
    sc = df["Status"].value_counts().reset_index()
    sc.columns = ["Status","Count"]
    fig_pie = px.pie(sc, names="Status", values="Count", color="Status",
                     color_discrete_map=STATUS_COLOR, title="By Status",
                     height=280, hole=0.45)
    fig_pie.update_layout(
        showlegend=True,
        legend=dict(orientation="h", font_size=10),
        margin=dict(l=0,r=0,t=40,b=0),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig_pie.update_traces(textposition="inside", textinfo="percent+label",
                          textfont_size=10)
    st.plotly_chart(fig_pie, use_container_width=True)

with cb:
    td = df.groupby("Type").agg(Orders=("WC_ID","count"), Revenue=("Total","sum")).reset_index()
    fig_type = px.bar(td, x="Type", y="Revenue", color="Type",
                      color_discrete_map={"Sample Kit":"#10B981","Website Order":"#3B82F6"},
                      title="Revenue by Type (₹)", labels={"Revenue":"₹","Type":""},
                      height=280, text="Orders")
    fig_type.update_traces(texttemplate="%{text} orders", textposition="outside")
    fig_type.update_layout(showlegend=False, margin=dict(l=0,r=0,t=40,b=0),
                            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig_type, use_container_width=True)

# Chart 4: Top states (full width)
state_rev = (df.groupby("State")["Total"].sum()
               .sort_values(ascending=False).head(12).reset_index())
fig_state = px.bar(state_rev, x="Total", y="State", orientation="h",
                   title="Top States by Revenue (₹)",
                   labels={"Total":"₹","State":""},
                   height=320, color="Total", color_continuous_scale="Greens")
fig_state.update_layout(
    margin=dict(l=0,r=0,t=40,b=0), coloraxis_showscale=False,
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    yaxis=dict(autorange="reversed"),
)
st.plotly_chart(fig_state, use_container_width=True)

# Chart 5+6: Top cities | Payment — stacks on mobile
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
    st.plotly_chart(fig_city, use_container_width=True)

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
    st.plotly_chart(fig_pay, use_container_width=True)

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
