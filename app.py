import streamlit as st
import requests
import pandas as pd
from datetime import datetime, timezone

st.set_page_config(page_title="My FPL Secret Weapon", page_icon="⚽", layout="centered")

API_BASE = "https://fantasy.premierleague.com/api"
POS_NAMES = ["GK", "DEF", "MID", "FWD"]
STATUS_LABELS = {"i": "Cedera", "s": "Digantung", "d": "Diragui", "u": "Tidak Tersedia", "n": "Tidak Tersedia"}

# --- iOS-style theme & Custom CSS ---
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
  
  /* PITCH VIEW CSS */
  .pitch-container { background: linear-gradient(180deg, #2A8C4A 0%, #237A3E 100%); border-radius: 16px; padding: 20px 10px; margin-bottom: 20px; border: 2px solid #1E6B35; box-shadow: inset 0 0 20px rgba(0,0,0,0.2); }
  .bench-container { background: linear-gradient(180deg, #E5E5EA 0%, #D1D1D6 100%); border-radius: 16px; padding: 15px 10px; margin-bottom: 20px; }
  .pitch-row { display: flex; justify-content: space-evenly; margin-bottom: 15px; }
  .player-card { background-color: rgba(255, 255, 255, 0.95); border-radius: 8px; padding: 6px; width: 78px; text-align: center; box-shadow: 0 4px 6px rgba(0,0,0,0.15); border-bottom: 4px solid #007AFF; }
  .player-name { font-weight: 800; font-size: 11px; color: #1C1C1E; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .player-team { font-size: 10px; color: #8E8E93; font-weight: 700; margin-bottom: 2px; }
  .player-stat { font-size: 10px; color: #007AFF; font-weight: 800; margin-top: 2px; background: #F2F2F7; border-radius: 4px; padding: 2px; }
  .player-tsb { font-size: 9px; color: #48484A; font-weight: 600; margin-top: 2px; }
  .captain-tag { font-size: 9px; color: #FF9500; font-weight: 900; }
  .block-container { padding-top: 1.2rem !important; padding-bottom: 3rem !important; }
</style>
""", unsafe_allow_html=True)

st.title("⚽ My FPL Secret Weapon")
st.caption("Papan pemuka pengurus elit")

def get(url, timeout=10):
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Ralat rangkaian: {e}")
        return None

@st.cache_data(ttl=300)
def fetch_static(): return get(f"{API_BASE}/bootstrap-static/")

@st.cache_data(ttl=300)
def fetch_all_fixtures(): return get(f"{API_BASE}/fixtures/")

def fetch_entry(team_id): return get(f"{API_BASE}/entry/{team_id}/")
def fetch_picks(team_id, gw): return get(f"{API_BASE}/entry/{team_id}/event/{gw}/picks/")

def fmt_countdown(target_iso):
    target = datetime.fromisoformat(target_iso.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    delta = target - now
    if delta.total_seconds() <= 0: return "Tamat tempoh"
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    mins = rem // 60
    return f"{days}h {hours}j {mins}m"

# Helper membina kad pemain dengan Ownership & Amararan Harga
def build_player_card(p):
    cap_text = "<span class='captain-tag'> (C)</span>" if p['captain'] else "<span class='captain-tag'> (V)</span>" if p['vice'] else ""
    status_alert = f" 🔴" if p['status'] != 'a' else ""
    trend_icon = f" 📈" if p['trend'] > 75000 else f" 📉" if p['trend'] < -75000 else ""
    
    return f"""
    <div class="player-card">
        <div class="player-name">{p['name']}{cap_text}</div>
        <div class="player-team">{p['team_short']}{status_alert}{trend_icon}</div>
        <div class="player-stat">xP: {p['xP']}</div>
        <div class="player-tsb">{p['tsb']}% TSB</div>
    </div>
    """

def build_row(players):
    cards_html = "".join([build_player_card(p) for p in players])
    return f'<div class="pitch-row">{cards_html}</div>'

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
            
            # Pengiraan Trend Harga (Net Transfers)
            net_transfers = p.get("transfers_in_event", 0) - p.get("transfers_out_event", 0)
            
            squad.append({
                "id": p["id"],
                "name": p["web_name"],
                "team": p["team"],
                "team_short": teams.get(p["team"], "?"),
                "pos": POS_NAMES[p["element_type"] - 1],
                "pos_idx": p["element_type"],
                "price": p["now_cost"] / 10,
                "status": p.get("status"),
                "news": p.get("news"),
                "captain": pick["is_captain"],
                "vice": pick["is_vice_captain"],
                "bench": pick["position"] > 11,
                "xP": float(p.get("ep_next") or 0.0),
                "xG": float(p.get("expected_goals") or 0.0),
                "xA": float(p.get("expected_assists") or 0.0),
                "tsb": p.get("selected_by_percent", "0.0"),
                "trend": net_transfers
            })
        
        starters = [p for p in squad if not p["bench"]]
        bench = [p for p in squad if p["bench"]]

        s_gk = [p for p in starters if p["pos"] == "GK"]
        s_def = [p for p in starters if p["pos"] == "DEF"]
        s_mid = [p for p in starters if p["pos"] == "MID"]
        s_fwd = [p for p in starters if p["pos"] == "FWD"]
        formation = f"{len(s_def)}-{len(s_mid)}-{len(s_fwd)}"

        # --- Dashboard Header ---
        st.subheader(f"{entry.get('name', 'Pasukan Saya')} 🛡️ {formation}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Nilai Skuad", f"£{team_value:.1f}m")
        c2.metric("Baki Bank", f"£{bank:.1f}m")
        if next_event:
            c3.metric(f"GW{next_event['id']} Deadline", fmt_countdown(next_event['deadline_time']))

        # NOTIFIKASI KECEDERAAN (Kekal di atas supaya jelas)
        flagged_starters = [p for p in starters if p["status"] and p["status"] != "a"]
        if flagged_starters:
            alert_msgs = [f"**{p['name']}** ({STATUS_LABELS.get(p['status'], 'Bermasalah')}): {p['news']}" for p in flagged_starters]
            st.error("🚨 **AMARAN KECEDERAAN UTAMA!**\n\n- " + "\n- ".join(alert_msgs))

        # ==========================================
        # SISTEM TABS (UI Lebih Kemas)
        # ==========================================
        tab1, tab2, tab3, tab4 = st.tabs(["🏟️ Skuad Utama", "🔄 Transfer Hub", "🚥 Fixture Radar", "📊 Data Analitik"])

        # --- TAB 1: PADANG & BANGKU SIMPANAN ---
        with tab1:
            st.markdown("💡 *Petunjuk: 📉 Ramai jual (Awas harga jatuh) | 📈 Ramai beli (Harga akan naik) | 🔴 Bermasalah*")
            
            pitch_html = f"""
            <div class="pitch-container">
                {build_row(s_gk)}
                {build_row(s_def)}
                {build_row(s_mid)}
                {build_row(s_fwd)}
            </div>
            """
            st.markdown(pitch_html, unsafe_allow_html=True)
            
            st.markdown("### 🪑 Bangku Simpanan")
            bench_html = f"""
            <div class="bench-container">
                {build_row(bench)}
            </div>
            """
            st.markdown(bench_html, unsafe_allow_html=True)

        # --- TAB 2: SIMULATOR PERTUKARAN ---
        with tab2:
            st.markdown("### 🔄 Simulator Pertukaran")
            col_sell, col_buy = st.columns(2)
            
            with col_sell:
                sell_name = st.selectbox("👋 Jual Pemain", [f"{p['name']} (£{p['price']:.1f}m)" for p in squad])
                sell_p = next(p for p in squad if f"{p['name']} (£{p['price']:.1f}m)" == sell_name)
                est_sell_price = sell_p["price"] - 0.1 if sell_p["price"] >= 5.0 else sell_p["price"]
                est_budget = bank + est_sell_price
                st.info(f"Bajet Pembelian: **£{est_budget:.1f}m**")

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
                st.success(f"**Keputusan Simulasi:** Baki Bank: £{new_bank:.1f}m | Perubahan xP: **{'+' if xp_diff > 0 else ''}{xp_diff:.1f}**")

        # --- TAB 3: RADAR JADUAL (PENGESAN BGW/DGW) ---
        with tab3:
            st.markdown("### 🚥 Radar Jadual Pintar (5 GW)")
            st.caption("Petunjuk Khas: ⬛ **BGW (Tiada Game)** | 🟦 **DGW (Double Game)**")
            
            all_fixtures = fetch_all_fixtures()
            team_gw_fixtures = {t: {} for t in teams.keys()}
            team_fdr_avg = {t: {} for t in teams.keys()}
            next_5_gws = [next_event['id'] + i for i in range(5)] if next_event else []

            if all_fixtures and next_5_gws:
                # Kira jumlah perlawanan & FDR untuk setiap pasukan
                for f in all_fixtures:
                    gw = f["event"]
                    if gw in next_5_gws:
                        for team_key, diff_key in [("team_h", "team_h_difficulty"), ("team_a", "team_a_difficulty")]:
                            tid = f[team_key]
                            team_gw_fixtures[tid][gw] = team_gw_fixtures[tid].get(gw, 0) + 1
                            team_fdr_avg[tid][gw] = max(team_fdr_avg[tid].get(gw, 0), f[diff_key])

                diff_emoji = {1: "🟢 1", 2: "🟢 2", 3: "⚪ 3", 4: "🔴 4", 5: "🟤 5"}
                ticker_data = []
                
                for p in starters:
                    row = {"Pemain": p["name"], "Pasukan": p["team_short"]}
                    for gw in next_5_gws:
                        match_count = team_gw_fixtures.get(p["team"], {}).get(gw, 0)
                        fdr = team_fdr_avg.get(p["team"], {}).get(gw, 3)
                        
                        if match_count == 0:
                            row[f"GW{gw}"] = "⬛ BGW"
                        elif match_count > 1:
                            row[f"GW{gw}"] = "🟦 DGW"
                        else:
                            row[f"GW{gw}"] = diff_emoji.get(fdr, str(fdr))
                            
                    ticker_data.append(row)
                
                st.dataframe(ticker_data, use_container_width=True, hide_index=True)

        # --- TAB 4: DATA ANALITIK TERPERINCI ---
        with tab4:
            st.markdown("### 📊 Jadual xG & xA Kesebelasan Utama")
            st.dataframe(
                [{"Pemain": p["name"] + (" (C)" if p["captain"] else ""), "Pos": p["pos"], "TSB%": f"{p['tsb']}%", "xP (Mata Jangkaan)": p["xP"], "xG (Jangkaan Gol)": p["xG"], "xA (Jangkaan Bantuan)": p["xA"]} for p in starters],
                use_container_width=True, hide_index=True
            )
