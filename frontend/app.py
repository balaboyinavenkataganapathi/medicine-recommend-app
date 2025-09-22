import streamlit as st
import pandas as pd
import requests
import math
import matplotlib.pyplot as plt
from datetime import datetime

# Backend base URL (adjust if running elsewhere)
BACKEND = st.secrets.get("backend_url", "http://127.0.0.1:8000")

# -----------------------------
# Load CSVs locally for UI helper info (not for DB) - same CSV filenames expected in backend folder
# -----------------------------
try:
    df_medicines = pd.read_csv("medicines_realistic.csv")
except Exception:
    df_medicines = pd.DataFrame(columns=["name","composition","side_effects","category"])

try:
    df_symptom_condition = pd.read_csv("symptom_condition_curated.csv")
except Exception:
    df_symptom_condition = pd.DataFrame(columns=["symptoms","possible_condition"])

try:
    df_condition_medicine = pd.read_csv("condition_medicine_realistic.csv")
except Exception:
    df_condition_medicine = pd.DataFrame(columns=["condition","recommended_medicines"])

try:
    df_condition_precautions = pd.read_csv("condition_precautions_realistic.csv")
except Exception:
    df_condition_precautions = pd.DataFrame(columns=["condition","precautions"])

# -----------------------------
# Streamlit page config
# -----------------------------
st.set_page_config(page_title="💊 SymptoMed Pro", layout="wide")

# -----------------------------
# Session state
# -----------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_email" not in st.session_state:
    st.session_state.user_email = ""
if "username" not in st.session_state:
    st.session_state.username = ""

# -----------------------------
# Login / Signup helper functions
# -----------------------------
def login_user(email, password):
    payload = {"email": email, "password": password}
    try:
        r = requests.post(f"{BACKEND}/login", json=payload, timeout=5)
        if r.status_code == 200:
            data = r.json()
            st.session_state.logged_in = True
            st.session_state.user_email = data["email"]
            st.session_state.username = data["username"]
            return True
        return False
    except Exception:
        return False

def register_user(username, email, password):
    payload = {"username": username, "email": email, "password": password}
    try:
        r = requests.post(f"{BACKEND}/register", json=payload, timeout=5)
        return r.status_code == 200
    except Exception:
        return False

# -----------------------------
# Centered Login Page
# -----------------------------
login_css = """
<style>
.centered-container {
    display: flex;
    justify-content: center;
    align-items: center;
    height: 80vh;
}
.centered-box {
    width: 400px;
    padding: 30px;
    border-radius: 15px;
    background: #f9f9f9;
    box-shadow: 0 8px 20px rgba(0,0,0,0.2);
}
</style>
"""

if not st.session_state.logged_in:
    st.markdown(login_css, unsafe_allow_html=True)
    st.title("💊 SymptoMed Pro Login / Signup")

    tab_login, tab_register = st.tabs(["Login", "Signup"])

    with tab_login:
        login_email = st.text_input("Email")
        login_pass = st.text_input("Password", type="password")
        if st.button("Login"):
            if login_user(login_email, login_pass):
                st.success(f"Welcome back, {st.session_state.username}!")
                st.experimental_set_query_params(logged="1")
                st.rerun()
            else:
                st.error("Invalid email or password.")

    with tab_register:
        reg_username = st.text_input("Username")
        reg_email = st.text_input("Email", key="reg_email")
        reg_pass = st.text_input("Password", type="password", key="reg_pass")
        if st.button("Signup"):
            if register_user(reg_username, reg_email, reg_pass):
                st.success("Signup successful! Please login now.")
            else:
                st.error("Email already exists. Use a different email.")

    st.stop()

# -----------------------------
# Custom CSS
# -----------------------------
st.markdown("""
<style>
body {font-family: 'Segoe UI', sans-serif;}
.card {border-radius:15px; padding:20px; margin:10px 5px; transition: transform 0.3s, box-shadow 0.3s; position: relative; font-weight:bold; color:#000000;}
.card:hover { transform: translateY(-5px); box-shadow:0 12px 30px rgba(0,0,0,0.35);}
.mild {background: linear-gradient(120deg,#d4edda,#a8e6a2);}
.moderate {background: linear-gradient(120deg,#fff3cd,#ffe08a);}
.severe {background: linear-gradient(120deg,#f8d7da,#f1a1a8);}
h4 {margin-bottom:10px;}
.severity-badge { display:inline-block; width:16px; height:16px; border-radius:50%; margin-right:5px; }
.glow-alert { border:2px solid #dc3545; padding:15px; border-radius:10px; background-color:#f8d7da; color:#721c24; font-weight:bold; text-align:center; box-shadow:0 0 20px #dc3545; animation:pulse 1.5s infinite; }
@keyframes pulse { 0%{box-shadow:0 0 10px #dc3545;} 50%{box-shadow:0 0 25px #dc3545;} 100%{box-shadow:0 0 10px #dc3545;} }
</style>
""", unsafe_allow_html=True)

# -----------------------------
# Profile + Logout Section
# -----------------------------
with st.sidebar:
    st.markdown(f"### 👤 Profile")
    st.info(f"*Username:* {st.session_state.username}\n\n*Email:* {st.session_state.user_email}")
    if st.button("🚪 Logout"):
        st.session_state.logged_in = False
        st.session_state.user_email = ""
        st.session_state.username = ""
        st.experimental_set_query_params(logged="0")
        st.rerun()

st.markdown(f"<h1 style='text-align:center; color:#2c3e50;'>💊 Welcome {st.session_state.username} </h1>", unsafe_allow_html=True)

# -----------------------------
# Prepare symptoms
# -----------------------------
all_symptoms = df_symptom_condition["symptoms"].dropna().unique().tolist() if not df_symptom_condition.empty else []
common_symptoms = sorted([
    "fever","cold","cough","headache","chest pain","fatigue","sore throat","allergy",
    "nausea","vomiting","diarrhea","stomach pain","dizziness","shortness of breath",
    "rash","joint pain","loss of appetite","anxiety","insomnia","back pain",
    "weight loss","blurred vision","ear pain","runny nose","constipation"
])
severity_colors = {"Mild":"#28a745","Moderate":"#ffc107","Severe":"#dc3545"}

# -----------------------------
# Tabs
# -----------------------------
tab1, tab2 = st.tabs(["🧩 Symptom Explorer", "📚 Medical History & Patterns"])

# -----------------------------
# Tab 1: Recommendations
# -----------------------------
with tab1:
    st.write("Type your symptoms (comma separated) or pick from common symptoms.")
    manual_input = st.text_input("Enter symptoms:", "")
    selected_common = st.multiselect("Pick from common symptoms:", common_symptoms)

    input_symptoms_raw = manual_input
    if selected_common:
        input_symptoms_raw += "," + ",".join(selected_common)
    input_symptoms_raw = input_symptoms_raw.strip(", ")

    severity_level = st.selectbox("Select severity:", ["Mild","Moderate","Severe"])
    duration_days = st.number_input("Duration (days):", min_value=0, max_value=365, value=1)

    if st.button("💊 Recommend Medicines") and input_symptoms_raw:
        payload = {
            "input_symptoms": input_symptoms_raw,
            "severity": severity_level,
            "duration_days": int(duration_days),
            "user_email": st.session_state.user_email
        }
        try:
            r = requests.post(f"{BACKEND}/search", json=payload, timeout=10)
            if r.status_code != 200:
                st.error("Search failed — please try again.")
            else:
                data = r.json()
                matched_conditions = data.get("matched_conditions", [])
                risk_score = data.get("risk_score", 0)
                results = data.get("results", [])

                if matched_conditions:
                    if risk_score > 10:
                        st.markdown("<div class='glow-alert'>⚠ High Risk! Immediate action needed! Consult a doctor immediately.</div>", unsafe_allow_html=True)
                    elif risk_score >= 5:
                        st.warning("⚠ Moderate Risk. Monitor symptoms and consult a doctor if worsens.")
                    else:
                        st.success("✅ Low Risk. Continue monitoring symptoms.")

                    combined_rows = results
                    cols_per_row = 3
                    num_cards = len(combined_rows)
                    num_rows = math.ceil(num_cards/cols_per_row)

                    for row_idx in range(num_rows):
                        row_start = row_idx*cols_per_row
                        row_end = min(row_start+cols_per_row, num_cards)
                        cols = st.columns(row_end-row_start)
                        for col_idx, row in zip(range(row_end-row_start), combined_rows[row_start:row_end]):
                            med_names = row.get("recommended_medicines", [])
                            precautions = row.get("precautions", "No precautions available")
                            severity_class = severity_level.lower()
                            severity_color = severity_colors.get(severity_level, "#6c757d")

                            med_html = ""
                            for med in med_names:
                                med_info = df_medicines[df_medicines["name"] == med]
                                if not med_info.empty:
                                    comp = med_info.iloc[0].get("composition", "")
                                    side = med_info.iloc[0].get("side_effects", "")
                                    med_html += f"<div title='Composition:{comp}, Side Effects:{side}'>{med}</div><br>"
                                else:
                                    med_html += f"{med}<br>"

                            with cols[col_idx]:
                                st.markdown(
                                    f"<div class='card {severity_class}'>"
                                    f"<h4><span class='severity-badge' style='background-color:{severity_color}'></span>{row['condition']}</h4>"
                                    f"<p>Severity:{severity_level} | Duration:{duration_days} days</p>"
                                    f"<b>💊 Medicines:</b><br>{med_html}"
                                    f"<b>⚠ Precautions:</b><br>{precautions}</div>",
                                    unsafe_allow_html=True
                                )

                                if med_names:
                                    if st.button(f"🛒 Purchase {med_names[0]}", key=f"buy_{row['condition']}_{col_idx}"):
                                        pay = {"user_email": st.session_state.user_email, "condition": row['condition'], "medicine": med_names[0]}
                                        pr = requests.post(f"{BACKEND}/purchase", json=pay, timeout=5)
                                        if pr.status_code == 200:
                                            st.success(f"✅ {med_names[0]} purchased successfully!")
                                        else:
                                            st.error("Purchase failed. Try again.")
                else:
                    st.warning("⚠ No matching conditions found.")
        except Exception as e:
            st.error(f"Error contacting backend: {e}")

# -----------------------------
# Tab 2: Analytics + Frequently Purchased
# -----------------------------
with tab2:
    st.subheader("🗂 Personal Health Record")
    try:
        r = requests.get(f"{BACKEND}/history/{st.session_state.user_email}", timeout=8)
        if r.status_code == 200:
            df_hist_json = r.json()
            if df_hist_json:
                df_hist = pd.DataFrame(df_hist_json)
                st.dataframe(df_hist)

                csv_buf = df_hist.to_csv(index=False)
                st.download_button("💾 Download History", csv_buf, "history.csv", "text/csv")

                st.markdown("### 🧬 Health Severity Trendline")
                trend_data = {}
                for _, r2 in df_hist.iterrows():
                    for cond in str(r2['conditions_found']).split(", "):
                        if cond not in trend_data:
                            trend_data[cond] = []
                        trend_data[cond].append({"severity": r2["severity"], "day": int(r2["duration_days"])})

                fig, ax = plt.subplots(figsize=(10, 5))
                color_map = {"Mild": "#28a745", "Moderate": "#ffc107", "Severe": "#dc3545"}
                for cond, vals in trend_data.items():
                    days = [v["day"] for v in vals]
                    sev_numeric = [1 if v["severity"]=="Mild" else 2 if v["severity"]=="Moderate" else 3 for v in vals]
                    ax.plot(days, sev_numeric, marker='o', linestyle='-', label=cond)
                ax.set_yticks([1, 2, 3])
                ax.set_yticklabels(["Mild", "Moderate", "Severe"])
                ax.set_xlabel("Duration (days)")
                ax.set_ylabel("Severity Level")
                ax.set_title("Symptom Severity Trend")
                ax.legend()
                st.pyplot(fig)

                # Frequent purchases
                st.markdown("### 📦 Medicine Purchase Trends by other users")
                r2 = requests.get(f"{BACKEND}/frequent_purchases", timeout=8)
                if r2.status_code == 200:
                    top_purchases = pd.DataFrame(r2.json())
                    if not top_purchases.empty:
                        st.table(top_purchases)
                    else:
                        #st.info("No purchases recorded yet. Showing demo sample:")
                        demo_data = pd.DataFrame([
                            {"condition": "Fever", "medicine": "Paracetamol", "freq": 12},
                            {"condition": "Diabetes", "medicine": "Metformin", "freq": 8},
                            {"condition": "Hypertension", "medicine": "Amlodipine", "freq": 5},
                            {"condition": "Asthma", "medicine": "Salbutamol Inhaler", "freq": 4},
                        ])
                        st.table(demo_data)
                else:
                    st.error("Could not fetch frequent purchases from backend.")
    except Exception as e:
        st.error(f"Error contacting backend: {e}")
