import streamlit as st
import requests
from datetime import datetime, timezone

st.set_page_config(page_title="FPL Assistant", page_icon="⚽", layout="centered")

API_BASE = "https://fantasy.premierleague.com/api"
POS_NAMES = ["GK", "DEF", "MID", "FWD"]
STATUS_LABELS = {"i": "Injured", "s": "Suspended", "d": "Doubtful", "u": "Unavailable", "n": "Not available"}
CHIP_LABELS = {"wildcard": "Wildcard", "3xc": "Triple captain", "bboost": "Bench boost", "freehit": "Free hit"}

# --- iOS-style theme: fonts, colors, rounded cards, pill buttons, home-screen meta tags ---
st.markdown("""
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="mobile-web-app-capable" content="yes">
<meta name="theme-color" content="#F2F2F7">
<style>
  html, body, [class*="css"] {
    font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "SF Pro Text",
                 "Helvetica Neue", Arial, sans-serif !important;
  }
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
  .stButton > button:active { opacity: 0.65; }
  button[kind="primary"] { background: #007AFF !important; }
  div[data-testid="stAlert"] { border-radius: 14px !important; border: none !important; padding: 12px 14px !important; }
  div[data-testid="stExpander"] summary { font-weight: 600 !important; color: #007AFF !important; border-radius: 14px !important; }
  hr { border-color: #E5E5EA !important; }
  .block-container { padding-top: 1.2rem !important; padding-bottom: 3rem !important; }
</style>
""", unsafe_allow_html=True)

st.title("⚽ My FPL Assistant")
st.caption("Your personal squad advisor")

def get(url, timeout=10):
    try:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {e}")
        return None

@st.cache_data(ttl=300)
def fetch_static():
    return get(f"{API_BASE}/bootstrap-static/")

def fetch_entry(team_id):
    return get(f"{API_BASE}/entry/{team_id}/")

def fetch_picks(team_id, gw):
    return get(f"{API_BASE}/entry/{team_id}/event/{gw}/picks/")

def fetch_history(team_id):
    return get(f"{API_BASE}/entry/{team_id}/history/")

def fetch_fixtures(gw):
    return get(f"{API_BASE}/fixtures/?event={gw}")

def fetch_standings(league_id, page=1):
    return get(f"{API_BASE}/leagues-classic/{league_id}/standings/?page_standings={page}")

def fmt_countdown(target_iso):
    target = datetime.fromisoformat(target_iso.replace("Z", "+00:00"))
    now = datetime.now(timezone.utc)
    delta = target - now
    if delta.total_seconds() <= 0:
        return "Deadline passed"
    days = delta.days
    hours, rem = divmod(delta.seconds, 3600)
    mins = rem // 60
    return f"{days}d {hours}h {mins}m"

# --- Sidebar-style inputs at top ---
with st.container():
    default_team = st.session_state.get("team_id", "1152818")
    team_id = st.text_input("FPL Team ID", value=default_team)
    league_id = st.text_input("Mini-league ID (for rival comparison)", value=st.session_state.get("league_id", ""))
    
    load = st.button("Load my dashboard", type="primary")

if load or "auto_loaded" not in st.session_state:
    st.session_state["auto_loaded"] = True
    st.session_state["team_id"] = team_id
    st.session_state["league_id"] = league_id

    if not team_id or not team_id.strip().isdigit():
        st.warning("Enter a valid Team ID first.")
        st.stop()

    with st.spinner("Loading your dashboard..."):
        static = fetch_static()
        if not static:
            st.stop()

        elements = {p["id"]: p for p in static["elements"]}
        teams = {t["id"]: t["short_name"] for t in static["teams"]}
        events = static["events"]
        current_event = next((e for e in events if e["is_current"]), None) or next((e for e in events if e["is_next"]), None)
        next_event = next((e for e in events if e["is_next"]), current_event)
        gw_for_picks = (
            next((e for e in events if e["is_current"]), None)
            or next((e for e in events if e["is_previous"]), None)
            or events[0]
        )["id"]

        entry = fetch_entry(team_id)
        picks_data = fetch_picks(team_id, gw_for_picks)
        history = fetch_history(team_id)

        if not entry or not picks_data or "picks" not in picks_data:
            st.error("Could not find that team. Double-check the Team ID.")
            st.stop()

        bank = (picks_data.get("entry_history", {}).get("bank", 0)) / 10
        team_value = (picks_data.get("entry_history", {}).get("value", 0)) / 10

        squad = []
        for pick in picks_data["picks"]:
            p = elements.get(pick["element"])
            if not p:
                continue
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
                "chance": p.get("chance_of_playing_next_round"),
                "news": p.get("news"),
                "captain": pick["is_captain"],
                "vice": pick["is_vice_captain"],
                "bench": pick["position"] > 11,
            })
        starters = [p for p in squad if not p["bench"]]
        bench = [p for p in squad if p["bench"]]

        fixture_diff = {}
        if next_event:
            fixtures = fetch_fixtures(next_event["id"])
            if fixtures:
                for f in fixtures:
                    fixture_diff[f["team_h"]] = f["team_h_difficulty"]
                    fixture_diff[f["team_a"]] = f["team_a_difficulty"]

        # --- Header ---
        st.subheader(entry.get("name", "My team"))
        st.caption(f"{entry.get('player_first_name', '')} {entry.get('player_last_name', '')}".strip())
        c1, c2, c3 = st.columns(3)
        c1.metric("Squad value", f"£{team_value:.1f}m")
        c2.metric("Bank", f"£{bank:.1f}m")
        rank = entry.get("summary_overall_rank")
        c3.metric("Overall rank", f"{rank:,}" if rank else "-")

        # --- 1. Deadline ---
        if next_event:
            st.markdown("### ⏰ Next deadline")
            st.markdown(f"**GW{next_event['id']}** — {fmt_countdown(next_event['deadline_time'])}")

        # --- 2. Squad health ---
        st.markdown("### 🩺 Squad health")
        flagged = [p for p in squad if p["status"] and p["status"] != "a"]
        if flagged:
            for p in flagged:
                label = STATUS_LABELS.get(p["status"], "Flagged")
                chance = f" ({p['chance']}% chance of playing)" if p["chance"] is not None else ""
                news = f": {p['news']}" if p["news"] else ""
                st.warning(f"**{p['name']}** — {label}{chance}{news}")
        else:
            st.success("✅ No flagged players in your squad.")

        # --- 3. Captain suggestion ---
        st.markdown("### 🎯 Captain suggestion")
        eligible = [p for p in starters if not p["status"] or p["status"] == "a"]

        def captain_score(p):
            diff = fixture_diff.get(p["team"], 3)
            return p["form"] * (6 - diff)

        ranked = sorted(eligible, key=captain_score, reverse=True)
        current_captain = next((p for p in squad if p["captain"]), None)
        if ranked:
            top = ranked[0]
            if current_captain and top["id"] == current_captain["id"]:
                st.success(f"✅ Your captain (**{current_captain['name']}**) is the strongest pick this week based on form and fixture.")
            else:
                cap_name = current_captain["name"] if current_captain else "none"
                st.info(f"Consider **{top['name']}** ({top['team_short']}) — form {top['form']:.1f} with a favorable next fixture. Currently captained: **{cap_name}**.")
        else:
            st.warning("Not enough data to suggest a captain.")

        # --- 4. Transfer suggestions ---
        st.markdown("### 🔄 Transfer suggestions")
        troubled = [p for p in squad if (p["status"] and p["status"] != "a") or p["form"] < 2.0]
        if not troubled:
            st.success("✅ No underperforming or flagged players — no urgent transfers needed.")
        else:
            for p in troubled:
                reason = STATUS_LABELS.get(p["status"], "Flagged") if (p["status"] and p["status"] != "a") else "Low form"
                news = f": {p['news']}" if p["news"] else ""
                
                # UPGRADED SELLING PRICE LOGIC:
                # Apply a conservative 0.1m buffer deduction for players who likely rose in price. 
                # This ensures we don't overestimate your budget.
                estimated_sell_price = p["price"] - 0.1 if p["price"] >= 5.0 else p["price"]
                estimated_budget = bank + estimated_sell_price
                
                alternatives = sorted(
                    [
                        e for e in static["elements"]
                        if e["element_type"] == p["pos_idx"] and e["id"] != p["id"]
                        and (e["now_cost"] / 10) <= estimated_budget
                    ],
                    key=lambda e: float(e.get("form") or 0),
                    reverse=True,
                )[:3]
                
                with st.container():
                    st.warning(f"**{p['name']}** — {reason}{news}")
                    st.caption(f"Estimated Available Budget: **£{estimated_budget:.1f}m** *(Assumes £{estimated_sell_price:.1f}m sell price + £{bank:.1f}m bank)*")
                    
                    if alternatives:
                        st.table([
                            {"Alternative": a["web_name"], "Team": teams.get(a["team"], "?"),
                             "Price": f"£{a['now_cost']/10:.1f}m", "Form": a.get("form")}
                            for a in alternatives
                        ])
            
            st.caption("ℹ️ *Note: Public FPL data does not show exact purchase prices. Selling price is conservatively estimated by applying a £0.1m safety buffer.*")

        # --- 5. Chip tracker ---
        st.markdown("### 🃏 Chip tracker")
        used_chips = (history or {}).get("chips", [])
        if used_chips:
            chip_line = "  ".join(f"`{CHIP_LABELS.get(c['name'], c['name'])} — GW{c['event']}`" for c in used_chips)
            st.markdown(chip_line)
        used_keys = {c["name"] for c in used_chips}
        remaining = [label for key, label in CHIP_LABELS.items() if key not in used_keys]
        st.caption(f"Not yet used: {', '.join(remaining) if remaining else 'none — all chips played'}")

        # --- 6. Rival comparison ---
        if league_id and league_id.strip().isdigit():
            st.markdown("### 🏆 League standing")
            standings = fetch_standings(league_id, 1)
            if standings and "standings" in standings:
                results = standings["standings"].get("results", [])
                me = next((r for r in results if str(r["entry"]) == str(team_id)), None)
                avg_points = sum(r["total"] for r in results) / len(results) if results else 0
                if me:
                    c1, c2, c3 = st.columns(3)
                    c1.metric("Your rank", f"#{me['rank']}")
                    c2.metric("Your points", me["total"])
                    c3.metric("League avg", f"{avg_points:.0f}")
                    diff = me["total"] - avg_points
                    if diff >= 0:
                        st.info(f"You're {abs(diff):.0f} points above your league average (first page)")
                    else:
                        st.warning(f"You're {abs(diff):.0f} points below your league average (first page)")
                else:
                    st.warning("Your team wasn't found on the first page of that league's standings.")

        # --- 7. Squad rating ---
        st.markdown("### 📊 Squad rating")
        bench_value = sum(p["price"] for p in bench)
        score = 10.0
        warnings = []
        if bench_value > 19.0:
            score -= 1.5
            warnings.append("⚠️ **High bench value:** Too much money tied up on substitutes.")
        bench_gk = next((p for p in bench if p["pos"] == "GK"), None)
        if bench_gk and bench_gk["price"] > 4.0:
            score -= 1.0
            warnings.append("⚠️ **Expensive reserve GK:** Consider a £4.0m enabler.")
        if current_captain and current_captain["price"] < 8.0:
            score -= 1.0
            warnings.append("⚠️ **Differential captain:** Armband on a non-premium player.")
        score = max(score, 1.0)
        st.markdown(f"**Rating: {score:.1f} / 10**")
        if warnings:
            for w in warnings:
                st.markdown(w)
        else:
            st.success("✅ Solid squad balance.")

        # --- Squad tables ---
        st.markdown("### Starting XI")
        st.dataframe(
            [{"Pos": p["pos"], "Name": p["name"] + (" (C)" if p["captain"] else "") + (" (V)" if p["vice"] else ""),
              "Team": p["team_short"], "Price": f"£{p['price']:.1f}m"} for p in starters],
            use_container_width=True, hide_index=True
        )
        st.markdown("### Bench")
        st.dataframe(
            [{"Pos": p["pos"], "Name": p["name"], "Team": p["team_short"], "Price": f"£{p['price']:.1f}m"} for p in bench],
            use_container_width=True, hide_index=True
        )
