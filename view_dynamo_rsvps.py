import streamlit as st
import boto3
from datetime import datetime
from boto3.dynamodb.types import TypeDeserializer
from dateutil.parser import parse as parse_date

# Page config
st.set_page_config(page_title="Wedding RSVP Viewer", layout="wide")
st.markdown("""
<style>
    /* Force light background and text */
    html, body, [class*="st-"] {
        background-color: #f8f9fa !important;
        color: #212529 !important;
    }

    .guest-card {
        background-color: #ffffff !important;
        border-radius: 12px;
        padding: 2rem;
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }
    .guest-header {
        font-size: 1.6rem;
        font-weight: 700;
        color: #222222;
        margin-bottom: 1.2rem;
    }
    .meal-entry {
        font-size: 1.3rem;
        line-height: 1.8;
        margin-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

st.title("🎉 Wedding RSVP Submissions")

# AWS DynamoDB config from secrets
aws = st.secrets["aws"]
dynamodb = boto3.client(
    'dynamodb',
    region_name=aws["region_name"],
    aws_access_key_id=aws["aws_access_key_id"],
    aws_secret_access_key=aws["aws_secret_access_key"]
)

table_name = 'wedding-api-submissions-prod'
deserializer = TypeDeserializer()

def deserialize_item(item):
    return {k: deserializer.deserialize(v) for k, v in item.items()}

def fetch_submissions():
    response = dynamodb.scan(TableName=table_name)
    items = response.get("Items", [])
    return [deserialize_item(item) for item in items]

submissions = fetch_submissions()

# ✅ Calculate total guests, total children, and weighted count
total_guests_count = 0
total_children_count = 0
weighted_count = 0

for submission in submissions:
    guests = submission.get("Guests", [])
    for guest in guests:
        name = guest.get("Name", "").lower()
        is_child = guest.get("IsChild", 0)
        total_guests_count += 1
        if is_child == 1:
            total_children_count += 1
            weighted_count += 0.5
        else:
            weighted_count += 1

# ✅ Minus 1 adult for Kathryn duplicate
# Adjust only once overall (outside loop) to avoid multiple deductions if multiple entries exist
weighted_count -= 1
total_guests_count -= 1

# ✅ Ensure counts do not go negative accidentally
if weighted_count < 0:
    weighted_count = 0
if total_guests_count < 0:
    total_guests_count = 0

# ✅ Show guest count summary
st.markdown(f"### 🧮 Guest Summary")
st.markdown(f"- **Total Guests (incl. children, adjusted):** {total_guests_count}")
st.markdown(f"- **Total Children:** {total_children_count}")
st.markdown(f"- **Weighted Count (children = 0.5, minus Kathryn):** {weighted_count}")

# Continue with the original rendering logic
if not submissions:
    st.info("No submissions found.")
else:
    for submission in submissions:
        party_id = submission.get("Id", "Unknown")
        guests = submission.get("Guests", [])
        timestamp_raw = submission.get("SubmittedAt", datetime.utcnow().isoformat())
        timestamp = parse_date(timestamp_raw).strftime("%b %d, %Y %H:%M")

        with st.expander(f"🧾 **Party ID:** {party_id}  \n📅 **Submitted:** {timestamp}"):
            for i, guest in enumerate(guests, start=1):
                name = guest.get("Name", "Unknown")
                is_child = "Yes" if guest.get("IsChild", 0) == 1 else "No"
                meal = guest.get("Meal", {})

                with st.container():
                    st.markdown(f"""
                        <div class='guest-card'>
                            <div class='guest-header'>👤 Guest {i}: {name} ({'Child' if is_child == 'Yes' else 'Adult'})</div>
                            <div class='meal-entry' style='color: #111111;'><b style='color: #111111;'>Starter:</b> {meal.get("Starter", "N/A")}</div>
                            <div class='meal-entry' style='color: #111111;'><b style='color: #111111;'>Main:</b> {meal.get("Main", "N/A")}</div>
                            <div class='meal-entry' style='color: #111111;'><b style='color: #111111;'>Dessert:</b> {meal.get("Dessert", "N/A")}</div>
                        </div>
                    """, unsafe_allow_html=True)