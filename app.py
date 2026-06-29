"""
St. Vital Mustangs Equipment Rental Manager
Brand new standalone Streamlit app (Equipment-focused only)
Based on the Equipment.py outline/logic but fully self-contained with its own Google Sheet.

SECURITY NOTES:
- Uses streamlit-authenticator + Google Sheets for Users (passwords hashed)
- Service account JSON stored ONLY in Streamlit Cloud secrets (never in GitHub)
- Use open_by_key + minimal share (Editor on THIS sheet only)
- Strong random COOKIE_KEY in config + secrets
- .gitignore includes .streamlit/secrets.toml and *.json
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

# Hide default multipage nav
st.markdown("""
    <style>
        [data-testid="stSidebarNav"] {display: none !important;}
        .stButton > button[kind="primary"] {background-color: #1E88E5; color: white;}
    </style>
""", unsafe_allow_html=True)

# ====================== SESSION STATE INIT ======================
if "logout" not in st.session_state:
    st.session_state.logout = False
if "page" not in st.session_state:
    st.session_state.page = "Rental"

# ====================== GOOGLE SHEETS + AUTH INITIALIZATION ======================
def init_services():
    """Initialize gspread client and authenticator. 
    Note: No caching decorator because streamlit-authenticator uses widgets internally.
    """
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

        st.session_state.sheet = sheet

        # Build authenticator from Users worksheet
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
        st.session_state.authenticator = authenticator
        st.session_state.client = client
        return authenticator, sheet

    except Exception as e:
        st.error(f"Initialization error: {str(e)}")
        st.stop()
# ====================== HELPER FUNCTIONS ======================
def to_bool(val) -> bool:
    if pd.isna(val) or val == "" or val is None:
        return False
    return str(val).strip().lower() in ["true", "1", "yes", "t", "checked"]

def get_equipment_df() -> pd.DataFrame:
    """Load Equipment worksheet with automatic column creation + 429 retry."""
    ws = st.session_state.sheet.worksheet(EQUIPMENT_WS)
    try:
        records = ws.get_all_records()
        df = pd.DataFrame(records)
    except Exception as e:
        if "429" in str(e):
            time.sleep(8)
            return get_equipment_df()
        st.error(f"Error loading Equipment sheet: {str(e)}")
        return pd.DataFrame()

    # Ensure all required columns exist
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
            if col in ["Helmet_Taken", "Shoulder_Taken", "Pants_Taken",
                       "Kneepads_Taken", "Thighpads_Taken", "Hippads_Taken",
                       "Tailbone_Taken", "Belt_Taken"]:
                df[col] = False
            else:
                df[col] = ""
    return df

def save_equipment_df(df: pd.DataFrame):
    """Write full Equipment dataframe back to sheet."""
    ws = st.session_state.sheet.worksheet(EQUIPMENT_WS)
    ws.update([df.columns.values.tolist()] + df.fillna("").values.tolist())

def generate_player_id(first: str, last: str, birthdate: str = "") -> str:
    b = birthdate or "NOBIRTH"
    return f"{first.strip()}_{last.strip()}_{b}".replace(" ", "_")

def safe_select_index(options: list, current_value: str, default: int = 0) -> int:
    """Safely find index of current_value in options list."""
    if not current_value or pd.isna(current_value):
        return default
    try:
        return options.index(str(current_value).strip())
    except ValueError:
        return default

# ====================== AUTHENTICATION FLOW ======================
authenticator.login(location="main")

if st.session_state.get("authentication_status") is True:
    name = st.session_state.name
    username = st.session_state.username.lower()

    # Sidebar
    st.sidebar.success(f"👤 {name}")
    st.sidebar.caption(f"Equipment Rental Manager • {VERSION}")

    if st.sidebar.button("🚪 Logout", type="secondary"):
        authenticator.logout("main")
        for key in list(st.session_state.keys()):
            if key not in ["authenticator", "sheet", "client"]:
                del st.session_state[key]
        st.rerun()

    st.sidebar.markdown("---")
    st.sidebar.subheader("Navigation")
    if st.sidebar.button("📦 Rental / Return", width="stretch"):
        st.session_state.page = "Rental"
    if st.sidebar.button("➕ Add Private Rental Player", width="stretch"):
        st.session_state.page = "Private Rental"
    if st.sidebar.button("📋 Current Rentals Dashboard", width="stretch"):
        st.session_state.page = "All Rentals"

    # Load data
    equip_df = get_equipment_df()

    # ====================== RENTAL / CHECKOUT PAGE ======================
    if st.session_state.page == "Rental":
        st.header("📦 Equipment Rental / Return")
        st.caption("Select or add a player, then manage their equipment checkout or return.")

        if st.button("🔄 Refresh Data", type="primary", width="stretch"):
            st.cache_data.clear()
            st.rerun()

        # Team filter
        teams = ["All Teams"] + sorted(equip_df["Team Assignment"].dropna().unique().tolist()) if not equip_df.empty else ["All Teams"]
        selected_team = st.selectbox("Filter by Team / Group", teams, key="rental_team")

        search_term = st.text_input("🔍 Search by name or PlayerID", key="rental_search")

        roster = equip_df.copy()
        if selected_team != "All Teams":
            roster = roster[roster["Team Assignment"] == selected_team]
        if search_term:
            roster = roster[roster.apply(lambda r: search_term.lower() in str(r.values).lower(), axis=1)]

        if roster.empty:
            st.info("No players found. Use 'Add Private Rental Player' to create new ones.")
        else:
            st.subheader(f"Players ({len(roster)} shown)")

            for idx, player in roster.iterrows():
                first = str(player.get("First Name", ""))
                last = str(player.get("Last Name", ""))
                team = player.get("Team Assignment", "—")

                # Summary
                summary_parts = []
                taken_map = {
                    "Helmet_Taken": "Helmet",
                    "Shoulder_Taken": "Shoulder",
                    "Pants_Taken": "Pants",
                    "Kneepads_Taken": "Kneepads",
                    "Thighpads_Taken": "Thighpads",
                    "Hippads_Taken": "Hippads",
                    "Tailbone_Taken": "Tailbone",
                    "Belt_Taken": "Belt"
                }
                for col, nice_name in taken_map.items():
                    if to_bool(player.get(col)):
                        summary_parts.append(nice_name + " ✓")
                if player.get("Practice_Jersey_Color"):
                    summary_parts.append(f"Practice {player.get('Practice_Jersey_Color')} ✓")
                current_rented = " | ".join(summary_parts) if summary_parts else "No active rentals"

                return_date = str(player.get("Return_Date", "")).strip()
                status = "🔄 Currently Rented" if summary_parts and not return_date else "✅ Available / Returned"

                expander_title = f"**{first} {last}** — {team} | {status} | {current_rented[:80]}"

                with st.expander(expander_title):
                    if player.get("Rental Date"):
                        st.markdown(f"**Last Rental Date:** {player.get('Rental Date')}")
                    if return_date:
                        st.markdown(f"**Last Return Date:** {return_date}")

                    # Rental form
                    with st.form(key=f"rental_form_{idx}"):
                        st.markdown("### Checkout Equipment")
                        col1, col2 = st.columns(2)

                        with col1:
                            helmet_taken = st.checkbox("Helmet Taken", value=to_bool(player.get("Helmet_Taken")), key=f"helm_{idx}")
                            if helmet_taken:
                                helmet_opts = ["", "XS", "S", "M", "L", "XL", "XXL", "AS", "AM", "AL", "AXL"]
                                helmet_size = st.selectbox("Helmet Size", helmet_opts,
                                                           index=safe_select_index(helmet_opts, str(player.get("Helmet_Size", ""))), key=f"helm_size_{idx}")
                                helmet_date = st.text_input("Helmet Made / Manufacture Date (e.g. 2023, 05/2024)", 
                                                            value=str(player.get("Helmet_Date", "")), 
                                                            key=f"helm_date_{idx}")
                            else:
                                helmet_size = ""
                                helmet_date = str(player.get("Helmet_Date", ""))

                            shoulder_taken = st.checkbox("Shoulder Pads Taken", value=to_bool(player.get("Shoulder_Taken")), key=f"shoul_{idx}")
                            if shoulder_taken:
                                shoulder_opts = ["", "XS", "S", "M", "L", "XL", "XXL"]
                                shoulder_size = st.selectbox("Shoulder Size", shoulder_opts,
                                                             index=safe_select_index(shoulder_opts, str(player.get("Shoulder_Size", ""))), key=f"shoul_size_{idx}")
                                shoulder_make = st.text_input("Shoulder Make / Brand", value=str(player.get("Shoulder_Make", "")), key=f"shoul_make_{idx}")
                            else:
                                shoulder_size = shoulder_make = ""

                            pants_taken = st.checkbox("Pants Taken", value=to_bool(player.get("Pants_Taken")), key=f"pants_{idx}")
                            if pants_taken:
                                pant_opts = ["", "YXS", "YS", "YM", "YL", "YXL", "YXXL", "AS", "AM", "AL", "AXL", "A2XL", "A3XL"]
                                pant_size = st.selectbox("Pant Size", pant_opts,
                                                         index=safe_select_index(pant_opts, str(player.get("Pant_Size", ""))), key=f"pant_size_{idx}")
                            else:
                                pant_size = ""

                            game_jersey = st.text_input("Game Jersey #", value=str(player.get("Game_Jersey_No", "")), key=f"game_jersey_{idx}")

                        with col2:
                            kneepads = st.checkbox("Kneepads Taken", value=to_bool(player.get("Kneepads_Taken")), key=f"knee_{idx}")
                            thighpads = st.checkbox("Thighpads Taken", value=to_bool(player.get("Thighpads_Taken")), key=f"thigh_{idx}")
                            hippads = st.checkbox("Hippads Taken", value=to_bool(player.get("Hippads_Taken")), key=f"hip_{idx}")
                            tailbone = st.checkbox("Tailbone Pad Taken", value=to_bool(player.get("Tailbone_Taken")), key=f"tail_{idx}")
                            belt = st.checkbox("Belt Taken", value=to_bool(player.get("Belt_Taken")), key=f"belt_{idx}")

                            st.markdown("**Practice Jersey**")
                            practice_color_opts = ["", "Red", "Black", "White", "Other"]
                            practice_color = st.selectbox("Practice Jersey Color", practice_color_opts,
                                                          index=safe_select_index(practice_color_opts, str(player.get("Practice_Jersey_Color", ""))), key=f"practice_color_{idx}")

                        submitted = st.form_submit_button("💾 Save Rental / Update Status", type="primary")

                        if submitted:
                            now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                            new_data = {
                                "Helmet_Taken": helmet_taken,
                                "Helmet_Size": helmet_size,
                                "Helmet_Date": helmet_date,
                                "Shoulder_Taken": shoulder_taken,
                                "Shoulder_Make": shoulder_make,
                                "Shoulder_Size": shoulder_size,
                                "Pants_Taken": pants_taken,
                                "Pant_Size": pant_size,
                                "Game_Jersey_No": game_jersey,
                                "Practice_Jersey_Color": practice_color,
                                "Kneepads_Taken": kneepads,
                                "Thighpads_Taken": thighpads,
                                "Hippads_Taken": hippads,
                                "Tailbone_Taken": tailbone,
                                "Belt_Taken": belt,
                                "Rental Date": now_str,
                                "Return_Date": "" if any([helmet_taken, shoulder_taken, pants_taken, kneepads, thighpads, hippads, tailbone, belt]) else player.get("Return_Date", "")
                            }

                            for k, v in new_data.items():
                                equip_df.at[idx, k] = v

                            save_equipment_df(equip_df)
                            st.success(f"✅ Rental status updated for {first} {last}")
                            st.cache_data.clear()
                            time.sleep(0.8)
                            st.rerun()

                    # Return section
                    has_active = any(to_bool(player.get(c)) for c in ["Helmet_Taken", "Shoulder_Taken", "Pants_Taken", "Kneepads_Taken", "Thighpads_Taken", "Hippads_Taken", "Tailbone_Taken", "Belt_Taken"])
                    if has_active and not str(player.get("Return_Date", "")).strip():
                        st.markdown("---")
                        st.subheader("🔄 Return Equipment")
                        with st.form(key=f"return_form_{idx}"):
                            ret_helmet = st.checkbox("Return Helmet", value=True, key=f"ret_h_{idx}") if to_bool(player.get("Helmet_Taken")) else False
                            ret_shoulder = st.checkbox("Return Shoulder", value=True, key=f"ret_s_{idx}") if to_bool(player.get("Shoulder_Taken")) else False
                            ret_pants = st.checkbox("Return Pants", value=True, key=f"ret_p_{idx}") if to_bool(player.get("Pants_Taken")) else False
                            ret_knee = st.checkbox("Return Kneepads", value=True, key=f"ret_k_{idx}") if to_bool(player.get("Kneepads_Taken")) else False
                            ret_thigh = st.checkbox("Return Thighpads", value=True, key=f"ret_th_{idx}") if to_bool(player.get("Thighpads_Taken")) else False
                            ret_hip = st.checkbox("Return Hippads", value=True, key=f"ret_hip_{idx}") if to_bool(player.get("Hippads_Taken")) else False
                            ret_tail = st.checkbox("Return Tailbone", value=True, key=f"ret_t_{idx}") if to_bool(player.get("Tailbone_Taken")) else False
                            ret_belt = st.checkbox("Return Belt", value=True, key=f"ret_b_{idx}") if to_bool(player.get("Belt_Taken")) else False

                            if st.form_submit_button("✅ Confirm Return of Selected Items", type="primary"):
                                if ret_helmet: equip_df.at[idx, "Helmet_Taken"] = False
                                if ret_shoulder: equip_df.at[idx, "Shoulder_Taken"] = False
                                if ret_pants: equip_df.at[idx, "Pants_Taken"] = False
                                if ret_knee: equip_df.at[idx, "Kneepads_Taken"] = False
                                if ret_thigh: equip_df.at[idx, "Thighpads_Taken"] = False
                                if ret_hip: equip_df.at[idx, "Hippads_Taken"] = False
                                if ret_tail: equip_df.at[idx, "Tailbone_Taken"] = False
                                if ret_belt: equip_df.at[idx, "Belt_Taken"] = False

                                equip_df.at[idx, "Return_Date"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                                save_equipment_df(equip_df)
                                st.success(f"✅ Equipment returned for {first} {last}")
                                st.cache_data.clear()
                                time.sleep(0.6)
                                st.rerun()

    # ====================== PRIVATE RENTAL PAGE ======================
    elif st.session_state.page == "Private Rental":
        st.header("➕ Add New Player for Equipment Rental")
        st.info("Use this for players who are **not** in the main registration system or for quick private rentals.")

        with st.form("add_private_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                first = st.text_input("First Name *", key="pr_first")
                last = st.text_input("Last Name *", key="pr_last")
                email = st.text_input("Email (optional)", key="pr_email")
            with c2:
                phone = st.text_input("Phone (optional)", key="pr_phone")
                team = st.text_input("Team / Group (e.g. U12 Mustangs or Private)", value="Private Rental", key="pr_team")

            submitted = st.form_submit_button("Create Player & Add to Equipment List", type="primary")

            if submitted:
                if not first or not last:
                    st.error("First and Last name are required.")
                else:
                    pid = generate_player_id(first, last, "")
                    if not equip_df.empty and pid in equip_df.get("PlayerID", pd.Series()).values:
                        st.warning("A player with similar ID may already exist.")
                    else:
                        new_row = {
                            "PlayerID": pid,
                            "First Name": first.strip(),
                            "Last Name": last.strip(),
                            "Rental Date": "",
                            "Phone": phone.strip(),
                            "Email": email.strip(),
                            "Team Assignment": team.strip() or "Private Rental",
                            "Helmet_Taken": False, "Helmet_Size": "", "Helmet_Date": "",
                            "Shoulder_Taken": False, "Shoulder_Make": "", "Shoulder_Size": "",
                            "Pants_Taken": False, "Pant_Size": "",
                            "Game_Jersey_No": "",
                            "Practice_Jersey_Color": "",
                            "Kneepads_Taken": False, "Thighpads_Taken": False,
                            "Hippads_Taken": False, "Tailbone_Taken": False, "Belt_Taken": False,
                            "Return_Date": ""
                        }
                        equip_df = pd.concat([equip_df, pd.DataFrame([new_row])], ignore_index=True)
                        save_equipment_df(equip_df)
                        st.success(f"✅ Player '{first} {last}' added to Equipment list!")
                        st.cache_data.clear()
                        time.sleep(1)
                        st.rerun()

    # ====================== ALL CURRENT RENTALS DASHBOARD ======================
    elif st.session_state.page == "All Rentals":
        st.header("📋 Current Equipment Rentals Dashboard")
        st.caption("Overview of all equipment currently checked out.")

        if st.button("🔄 Refresh Dashboard", type="primary", width="stretch"):
            st.cache_data.clear()
            st.rerun()

        taken_cols = ["Helmet_Taken", "Shoulder_Taken", "Pants_Taken", "Kneepads_Taken",
                      "Thighpads_Taken", "Hippads_Taken", "Tailbone_Taken", "Belt_Taken"]
        active_mask = (
            equip_df[taken_cols].applymap(to_bool).any(axis=1) &
            (equip_df["Return_Date"].isna() | (equip_df["Return_Date"].astype(str).str.strip() == ""))
        )
        active_df = equip_df[active_mask].copy()

        if active_df.empty:
            st.success("🎉 No equipment is currently rented out!")
        else:
            st.subheader("Total Items Currently Out")
            total_row = {}
            for col in taken_cols:
                total_row[col.replace("_Taken", "")] = int(active_df[col].apply(to_bool).sum() if col in active_df.columns else 0)
            if "Practice_Jersey_Color" in active_df.columns:
                total_row["Practice_Jersey"] = int((active_df["Practice_Jersey_Color"].astype(str).str.strip() != "").sum())
            st.dataframe(pd.DataFrame([total_row]), hide_index=True, use_container_width=True)

            st.subheader("Equipment by Team / Group")
            if "Team Assignment" in active_df.columns:
                team_totals = active_df.groupby("Team Assignment").agg(
                    {col: lambda x: x.apply(to_bool).sum() for col in taken_cols if col in active_df.columns}
                ).reset_index()
                st.dataframe(team_totals, hide_index=True, use_container_width=True)

            st.subheader("Detailed Active Rentals")
            display_cols = ["First Name", "Last Name", "Team Assignment", "Rental Date"] + taken_cols
            display = active_df[[c for c in display_cols if c in active_df.columns]].copy()
            for col in taken_cols:
                if col in display.columns:
                    display[col] = display[col].apply(lambda x: "✅" if to_bool(x) else "")
            if "Practice_Jersey_Color" in display.columns:
                display["Practice_Jersey_Color"] = display["Practice_Jersey_Color"].fillna("")
            display["Player"] = (display.get("First Name", "").astype(str) + " " + display.get("Last Name", "").astype(str)).str.strip()
            display = display.drop(columns=[c for c in ["First Name", "Last Name"] if c in display.columns], errors="ignore")
            st.dataframe(display, hide_index=True, use_container_width=True)

    st.caption(f"✅ St. Vital Mustangs Equipment Rental Manager | {VERSION} | Data source: Google Sheet '{EQUIPMENT_WS}' tab")

else:
    if st.session_state.get("authentication_status") is False:
        st.error("❌ Invalid username or password. Please try again.")
    else:
        st.warning("Please log in with your Equipment Manager credentials.")

    st.info("""
    **First time setup?**
    1. Make sure your Google Sheet has a "Users" tab with at least one row.
    2. After first successful login, you can update the password in the sheet with a hashed version if needed.
    """)
