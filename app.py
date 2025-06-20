import streamlit as st
# Compatibility patch for Streamlit rerun
if not hasattr(st, "rerun"):
    st.rerun = st.experimental_rerun

import pandas as pd
from auction_db import init_db, save_result, clear_results

# -------------------------------
# DB INIT
# -------------------------------
init_db()

# -------------------------------
# CONFIG
# -------------------------------
TEAM_BUDGET = 10_000_000
TEAMS = [
    "CSK", "MI", "RCB", "KKR",
    "SRH", "DC", "RR", "PBKS"
]
BID_INCREMENT = 5_000  # Bid step

ALLOWED_USERS = TEAMS + ["admin"]  # for login

# -------------------------------
# LOAD PLAYERS CSV
# -------------------------------
@st.cache_data
def load_players():
    try:
        return pd.read_csv("data/players.csv", encoding="utf-8")
    except UnicodeDecodeError:
        return pd.read_csv("data/players.csv", encoding="latin1")

players = load_players()

# -------------------------------
# SESSION STATE INIT
# -------------------------------
if "auction_status" not in st.session_state:
    st.session_state.auction_status = "stopped"

if "current_index" not in st.session_state:
    st.session_state.current_index = 0

if "teams" not in st.session_state:
    st.session_state.teams = {
        team: {"players": [], "spent": 0, "budget_left": TEAM_BUDGET}
        for team in TEAMS
    }

if "unsold" not in st.session_state:
    st.session_state.unsold = []  # Keep unsold players

if "highest_bid" not in st.session_state:
    st.session_state.highest_bid = 0

if "highest_bidder" not in st.session_state:
    st.session_state.highest_bidder = None

# -------------------------------
# LOGIN SYSTEM
# -------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
    st.session_state.username = ""

if not st.session_state.logged_in:
    st.title("🔐 Team Login")
    username = st.text_input("Team Name")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if username in ALLOWED_USERS and password == username:
            st.session_state.logged_in = True
            st.session_state.username = username
            st.success(f"✅ Logged in as **{username}**")
            st.rerun()
        else:
            st.error("❌ Invalid credentials. Hint: Team name = password")

    st.stop()  # prevent rest of app from loading

# -------------------------------
# SIDEBAR NAVIGATION
# -------------------------------
st.sidebar.title(f"🏏 IPL Auction — Logged in as: **{st.session_state.username}**")

menu = st.sidebar.radio(
    "Navigate",
    ["🏟️ Auction Room", "👥 Squads"]
)

# -------------------------------
# ADMIN CONTROLS
# -------------------------------
if st.session_state.username == "admin":
    st.sidebar.title("⚙️ Admin Controls")

    if st.sidebar.button("▶️ Start Auction"):
        st.session_state.auction_status = "running"

    if st.sidebar.button("⏸️ Pause Auction"):
        st.session_state.auction_status = "paused"

    if st.sidebar.button("🔄 Reset Auction"):
        st.session_state.auction_status = "stopped"
        st.session_state.current_index = 0
        st.session_state.teams = {
            team: {"players": [], "spent": 0, "budget_left": TEAM_BUDGET}
            for team in TEAMS
        }
        st.session_state.unsold = []
        st.session_state.highest_bid = 0
        st.session_state.highest_bidder = None
        clear_results()
        st.rerun()

# -------------------------------
# SIDEBAR FILTER
# -------------------------------
st.sidebar.title("🔍 Filter Players")

roles = players["Role"].unique()
selected_role = st.sidebar.selectbox(
    "Show Role",
    ["All"] + list(roles)
)

if selected_role != "All":
    filtered_players = players[players["Role"] == selected_role].reset_index(drop=True)
else:
    filtered_players = players

# -------------------------------
# MAIN AREA: AUCTION ROOM
# -------------------------------
if menu == "🏟️ Auction Room":
    if st.session_state.current_index < len(filtered_players):
        player = filtered_players.iloc[st.session_state.current_index]

        # If new player, set base price
        if st.session_state.highest_bid == 0:
            st.session_state.highest_bid = player['BasePrice']
            st.session_state.highest_bidder = None

        st.title("🏏 IPL Mega Auction Room")
        st.header(f"Player: **{player['Name']}** | Role: {player['Role']}")
        st.subheader(f"Base Price: ₹{player['BasePrice']:,}")

        st.success(
            f"💰 Current Highest Bid: ₹{st.session_state.highest_bid:,} by {st.session_state.highest_bidder if st.session_state.highest_bidder else 'None'}"
        )

        # -------------------------------
        # Only team can raise bid
        # -------------------------------
        if st.session_state.username in TEAMS:
            team = st.session_state.username
            st.write(f"**Your Team:** {team}")
            st.write(f"💰 Your Budget: ₹{st.session_state.teams[team]['budget_left']:,}")

            can_bid = (
                st.session_state.teams[team]['budget_left'] >= st.session_state.highest_bid + BID_INCREMENT
            )
            if can_bid and st.session_state.auction_status == "running":
                if st.button(f"Raise Bid +₹{BID_INCREMENT:,}"):
                    st.session_state.highest_bid += BID_INCREMENT
                    st.session_state.highest_bidder = team
                    st.rerun()
            elif not can_bid:
                st.warning("❌ You don't have enough budget to bid!")

        # -------------------------------
        # Admin: Mark as SOLD or UNSOLD
        # -------------------------------
        if st.session_state.username == "admin" and st.session_state.auction_status == "running":
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Mark as SOLD!"):
                    if st.session_state.highest_bidder:
                        winner = st.session_state.highest_bidder
                        final_price = st.session_state.highest_bid

                        st.success(f"🎉 {winner} won **{player['Name']}** for ₹{final_price:,}")
                        st.session_state.teams[winner]['players'].append((player['Name'], final_price))
                        st.session_state.teams[winner]['spent'] += final_price
                        st.session_state.teams[winner]['budget_left'] -= final_price
                        save_result(winner, player['Name'], final_price)
                    else:
                        st.warning("⚠️ No valid bid to mark as SOLD!")

                    st.session_state.current_index += 1
                    st.session_state.highest_bid = 0
                    st.session_state.highest_bidder = None
                    st.rerun()

            with col2:
                if st.button("🚫 Mark as UNSOLD"):
                    st.warning(f"🚫 **{player['Name']}** marked UNSOLD.")
                    st.session_state.unsold.append(player['Name'])
                    save_result("UNSOLD", player['Name'], 0)
                    st.session_state.current_index += 1
                    st.session_state.highest_bid = 0
                    st.session_state.highest_bidder = None
                    st.rerun()

    else:
        st.success("✅ Auction Completed!")

# -------------------------------
# MAIN AREA: SQUADS
# -------------------------------
elif menu == "👥 Squads":
    st.title("👥 Team Squads Overview")

    for team in TEAMS:
        st.subheader(f"🏆 {team}")
        squad = st.session_state.teams[team]
        st.write(f"💰 Budget Left: ₹{squad['budget_left']:,}")
        st.write(f"💸 Total Spent: ₹{squad['spent']:,}")
        if squad["players"]:
            squad_df = pd.DataFrame(squad["players"], columns=["Player", "Price"])
            st.table(squad_df)
        else:
            st.info("No players yet.")

    st.subheader("🚫 UNSOLD Players")
    if st.session_state.unsold:
        st.table(pd.DataFrame(st.session_state.unsold, columns=["Player"]))
    else:
        st.info("No unsold players.")
