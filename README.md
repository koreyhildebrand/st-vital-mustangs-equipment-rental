# St. Vital Mustangs Equipment Rental Manager (Standalone App)

**Brand new dedicated Streamlit app** for managing football equipment rentals, checkouts, returns, and private rentals.  
Built as a focused, self-contained application using **only one Google Sheet** (Equipment + Users tabs).  
Based on the logic and UI patterns from your original `Equipment.py` but cleaned up, modernized, and stripped of dependencies on the full registration/roles/players system.

---

## 🚀 High-Level Overview

- **Single Google Sheet** with two tabs: `Equipment` (all rental data) and `Users` (login accounts)
- Full **authentication** via `streamlit-authenticator` (secure hashed passwords)
- **Private Rental** player creation (for quick add without main registration)
- **Rental/Return** workflow with detailed per-player expander forms
- **Current Rentals Dashboard** with live totals, by-team breakdown, and detailed list
- **Security-first design**: Service account limited to one sheet, secrets in Streamlit Cloud only, strong cookies, `.gitignore`
- Deployable to **Streamlit Community Cloud** (free) or your own server

---

## Step-by-Step Instructions

### 1. Create the New Google Sheet (Recommended Structure)

1. Go to [sheets.google.com](https://sheets.google.com) → **Blank spreadsheet**
2. Rename it to: `StVitalMustangs_Equipment_Rentals`
3. **Create / rename the first tab to exactly `Equipment`**
4. In row 1, add these **exact column headers** (copy-paste ready).  
   **Note:** `Team Assignment` and `Return_Date` were added for filtering and the return workflow. You can remove them later if desired.
