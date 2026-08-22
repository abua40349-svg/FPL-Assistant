import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone

st.set_page_config(page_title="My FPL Secret Weapon", page_icon="⚽", layout="centered")

API_BASE = "https://fantasy.premierleague.com/api"
POS_NAMES = ["GK", "DEF", "MID", "FWD"]
STATUS_LABELS = {"i": "Injured", "s": "Suspended", "d": "Doubtful", "u": "Unavailable", "n": "Not available"}
CHIP_LABELS = {"wildcard": "Wildcard", "3xc": "Triple captain", "bboost": "Bench boost", "freehit": "Free hit"}

# --- iOS-style theme ---
st.markdown("""
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#F2F2F7">
<style>
  html, body, [class*="css"] { font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Helvetica Neue", sans-serif !important; }
  .stApp { background-color: #F2F2F7; }
  #MainMenu, footer, header { visibility: hidden; }
  h1 { font-size: 2.1rem !important; font-weight: 800 !important; letter-spacing: -0.02em; color: #1C1C1E; padding-top: 0.4rem; }
  h2, h3 { font-weight: 700 !important; letter-spacing: -0.01em; color: #1C1C1E; margin-top: 1.6rem !important; }
  .stCaption, [data-testid="stCaptionContainer"] { color: #8E8E93 !important; }
  [data-testid="stVerticalBlockBorderWrapper"], div[data-testid="stExpander"], div[data-testid="stMetric"], div[data-testid="stDataFrame"], .stTable {
    background: #FFFFFF !important; border-radius: 18px !important; border: none !important; box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 1px 2px rgba(0,0,0,0.04); padding: 4px;
  }
  div[data-testid="stMetric"] { padding: 14px 10px !important; text-align: center; }
  div[data-testid="stMetricLabel"] { color: #8E8E93 !important; font-size: 0.8rem !important; }
  div[data-testid="stMetricValue"] { color: #1C1C1E !important; font-weight: 700 !important; }
  .stTextInput > div > div > input { border-radius: 12px !important; border: 1px solid #E5E5EA !important; background: #FFFFFF !important; padding: 10px 14px !important; font-size: 1rem !important; }
  .stTextInput label { font-weight: 600 !important; color: #1C1C1E !important; font-size: 0.9rem !important; }
  .stButton > button { border-radius: 980px !important; background: #007AFF !important; color: #FFFFFF !important; border: none !important; font-weight: 600 !important; padding: 10px 22px !important; box-shadow: none !important; transition: opacity 0.15s ease; }
  .stButton > button:hover { opacity: 0.85; background: #007AFF !important; color: #fff !important; }
  div[data-testid="stAlert"] { border-radius: 14px !important; border: none !important; padding: 12px 14px !important; }
  hr { border-color: #E5E5EA !important; }
  .block-container { padding-top: 1.2rem !important; padding-bottom: 3rem !important; }
</style>
""", unsafe_allow_html=True)

st.title("⚽ My FPL Secret Weapon")
st.caption("Your private analytical dashboard")

def get(url, timeout=10):
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Ralat rangkaian: {e}")
        return None

@st.cache_data(ttl=300)
def fetch_static():
    return get(f"{API_BASE}/bootstrap-static/")

@st.cache_data(ttl=300)
def fetch_all_fixtures():
    return get(f"{API_BASE}/fixtures/")

def fetch_entry(team_id): return get(f"{API_BASE}/entry/{team_id}/")
def fetch_picks(team_id, gw): return get(f"{API_BASE}/entry/{team_id}/event/{gw}/picks/")

def fmt_countdown(target_iso):
    target = datetime.fromisoformat(target_iso.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    delta = target - now
    if delta.total_seconds() <= 0:
        return "Tamat tempoh"
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    mins = rem // 60
    return f"{days} hari {hours}j {mins}m"

# --- Input Section ---
with st.container():
    default_team = st.session_state.get("team_id", "1152818")
    team_id = st.text_input("FPL Team ID", value=default_team)
    load = st.button("Muatkan Data", type="primary")

if load or "auto_loaded" not in st.session_state:
    st.session_state["auto_loaded"] = True
    st.session_state["team_id"] = team_id

    if not team_id or not team_id.strip().isdigit():
        st.warning("Sila masukkan Team ID yang sah.")
        st.stop()

    with st.spinner("Menganalisis skuad..."):
        static = fetch_static()
        if not static: st.stop()

        elements = {p["id"]: p for p in static["elements"]}
        teams = {t["id"]: t["short_name"] for t in static["teams"]}
        events = static["events"]
        
        current_event = next((e for e in events if e["is_current"]), None) or next((e for e in events if e["is_next"]), None)
        next_event = next((e for e in events if e["is_next"]), current_event)
        gw_for_picks = (next((e for e in events if e["is_current"]), None) or next((e for e in events if e["is_previous"]), None) or events[0])["id"]

        entry = fetch_entry(team_id)
        picks_data = fetch_picks(team_id, gw_for_picks)

        if not entry or not picks_data or "picks" not in picks_data:
            st.error("Pasukan tidak dijumpai. Semak semula Team ID.")
            st.stop()

        bank = (picks_data.get("entry_history", {}).get("bank", 0)) / 10
        team_value = (picks_data.get("entry_history", {}).get("value", 0)) / 10

        squad = []
        for pick in picks_data["picks"]:
            p = elements.get(pick["element"])
            if not p: continue
            squad.append({
                "id": p["id"],
                "name": p["web_name"],
                "team": p["team"],
                "team_short": teams.get(p["team"], "?"),
                "pos": POS_NAMES[p["element_type"] - 1],
                "pos_idx": p["element_type"],
                "price": p["now_cost"] / 10,
                "form": float(p.get("form") or 0),
                "status": p.get("status"),
                "news": p.get("news"),
                "captain": pick["is_captain"],
                "bench": pick["position"] > 11,
                # METRIK ANALITIK LANJUTAN (FEATURE 3)
                "xP": float(p.get("ep_next") or 0.0),
                "xG": float(p.get("expected_goals") or 0.0),
                "xA": float(p.get("expected_assists") or 0.0),
            })
        
        starters = [p for p in squad if not p["bench"]]
        bench = [p for p in squad if p["bench"]]

        # FEATURE 5: NOTIFIKASI KECEDERAAN (INJURY ALERTS)
        flagged_starters = [p for p in starters if p["status"] and p["status"] != "a"]
        if flagged_starters:
            alert_msgs = [f"**{p['name']}** ({STATUS_LABELS.get(p['status'], 'Bermasalah')}): {p['news']}" for p in flagged_starters]
            st.error("🚨 **AMARAN KECEDERAAN KESEBELASAN UTAMA!**\n\n- " + "\n- ".join(alert_msgs))

        # --- Dashboard Header ---
        st.subheader(entry.get("name", "Pasukan Saya"))
        c1, c2, c3 = st.columns(3)
        c1.metric("Nilai Skuad", f"£{team_value:.1f}m")
        c2.metric("Bank", f"£{bank:.1f}m")
        if next_event:
            c3.metric(f"GW{next_event['id']} Deadline", fmt_countdown(next_event['deadline_time']))

        # --- FEATURE 1: SIMULATOR PERTUKARAN ---
        st.markdown("### 🔄 Simulator Pertukaran")
        col_sell, col_buy = st.columns(2)
        
        with col_sell:
            sell_name = st.selectbox("👋 Jual Pemain", [f"{p['name']} (£{p['price']:.1f}m)" for p in squad])
            sell_p = next(p for p in squad if f"{p['name']} (£{p['price']:.1f}m)" == sell_name)
            est_sell_price = sell_p["price"] - 0.1 if sell_p["price"] >= 5.0 else sell_p["price"]
            est_budget = bank + est_sell_price
            st.caption(f"Anggaran Bajet Baharu: **£{est_budget:.1f}m**")

        with col_buy:
            buy_candidates = [
                e for e in static["elements"]
                if e["element_type"] == sell_p["pos_idx"] and e["id"] != sell_p["id"] and (e["now_cost"]/10) <= est_budget
            ]
            buy_candidates = sorted(buy_candidates, key=lambda x: float(x.get("ep_next") or 0), reverse=True)
            
            buy_options = {f"{c['web_name']} (£{c['now_cost']/10:.1f}m) | xP: {c.get('ep_next', 0)}": c for c in buy_candidates}
            if buy_options:
                buy_name = st.selectbox("🤝 Beli Pemain", list(buy_options.keys()))
                buy_p = buy_options[buy_name]
            else:
                st.warning("Tiada pilihan dalam bajet ini.")
                buy_p = None

        if buy_p:
            new_bank = est_budget - (buy_p["now_cost"] / 10)
            xp_diff = float(buy_p.get("ep_next", 0)) - sell_p["xP"]
            st.info(f"**Impak Simulasi:** Baki Bank: £{new_bank:.1f}m | Perubahan Jangkaan Mata (xP): **{'+' if xp_diff > 0 else ''}{xp_diff:.1f}**")

        # --- FEATURE 4: RADAR JADUAL 5 MINGGU (FIXTURE TICKER) ---
        st.markdown("### 🚥 Radar Jadual (5 GW Seterusnya)")
        all_fixtures = fetch_all_fixtures()
        team_fdr = {t: {} for t in teams.keys()}
        next_5_gws = [next_event['id'] + i for i in range(5)] if next_event else []

        if all_fixtures and next_5_gws:
            for f in all_fixtures:
                gw = f["event"]
                if gw in next_5_gws:
                    team_fdr[f["team_h"]][gw] = f["team_h_difficulty"]
                    team_fdr[f["team_a"]][gw] = f["team_a_difficulty"]
            
            diff_emoji = {1: "🟢 1", 2: "🟢 2", 3: "⚪ 3", 4: "🔴 4", 5: "🟤 5"}
            ticker_data = []
            for p in starters:
                row = {"Pemain": p["name"], "Team": p["team_short"]}
                for gw in next_5_gws:
                    fdr = team_fdr.get(p["team"], {}).get(gw, 3)
                    row[f"GW{gw}"] = diff_emoji.get(fdr, str(fdr))
                ticker_data.append(row)
            
            st.dataframe(ticker_data, use_container_width=True, hide_index=True)

        # --- FEATURE 3: JADUAL METRIK ANALITIK (STARTING XI & BENCH) ---
        st.markdown("### 📈 Analitik Skuad Utama (Starting XI)")
        st.dataframe(
            [{"Pos": p["pos"], "Nama": p["name"] + (" (C)" if p["captain"] else ""), "Team": p["team_short"], "Harga": f"£{p['price']:.1f}m", "xP (Next GW)": p["xP"], "xG (Musim)": p["xG"], "xA (Musim)": p["xA"]} for p in starters],
            use_container_width=True, hide_index=True
        )
        
        st.markdown("### 🪑 Bangku Simpanan (Bench)")
        st.dataframe(
            [{"Pos": p["pos"], "Nama": p["name"], "Team": p["team_short"], "Harga": f"£{p['price']:.1f}m", "xP": p["xP"], "Status": STATUS_LABELS.get(p["status"], "OK") if p["status"] != "a" else "OK"} for p in bench],
            use_container_width=True, hide_index=True
        )
