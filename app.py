import streamlit as st
import pandas as pd
from auction_db import init_db, save_result, clear_results

# ------------------------------------
# DB INIT
# ------------------------------------
init_db()

# ------------------------------------
# CONFIG
# ------------------------------------
TEAM_BUDGET = 10_000_000
TEAMS = ["CSK", "MI", "RCB", "KKR", "SRH", "DC", "RR", "PBKS"]
BID_INCREMENT = 5_000

# ------------------------------------
# Load players
# ------------------------------------
@st.cache_data
def load_players():
    try:
        return pd.read_csv("data/players.csv", encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv("data/players.csv", encoding="latin1")

players = load_players()

# ------------------------------------
# Compatibility patch for rerun
# ------------------------------------
if not hasattr(st, "rerun"):
    st.rerun = st.experimental_rerun

# ------------------------------------
# SESSION STATE INIT
# ------------------------------------
state = st.session_state

# Global session vars
if "auction_status" not in state:
    state.auction_status = "stopped"

if "current_index" not in state:
    state.current_index = 0

if "teams_data" not in state:
    state.teams_data = {
        team: {"players": [], "spent": 0, "budget_left": TEAM_BUDGET} for team in TEAMS
    }

if "used_teams" not in state:
    state.used_teams = []

if "my_team" not in state:
    state.my_team = ""

if "highest_bid" not in state:
    state.highest_bid = 0

if "highest_bidder" not in state:
    state.highest_bidder = None

if "not_interested" not in state:
    state.not_interested = set()

if "unsold" not in state:
    state.unsold = []

# ------------------------------------
# TEAM SELECTION (No login)
# ------------------------------------
if not state.my_team:
    st.title("Select Your Team")
    available_teams = [t for t in TEAMS if t not in state.used_teams] + ["admin"]
    choice = st.selectbox("Choose your team:", available_teams)
    if st.button("Confirm Team"):
        state.my_team = choice
        if choice != "admin":
            state.used_teams.append(choice)
        st.rerun()
    st.stop()

# ------------------------------------
# SIDEBAR
# ------------------------------------
st.sidebar.title(f"🏏 IPL Auction | Team: **{state.my_team}**")

menu = st.sidebar.radio("Menu", ["🏟️ Auction Room", "👥 Squads"])

if state.my_team == "admin":
    st.sidebar.title("⚙️ Admin Controls")
    if st.sidebar.button("▶️ Start"):
        state.auction_status = "running"
    if st.sidebar.button("⏸️ Pause"):
        state.auction_status = "paused"
    if st.sidebar.button("🔄 Reset"):
        state.auction_status = "stopped"
        state.current_index = 0
        state.teams_data = {
            team: {"players": [], "spent": 0, "budget_left": TEAM_BUDGET}
            for team in TEAMS
        }
        state.used_teams = []
        state.my_team = ""
        state.highest_bid = 0
        state.highest_bidder = None
        state.not_interested = set()
        state.unsold = []
        clear_results()
        st.rerun()

# ------------------------------------
# Auction Room
# ------------------------------------
if menu == "🏟️ Auction Room":
    if state.current_index < len(players):
        player = players.iloc[state.current_index]

        if state.highest_bid == 0:
            state.highest_bid = player['BasePrice']
            state.highest_bidder = None
            state.not_interested = set()

        st.header(f"🎯 {player['Name']} ({player['Role']})")
        st.subheader(f"Base: ₹{player['BasePrice']:,}")
        st.success(f"💰 Highest Bid: ₹{state.highest_bid:,} by {state.highest_bidder if state.highest_bidder else 'None'}")

        # Bid actions for team users (not admin)
        if state.my_team in TEAMS:
            my_budget = state.teams_data[state.my_team]['budget_left']
            can_bid = my_budget >= state.highest_bid + BID_INCREMENT
            if can_bid and state.auction_status == "running":
                if st.button(f"Raise +₹{BID_INCREMENT:,}"):
                    state.highest_bid += BID_INCREMENT
                    state.highest_bidder = state.my_team
                    state.not_interested = set()
                    st.rerun()
            elif not can_bid:
                st.warning("❌ Not enough budget.")
            if state.my_team not in state.not_interested and state.auction_status == "running":
                if st.button("🚫 Not Interested"):
                    state.not_interested.add(state.my_team)
                    st.rerun()

        # Auto sell logic
        active_teams = set(TEAMS) - set([state.highest_bidder]) - state.not_interested
        if len(active_teams) == 0 and state.highest_bidder:
            winner = state.highest_bidder
            price = state.highest_bid
            state.teams_data[winner]['players'].append((player['Name'], price))
            state.teams_data[winner]['spent'] += price
            state.teams_data[winner]['budget_left'] -= price
            save_result(winner, player['Name'], price)
            st.success(f"✅ Auto-SOLD to {winner} for ₹{price:,}")
            state.current_index += 1
            state.highest_bid = 0
            state.highest_bidder = None
            state.not_interested = set()
            st.rerun()

        # Admin forced controls
        if state.my_team == "admin" and state.auction_status == "running":
            c1, c2 = st.columns(2)
            with c1:
                if st.button("✅ Force SOLD"):
                    if state.highest_bidder:
                        winner = state.highest_bidder
                        price = state.highest_bid
                        state.teams_data[winner]['players'].append((player['Name'], price))
                        state.teams_data[winner]['spent'] += price
                        state.teams_data[winner]['budget_left'] -= price
                        save_result(winner, player['Name'], price)
                    state.current_index += 1
                    state.highest_bid = 0
                    state.highest_bidder = None
                    state.not_interested = set()
                    st.rerun()
            with c2:
                if st.button("🚫 Mark UNSOLD"):
                    state.unsold.append(player['Name'])
                    save_result("UNSOLD", player['Name'], 0)
                    state.current_index += 1
                    state.highest_bid = 0
                    state.highest_bidder = None
                    state.not_interested = set()
                    st.rerun()

    else:
        st.success("🎉 Auction Done!")

# ------------------------------------
# Squads
# ------------------------------------
elif menu == "👥 Squads":
    st.title("📋 Team Squads")
    for team in TEAMS:
        data = state.teams_data[team]
        st.subheader(f"🏆 {team}")
        st.write(f"💰 Budget Left: ₹{data['budget_left']:,}")
        st.write(f"💸 Spent: ₹{data['spent']:,}")
        if data["players"]:
            df = pd.DataFrame(data["players"], columns=["Player", "Price"])
            st.table(df)
        else:
            st.info("No players yet.")
    st.subheader("🚫 UNSOLD")
    if state.unsold:
        st.table(pd.DataFrame(state.unsold, columns=["Player"]))
    else:
        st.info("No unsold players.")
