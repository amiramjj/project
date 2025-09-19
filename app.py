import streamlit as st
import pandas as pd
#------------------------------
# Page Config: Full Width Layout
# -------------------------------
st.set_page_config(layout="wide")

# -------------------------------
# Streamlit App for Matching Score
# -------------------------------



# ---- 1. Define weights ----
w = {
    # Requirements
    "household": 0.8,
    "special_cases": 0.8,
    "pets": 0.7,
    "dayoff": 0.7,
    "living": 0.7,
    "nationality": 0.5,
    "cuisine": 0.4,

    # Penalties
    "smoking": 0.4,
    "attitude": 0.4,
}

# ---- 2. Import the scoring function ----
from scoring_function import blueprint_score  # <-- save your function in scoring_function.py, or paste it here

# ---- 3. Streamlit Layout ----
st.set_page_config(layout="wide")  # use full width

st.title("🧾 Client–Maid Matching Score Dashboard")

# ---- 4. File upload ----
uploaded_file = st.file_uploader("Upload your dataset (CSV or Excel)", type=["csv", "xlsx"])
if uploaded_file is not None:
    # Load dataset
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.success(f"Loaded dataset with {len(df)} rows.")

    # ---- 5. Apply scoring ----
    results = df.apply(lambda row: blueprint_score(row, w), axis=1)
    df_results = pd.concat([df[["client_name", "maid_id"]], results], axis=1)

    # ---- 6. Display main table (just final scores) ----
    st.subheader("📊 Final Scores Overview")
    st.dataframe(df_results[["client_name", "maid_id", "final_score"]].head(30))

    # ---- 7. Interactive details ----
    st.subheader("🔍 Inspect Match Details")
    selected_row = st.selectbox("Select a client-maid pair:", df_results.index)

    if selected_row is not None:
        row = df_results.loc[selected_row]

        st.markdown(f"### Client: `{row['client_name']}` | Maid: `{row['maid_id']}`")
        st.metric("Final Score", f"{row['final_score']}%")

        with st.expander("✅ Requirements Met"):
            st.write(row["requirements"] if row["requirements"] else "None")

        with st.expander("❌ Penalties"):
            st.write(row["penalties"] if row["penalties"] else "None")

        with st.expander("🎁 Bonuses"):
            st.write(row["bonuses"] if row["bonuses"] else "None")

        with st.expander("ℹ️ Not Specified"):
            st.write(row["not_specified"] if row["not_specified"] else "None")
