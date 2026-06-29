"""Configuration for St. Vital Mustangs Equipment Rental App.
SECURITY: Never commit real secrets or service account JSON to GitHub.
"""

VERSION = "v1.0-equipment-only"
PAGE_ICON = "🛡️"
TITLE = "St. Vital Mustangs - Equipment Rental Manager"

# Cookie settings for streamlit-authenticator (use a LONG random string)
COOKIE_NAME = "stvital_equipment_rental"

# IMPORTANT: Change this to a new long random string for production!
COOKIE_KEY = "EqU1pM3ntR3nt4l_2026_S3cur3_R4nd0m_K3y_X7pQ9mN2vB5tY8wZ3kL6jH4gF1dS0aP7oI9uY2rT5eW8xC3vN6bM1qA4sD7fG9hJ2kL5pO8iU3yX6z"

COOKIE_EXPIRY_DAYS = 30

# Google Sheet settings
# Recommended: Use SPREADSHEET_KEY (get it from your sheet URL between /d/ and /edit)
SPREADSHEET_KEY = ""          # ← Fill this in later in Streamlit secrets
EQUIPMENT_WS = "Equipment"
USERS_WS = "Users"