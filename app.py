"""
St. Vital Mustangs Equipment Rental Manager
Standalone Streamlit app - Equipment focused only
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

st.set_page_config(page_title=TITLE, layout="wide", page_icon=PAGE_ICON)
st.title(f"🛡️ {TITLE}")

st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

if "page" not in st.session_state:
    st.session_state.page = "Rental"

# ====================== INITIALIZATION ======================
def init_services():
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds_dict = st.secrets["gcp_service_account"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        client = gspread.authorize(creds)

        if SPREADSHEET_KEY:
            sheet = client.open_by_key(SPREADSHEET_KEY)
        else:
            sheet = client.open("StVitalMustangs_Equipment_Rentals")

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

    df = df.astype(object)

    required_cols = [
        "PlayerID", "First Name", "Last Name", "Rental Date", "Phone", "Email",
        "Team Assignment",
        "Helmet_Taken", "Helmet_Size", "Helmet_Type", "Helmet_Date",
        "Shoulder_Taken", "Shoulder_Make", "Shoulder_Size",
        "Pants_Taken", "Pant_Size",
        "Game_Jersey_No", "Practice_Jersey_Color",
        "Kneepads_Taken", "Thighpads_Taken", "Hippads_Taken", "Tailbone_Taken", "Belt_Taken",
        "Return_Date"
    ]

    for col in required_cols:
        if col not in df.columns:
            df[col] = False if col.endswith("_Taken") else ""

    df = df.astype(object)
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

# ====================== AUTH ======================
authenticator.login(location="main")

if st.session_state.get("authentication_status") is True:
    name = st.session_state.name

    st.sidebar.success(f"👤 {name}")
    st.sidebar.caption(f"v{VERSION}")

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

        if st.button("🔄 Refresh", type="primary", width="stretch"):
            st.cache_data.clear()
            st.rerun()

        teams = ["All Teams"] + sorted(equip_df.get("Team Assignment", pd.Series()).dropna().unique().tolist())
        selected_team = st.selectbox("Filter by Team", teams)
        search = st.text_input("🔍 Search")

        roster = equip_df.copy()
        if selected_team != "All Teams":
            roster = roster[roster["Team Assignment"] == selected_team]
        if search:
            roster = roster[roster.apply(lambda r: search.lower() in str(r.values).lower(), axis=1)]

        for idx, player in roster.iterrows():
            first = str(player.get("First Name", ""))
            last = str(player.get("Last Name", ""))
            team = player.get("Team Assignment", "—")

            summary_parts = []
            for col, label in [("Helmet_Taken", "Helmet"), ("Shoulder_Taken", "Shoulder"),
                               ("Pants_Taken", "Pants"), ("Kneepads_Taken", "Kneepads"),
                               ("Thighpads_Taken", "Thighpads"), ("Hippads_Taken", "Hippads"),
                               ("Tailbone_Taken", "Tailbone"), ("Belt_Taken", "Belt")]:
                if to_bool(player.get(col)):
                    summary_parts.append(label)
            if player.get("Practice_Jersey_Color"):
                summary_parts.append(f"Practice {player.get('Practice_Jersey_Color')}")

            current = " | ".join(summary_parts) if summary_parts else "No equipment"
            return_date = str(player.get("Return_Date", "")).strip()
            status = "🔄 Rented" if summary_parts and not return_date else "✅ Available"

            with st.expander(f"**{first} {last}** — {team} | {status} | {current}"):

                # ========== HELMET ==========
                h_taken = st.checkbox("Helmet Taken", value=to_bool(player.get("Helmet_Taken")), key=f"helm_taken_{idx}")
                if h_taken:
                    h_size = st.selectbox("Helmet Size", ["","XS","S","M","L","XL","XXL"],
                                          index=safe_select_index(["","XS","S","M","L","XL","XXL"], player.get("Helmet_Size")),
                                          key=f"helm_size_{idx}")
                    h_type = st.text_input("Helmet Type", value=str(player.get("Helmet_Type", "")),
                                           key=f"helm_type_{idx}")
                    h_date = st.text_input("Helmet Made Date", value=str(player.get("Helmet_Date", "")),
                                           key=f"helm_date_{idx}")
                else:
                    h_size = h_type = h_date = ""

                # ========== SHOULDER PADS ==========
                s_taken = st.checkbox("Shoulder Pads Taken", value=to_bool(player.get("Shoulder_Taken")), key=f"shoul_taken_{idx}")
                if s_taken:
                    s_size = st.selectbox("Shoulder Size", ["","XS","S","M","L","XL","XXL"],
                                          index=safe_select_index(["","XS","S","M","L","XL","XXL"], player.get("Shoulder_Size")),
                                          key=f"shoul_size_{idx}")
                    s_make = st.text_input("Shoulder Make / Brand", value=str(player.get("Shoulder_Make", "")),
                                           key=f"shoul_make_{idx}")
                else:
                    s_size = s_make = ""

                # ========== PANTS ==========
                p_taken = st.checkbox("Pants Taken", value=to_bool(player.get("Pants_Taken")), key=f"pants_taken_{idx}")
                if p_taken:
                    p_size = st.selectbox("Pant Size", ["","YXS","YS","YM","YL","YXL","AS","AM","AL"],
                                          index=safe_select_index(["","YXS","YS","YM","YL","YXL","AS","AM","AL"], player.get("Pant_Size")),
                                          key=f"pant_size_{idx}")
                else:
                    p_size = ""

                # ========== OTHER ITEMS ==========
                k_taken = st.checkbox("Kneepads Taken", value=to_bool(player.get("Kneepads_Taken")), key=f"knee_taken_{idx}")
                t_taken = st.checkbox("Thighpads Taken", value=to_bool(player.get("Thighpads_Taken")), key=f"thigh_taken_{idx}")
                hi_taken = st.checkbox("Hippads Taken", value=to_bool(player.get("Hippads_Taken")), key=f"hip_taken_{idx}")
                tail_taken = st.checkbox("Tailbone Taken", value=to_bool(player.get("Tailbone_Taken")), key=f"tail_taken_{idx}")
                b_taken = st.checkbox("Belt Taken", value=to_bool(player.get("Belt_Taken")), key=f"belt_taken_{idx}")

                practice_color = st.selectbox("Practice Jersey Color", ["","Red","Black","White","Other"],
                                              index=safe_select_index(["","Red","Black","White","Other"], player.get("Practice_Jersey_Color")),
                                              key=f"practice_color_{idx}")

                game_jersey = st.text_input("Game Jersey #", value=str(player.get("Game_Jersey_No", "")),
                                            key=f"game_jersey_{idx}")

                if st.button("💾 Save Rental", key=f"save_{idx}", type="primary"):
                    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                    updates = {
                        "Helmet_Taken": h_taken, "Helmet_Size": h_size, "Helmet_Type": h_type, "Helmet_Date": h_date,
                        "Shoulder_Taken": s_taken, "Shoulder_Make": s_make, "Shoulder_Size": s_size,
                        "Pants_Taken": p_taken, "Pant_Size": p_size,
                        "Game_Jersey_No": game_jersey, "Practice_Jersey_Color": practice_color,
                        "Kneepads_Taken": k_taken, "Thighpads_Taken": t_taken,
                        "Hippads_Taken": hi_taken, "Tailbone_Taken": tail_taken, "Belt_Taken": b_taken,
                        "Rental Date": now,
                        "Return_Date": "" if any([h_taken, s_taken, p_taken, k_taken, t_taken, hi_taken, tail_taken, b_taken]) 
                                       else player.get("Return_Date", "")
                    }
                    for k, v in updates.items():
                        equip_df.loc[idx, k] = v

                    save_equipment_df(equip_df)
                    st.success("Rental saved successfully!")
                    st.rerun()

                if any(to_bool(player.get(c)) for c in ["Helmet_Taken","Shoulder_Taken","Pants_Taken","Kneepads_Taken","Thighpads_Taken","Hippads_Taken","Tailbone_Taken","Belt_Taken"]) and not return_date:
                    if st.button("🔄 Return Equipment", key=f"ret_{idx}"):
                        for c in ["Helmet_Taken","Shoulder_Taken","Pants_Taken","Kneepads_Taken","Thighpads_Taken","Hippads_Taken","Tailbone_Taken","Belt_Taken"]:
                            equip_df.loc[idx, c] = False
                        equip_df.loc[idx, "Return_Date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                        save_equipment_df(equip_df)
                        st.success("Equipment returned!")
                        st.rerun()

    # ====================== PRIVATE RENTAL (UPDATED) ======================
    elif st.session_state.page == "Private Rental":
        st.header("➕ Add Private Rental Player")
        st.caption("Fill in the details below and click Create Player. Fields will clear automatically after adding.")

        with st.form("private_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                first = st.text_input("First Name*")
                last = st.text_input("Last Name*")
                email = st.text_input("Email (optional)")
            with c2:
                phone = st.text_input("Phone (optional)")
                team = st.text_input("Team / Group", value="Private Rental")

            submitted = st.form_submit_button("Create Player", type="primary")

            if submitted:
                if first and last:
                    pid = generate_player_id(first, last)
                    new_row = {col: "" for col in equip_df.columns}
                    new_row.update({
                        "PlayerID": pid,
                        "First Name": first.strip(),
                        "Last Name": last.strip(),
                        "Email": email.strip(),
                        "Phone": phone.strip(),
                        "Team Assignment": team.strip() or "Private Rental",
                        "Helmet_Taken": False,
                        "Shoulder_Taken": False,
                        "Pants_Taken": False,
                        "Kneepads_Taken": False,
                        "Thighpads_Taken": False,
                        "Hippads_Taken": False,
                        "Tailbone_Taken": False,
                        "Belt_Taken": False
                    })
                    equip_df = pd.concat([equip_df, pd.DataFrame([new_row])], ignore_index=True)
                    save_equipment_df(equip_df)
                    st.success(f"✅ Player '{first} {last}' added successfully! You can now add another player.")
                else:
                    st.error("First Name and Last Name are required.")

    # ====================== DASHBOARD ======================
    elif st.session_state.page == "All Rentals":
        st.header("📋 Current Rentals Dashboard")
        if st.button("🔄 Refresh"):
            st.cache_data.clear()
            st.rerun()

        taken_cols = ["Helmet_Taken","Shoulder_Taken","Pants_Taken","Kneepads_Taken",
                      "Thighpads_Taken","Hippads_Taken","Tailbone_Taken","Belt_Taken"]
        existing_taken_cols = [col for col in taken_cols if col in equip_df.columns]

        if existing_taken_cols:
            active_mask = (
                equip_df[existing_taken_cols].map(to_bool).any(axis=1) &
                (equip_df["Return_Date"].isna() | (equip_df["Return_Date"].astype(str).str.strip() == ""))
            )
            active_df = equip_df[active_mask].copy()
        else:
            active_df = pd.DataFrame()

        if active_df.empty:
            st.success("No equipment currently rented out.")
        else:
            st.subheader("Total Items Out")
            totals = {c.replace("_Taken", ""): int(active_df[c].map(to_bool).sum()) for c in existing_taken_cols}
            st.dataframe(pd.DataFrame([totals]), hide_index=True)

            st.subheader("By Team")
            if "Team Assignment" in active_df.columns:
                st.dataframe(active_df.groupby("Team Assignment")[existing_taken_cols].apply(lambda x: x.map(to_bool).sum()).reset_index())

            st.subheader("Details")
            display_cols = ["First Name", "Last Name", "Team Assignment", "Rental Date"] + existing_taken_cols
            display = active_df[[c for c in display_cols if c in active_df.columns]].copy()
            for c in existing_taken_cols:
                display[c] = display[c].map(lambda x: "✅" if to_bool(x) else "")
            st.dataframe(display, hide_index=True)

    st.caption(f"St. Vital Mustangs Equipment Manager | {VERSION}")

else:
    if st.session_state.get("authentication_status") is False:
        st.error("Invalid login")
    else:
        st.warning("Please log in")
