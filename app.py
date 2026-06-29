"""
St. Vital Mustangs Equipment Rental Manager
Standalone Streamlit app for equipment rentals only.
"""

import streamlit as st
import pandas as pd
import datetime
import time
from google.oauth2.service_account import Credentials
import gspread
import streamlit_authenticator as stauth
from config import (
    VERSION, PAGE_ICON, TITLE, COOKIE_NAME, COOKIE_KEY, COOKIE_EXPIRY_DAYS,
    SPREADSHEET_KEY, EQUIPMENT_WS, USERS_WS
)

# ====================== PAGE CONFIG & STYLING ======================
st.set_page_config(page_title=TITLE, layout="wide", page_icon=PAGE_ICON)
st.title(f"🛡️ {TITLE}")

st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none !important;}
        .stButton > button[kind="primary"] {background-color: #1E88E5; color: white;}
    </style>
""", unsafe_allow_html=True)

# ====================== SESSION STATE ======================
if "page" not in st.session_state:
    st.session_state.page = "Rental"

# ====================== INITIALIZATION ======================
def init_services():
    """Initialize Google Sheets + Authenticator (no caching to avoid widget conflict)."""
    try:
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)

        if SPREADSHEET_KEY:
            sheet = client.open_by_key(SPREADSHEET_KEY)
        else:
            sheet = client.open("StVitalMustangs_Equipment_Rentals")

        # Users sheet for authentication
        users_ws = sheet.worksheet(USERS_WS)
        user_data = users_ws.get_all_records()

        credentials = {"usernames": {}}
        for user in user_data:
            uname = str(user.get("username", "")).strip().lower()
            if uname:
                credentials["usernames"][uname] = {
                    "name": user.get("name", uname),
                    "email": user.get("email", ""),
                    "password": user.get("password", ""),
                }

        authenticator = stauth.Authenticate(
            credentials=credentials,
            cookie_name=COOKIE_NAME,
            key=COOKIE_KEY,
            cookie_expiry_days=COOKIE_EXPIRY_DAYS,
        )

        st.session_state.sheet = sheet
        st.session_state.authenticator = authenticator
        st.session_state.client = client

        return authenticator, sheet

    except Exception as e:
        st.error(f"Setup error: {str(e)}")
        st.stop()


authenticator, sheet = init_services()

# ====================== HELPER FUNCTIONS ======================
def to_bool(val) -> bool:
    if pd.isna(val) or val == "" or val is None:
        return False
    return str(val).strip().lower() in ["true", "1", "yes", "t"]

def get_equipment_df() -> pd.DataFrame:
    ws = st.session_state.sheet.worksheet(EQUIPMENT_WS)
    try:
        df = pd.DataFrame(ws.get_all_records())
    except Exception as e:
        if "429" in str(e):
            time.sleep(8)
            return get_equipment_df()
        st.error(f"Error loading Equipment: {str(e)}")
        return pd.DataFrame()

    required_cols = [
        "PlayerID", "First Name", "Last Name", "Rental Date", "Phone", "Email",
        "Team Assignment",
        "Helmet_Taken", "Helmet_Size", "Helmet_Date",
        "Shoulder_Taken", "Shoulder_Make", "Shoulder_Size",
        "Pants_Taken", "Pant_Size",
        "Game_Jersey_No", "Practice_Jersey_Color",
        "Kneepads_Taken", "Thighpads_Taken", "Hippads_Taken", "Tailbone_Taken", "Belt_Taken",
        "Return_Date"
    ]
    for col in required_cols:
        if col not in df.columns:
            df[col] = False if col.endswith("_Taken") else ""
    return df

def save_equipment_df(df: pd.DataFrame):
    ws = st.session_state.sheet.worksheet(EQUIPMENT_WS)
    ws.update([df.columns.values.tolist()] + df.fillna("").values.tolist())

def generate_player_id(first: str, last: str) -> str:
    return f"{first.strip()}_{last.strip()}"

def safe_select_index(options, current_value, default=0):
    try:
        return options.index(str(current_value).strip())
    except:
        return default

# ====================== AUTHENTICATION ======================
authenticator.login(location="main")

if st.session_state.get("authentication_status") is True:
    name = st.session_state.name

    # Sidebar
    st.sidebar.success(f"👤 {name}")
    st.sidebar.caption(f"Equipment Rental Manager • {VERSION}")

    if st.sidebar.button("🚪 Logout", type="secondary"):
        authenticator.logout("main")
        st.rerun()

    st.sidebar.markdown("---")
    if st.sidebar.button("📦 Rental / Return", width="stretch"):
        st.session_state.page = "Rental"
    if st.sidebar.button("➕ Add Private Rental Player", width="stretch"):
        st.session_state.page = "Private Rental"
    if st.sidebar.button("📋 Current Rentals Dashboard", width="stretch"):
        st.session_state.page = "All Rentals"

    equip_df = get_equipment_df()

    # ====================== RENTAL PAGE ======================
    if st.session_state.page == "Rental":
        st.header("📦 Equipment Rental / Return")

        if st.button("🔄 Refresh Data", type="primary", width="stretch"):
            st.cache_data.clear()
            st.rerun()

        teams = ["All Teams"] + sorted(equip_df.get("Team Assignment", pd.Series()).dropna().unique().tolist())
        selected_team = st.selectbox("Filter by Team", teams)

        search = st.text_input("🔍 Search player")

        roster = equip_df.copy()
        if selected_team != "All Teams":
            roster = roster[roster["Team Assignment"] == selected_team]
        if search:
            roster = roster[roster.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]

        for idx, player in roster.iterrows():
            first = str(player.get("First Name", ""))
            last = str(player.get("Last Name", ""))
            team = player.get("Team Assignment", "—")

            summary = []
            for col, label in [("Helmet_Taken","Helmet"), ("Shoulder_Taken","Shoulder"), 
                               ("Pants_Taken","Pants"), ("Kneepads_Taken","Kneepads"),
                               ("Thighpads_Taken","Thighpads"), ("Hippads_Taken","Hippads"),
                               ("Tailbone_Taken","Tailbone"), ("Belt_Taken","Belt")]:
                if to_bool(player.get(col)):
                    summary.append(label)
            if player.get("Practice_Jersey_Color"):
                summary.append(f"Practice {player.get('Practice_Jersey_Color')}")

            current_rented = " | ".join(summary) if summary else "No equipment rented"
            return_date = str(player.get("Return_Date", "")).strip()
            status = "🔄 Rented" if summary and not return_date else "✅ Available"

            with st.expander(f"**{first} {last}** — {team} | {status} | {current_rented}"):
                with st.form(key=f"rental_{idx}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        h_taken = st.checkbox("Helmet Taken", value=to_bool(player.get("Helmet_Taken")))
                        if h_taken:
                            h_size = st.selectbox("Helmet Size", ["","XS","S","M","L","XL","XXL"], 
                                                  index=safe_select_index(["","XS","S","M","L","XL","XXL"], player.get("Helmet_Size")))
                            h_date = st.text_input("Helmet Made Date", value=str(player.get("Helmet_Date", "")))
                        else:
                            h_size, h_date = "", str(player.get("Helmet_Date", ""))

                        s_taken = st.checkbox("Shoulder Taken", value=to_bool(player.get("Shoulder_Taken")))
                        if s_taken:
                            s_size = st.selectbox("Shoulder Size", ["","XS","S","M","L","XL","XXL"],
                                                  index=safe_select_index(["","XS","S","M","L","XL","XXL"], player.get("Shoulder_Size")))
                            s_make = st.text_input("Shoulder Make", value=str(player.get("Shoulder_Make", "")))
                        else:
                            s_size, s_make = "", ""

                        p_taken = st.checkbox("Pants Taken", value=to_bool(player.get("Pants_Taken")))
                        if p_taken:
                            p_size = st.selectbox("Pant Size", ["","YXS","YS","YM","YL","YXL","AS","AM","AL"],
                                                  index=safe_select_index(["","YXS","YS","YM","YL","YXL","AS","AM","AL"], player.get("Pant_Size")))
                        else:
                            p_size = ""

                        game_jersey = st.text_input("Game Jersey #", value=str(player.get("Game_Jersey_No", "")))

                    with col2:
                        k_taken = st.checkbox("Kneepads Taken", value=to_bool(player.get("Kneepads_Taken")))
                        t_taken = st.checkbox("Thighpads Taken", value=to_bool(player.get("Thighpads_Taken")))
                        hi_taken = st.checkbox("Hippads Taken", value=to_bool(player.get("Hippads_Taken")))
                        tail_taken = st.checkbox("Tailbone Taken", value=to_bool(player.get("Tailbone_Taken")))
                        b_taken = st.checkbox("Belt Taken", value=to_bool(player.get("Belt_Taken")))

                        practice_color = st.selectbox("Practice Jersey Color", ["","Red","Black","White","Other"],
                                                      index=safe_select_index(["","Red","Black","White","Other"], player.get("Practice_Jersey_Color")))

                    if st.form_submit_button("💾 Save Rental"):
                        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        updates = {
                            "Helmet_Taken": h_taken, "Helmet_Size": h_size, "Helmet_Date": h_date,
                            "Shoulder_Taken": s_taken, "Shoulder_Make": s_make, "Shoulder_Size": s_size,
                            "Pants_Taken": p_taken, "Pant_Size": p_size,
                            "Game_Jersey_No": game_jersey,
                            "Practice_Jersey_Color": practice_color,
                            "Kneepads_Taken": k_taken, "Thighpads_Taken": t_taken,
                            "Hippads_Taken": hi_taken, "Tailbone_Taken": tail_taken, "Belt_Taken": b_taken,
                            "Rental Date": now,
                            "Return_Date": "" if any([h_taken, s_taken, p_taken, k_taken, t_taken, hi_taken, tail_taken, b_taken]) else player.get("Return_Date", "")
                        }
                        for k, v in updates.items():
                            equip_df.at[idx, k] = v
                        save_equipment_df(equip_df)
                        st.success("Saved!")
                        st.rerun()

                # Return section
                if any(to_bool(player.get(c)) for c in ["Helmet_Taken","Shoulder_Taken","Pants_Taken","Kneepads_Taken","Thighpads_Taken","Hippads_Taken","Tailbone_Taken","Belt_Taken"]) and not return_date:
                    st.markdown("---")
                    if st.button("🔄 Return All Equipment", key=f"return_{idx}"):
                        for c in ["Helmet_Taken","Shoulder_Taken","Pants_Taken","Kneepads_Taken","Thighpads_Taken","Hippads_Taken","Tailbone_Taken","Belt_Taken"]:
                            equip_df.at[idx, c] = False
                        equip_df.at[idx, "Return_Date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        save_equipment_df(equip_df)
                        st.success("Equipment returned!")
                        st.rerun()

    # ====================== PRIVATE RENTAL ======================
    elif st.session_state.page == "Private Rental":
        st.header("➕ Add Private Rental Player")
        with st.form("private_form"):
            c1, c2 = st.columns(2)
            with c1:
                first = st.text_input("First Name*")
                last = st.text_input("Last Name*")
                email = st.text_input("Email")
            with c2:
                phone = st.text_input("Phone")
                team = st.text_input("Team / Group", value="Private Rental")

            if st.form_submit_button("Create Player"):
                if first and last:
                    pid = generate_player_id(first, last)
                    new_row = {col: "" for col in equip_df.columns}
                    new_row.update({
                        "PlayerID": pid, "First Name": first, "Last Name": last,
                        "Email": email, "Phone": phone, "Team Assignment": team,
                        "Helmet_Taken": False, "Shoulder_Taken": False, "Pants_Taken": False,
                        "Kneepads_Taken": False, "Thighpads_Taken": False, "Hippads_Taken": False,
                        "Tailbone_Taken": False, "Belt_Taken": False
                    })
                    equip_df = pd.concat([equip_df, pd.DataFrame([new_row])], ignore_index=True)
                    save_equipment_df(equip_df)
                    st.success("Player added!")
                    st.rerun()

    # ====================== DASHBOARD ======================
    elif st.session_state.page == "All Rentals":
        st.header("📋 Current Rentals Dashboard")
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()

        taken_cols = ["Helmet_Taken","Shoulder_Taken","Pants_Taken","Kneepads_Taken",
                      "Thighpads_Taken","Hippads_Taken","Tailbone_Taken","Belt_Taken"]
        active = equip_df[
            (equip_df[taken_cols].applymap(to_bool).any(axis=1)) &
            (equip_df["Return_Date"].isna() | (equip_df["Return_Date"].astype(str).str.strip() == ""))
        ]

        if active.empty:
            st.success("No equipment currently rented out.")
        else:
            st.subheader("Items Currently Out")
            totals = {c.replace("_Taken",""): int(active[c].apply(to_bool).sum()) for c in taken_cols}
            st.dataframe(pd.DataFrame([totals]), hide_index=True)

            st.subheader("By Team")
            if "Team Assignment" in active.columns:
                st.dataframe(active.groupby("Team Assignment")[taken_cols].apply(lambda x: x.apply(to_bool).sum()).reset_index())

            st.subheader("Details")
            display = active[["First Name","Last Name","Team Assignment","Rental Date"] + taken_cols].copy()
            for c in taken_cols:
                display[c] = display[c].apply(lambda x: "✅" if to_bool(x) else "")
            st.dataframe(display, hide_index=True)

    st.caption(f"St. Vital Mustangs Equipment Manager | {VERSION}")

else:
    if st.session_state.get("authentication_status") is False:
        st.error("Invalid username or password")
    else:
        st.warning("Please log in")
