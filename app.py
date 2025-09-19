import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------------
# Page Config: Full Width Layout
# -------------------------------
st.set_page_config(layout="wide")

# -------------------------------
# Blueprint Scoring Function
# -------------------------------
def blueprint_score(row, w):
    requirement_score = 0.0
    requirement_max = 0.0
    penalties = 0.0

    req_explanations, pen_explanations = [], []
    bonus_explanations, neutral_explanations = [], []

    # Household type
    c_house = row.get("clientmts_household_type", "unspecified")
    m_house = row.get("maidmts_household_type", "unspecified")
    if c_house != "unspecified":
        requirement_max += w["household"]
        if (c_house == "baby" and m_house != "refuses_baby") or \
           (c_house == "many_kids" and m_house != "refuses_many_kids") or \
           (c_house == "baby_and_kids" and m_house != "refuses_baby_and_kids"):
            requirement_score += w["household"]
            req_explanations.append(f"Client wants {c_house}, maid accepts.")
        else:
            penalties += w["household"]
            pen_explanations.append(f"Client wants {c_house}, but maid refuses.")
    else:
        neutral_explanations.append("Client did not specify household type.")

    # ... (rest of requirement / penalties / bonuses same as before)
    # Attitude handling:
    maid_personality = str(row.get("maidpref_personality", ""))
    if "attitude" in maid_personality and "no_attitude" not in maid_personality:
        penalties += w["attitude"]
        pen_explanations.append("Maid shows negative attitude (penalty).")
    elif "no_attitude" in maid_personality:
        bonus_explanations.append("Maid does not have attitude (bonus).")

    # Bonuses
    if row.get("maidpref_smoking") == "non_smoker":
        bonus_explanations.append("Non-smoker")

    # Final score
    requirement_pct = (requirement_score / requirement_max * 100) if requirement_max > 0 else 0
    final_score = max(0, requirement_pct - penalties * 100)

    return pd.Series({
        "final_score": final_score,
        "requirements": "; ".join(req_explanations),
        "penalties": "; ".join(pen_explanations),
        "bonuses": ", ".join(bonus_explanations),
        "not_specified": "; ".join(neutral_explanations)
    })


# -------------------------------
# Streamlit App
# -------------------------------
st.title("Client–Maid Matching Score (Interactive)")

# Sidebar weights
st.sidebar.header("⚖️ Adjust Weights")
weights = {
    "household": st.sidebar.slider("Household Type", 0.0, 1.0, 0.7, 0.1),
    "special_cases": st.sidebar.slider("Special Cases (Elderly / Special Needs)", 0.0, 1.0, 0.7, 0.1),
    "dayoff": st.sidebar.slider("Day-Off Policy", 0.0, 1.0, 0.6, 0.1),
    "living": st.sidebar.slider("Living Arrangement", 0.0, 1.0, 0.6, 0.1),
    "pets": st.sidebar.slider("Pets", 0.0, 1.0, 0.6, 0.1),
    "nationality": st.sidebar.slider("Nationality Preference", 0.0, 1.0, 0.3, 0.1),
    "cuisine": st.sidebar.slider("Cuisine Preference", 0.0, 1.0, 0.3, 0.1),
    "smoking": st.sidebar.slider("Penalty: Smoking", 0.0, 1.0, 0.3, 0.1),
    "attitude": st.sidebar.slider("Penalty: Attitude", 0.0, 1.0, 0.3, 0.1),
}

uploaded_file = st.file_uploader("Upload your dataset (Excel or CSV)", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
    else:
        df = pd.read_csv(uploaded_file)

    st.write("### 📋 Final Scores Only")
    results = df.apply(lambda row: blueprint_score(row, weights), axis=1)
    results = pd.concat([df[["client_name", "maid_id"]], results[["final_score"]]], axis=1)

    # Show only final score table
    st.dataframe(results, use_container_width=True)

    # Drill-down explanations
    st.write("### 🔎 Explore Explanations")
    for idx, row in results.head(20).iterrows():  # limit to first 20 for speed
        with st.expander(f"Client {row['client_name']} – Maid {row['maid_id']} (Score: {row['final_score']:.1f}%)"):
            full_row = df.iloc[idx]
            scored_row = blueprint_score(full_row, weights)

            st.markdown("✅ **Requirements Matched:**")
            st.write(scored_row["requirements"] if scored_row["requirements"] else "None")

            st.markdown("❌ **Penalties / Mismatches:**")
            st.write(scored_row["penalties"] if scored_row["penalties"] else "None")

            st.markdown("🌟 **Bonus Traits:**")
            st.write(scored_row["bonuses"] if scored_row["bonuses"] else "None")

            st.markdown("⚪ **Not Specified by Client:**")
            st.write(scored_row["not_specified"] if scored_row["not_specified"] else "None")

    # -------------------------------
    # Charts: Distribution of scores
    # -------------------------------
    st.write("### 📊 Score Distribution Across All Matches")

    fig, ax = plt.subplots()
    ax.hist(results["final_score"], bins=20, edgecolor="black")
    ax.set_title("Distribution of Final Scores")
    ax.set_xlabel("Final Score (%)")
    ax.set_ylabel("Number of Matches")
    st.pyplot(fig)

    # Optional: Boxplot for spread
    fig2, ax2 = plt.subplots()
    ax2.boxplot(results["final_score"], vert=False)
    ax2.set_title("Score Spread (Boxplot)")
    ax2.set_xlabel("Final Score (%)")
    st.pyplot(fig2)
