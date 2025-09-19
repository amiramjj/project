------------------------------
# Page Config: Full Width Layout
# -------------------------------
st.set_page_config(layout="wide")

# -------------------------------
# Blueprint Scoring Function
# -------------------------------
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

# -------------------------------
# Final Blueprint Scoring Function
# -------------------------------

import pandas as pd

def blueprint_score(row, w):
    requirement_score = 0.0
    requirement_max = 0.0
    penalties = 0.0

    req_explanations = []
    pen_explanations = []
    bonus_explanations = []
    neutral_explanations = []

    # ----- REQUIREMENTS -----
    # Household & Kids
    c_house = row.get("clientmts_household_type", "unspecified")
    m_house = row.get("maidmts_household_type", "unspecified")
    kids_exp = row.get("maidpref_kids_experience", "unspecified")

    if c_house != "unspecified":
        requirement_max += w["household"]
        if ((c_house == "baby" and m_house != "refuses_baby" and kids_exp in ["lessthan2", "both"]) or
            (c_house == "many_kids" and m_house != "refuses_many_kids" and kids_exp in ["above2", "both"]) or
            (c_house == "baby_and_kids" and m_house != "refuses_baby_and_kids" and kids_exp == "both")):
            requirement_score += w["household"]
            req_explanations.append(f"Client wants {c_house}, maid accepts and has matching kids experience.")
        else:
            penalties += w["household"]
            pen_explanations.append(f"Client wants {c_house}, but maid refuses or did not specify.")
    else:
        neutral_explanations.append("Client did not specify household type.")

    # Special Care Needs
    c_special = row.get("clientmts_special_cases", "unspecified")
    m_care = row.get("maidpref_caregiving_profile", "unspecified")
    if c_special != "unspecified":
        requirement_max += w["special_cases"]
        if ((c_special == "elderly" and m_care in ["elderly_experienced", "elderly_and_special"]) or
            (c_special == "special_needs" and m_care in ["special_needs", "elderly_and_special"]) or
            (c_special == "elderly_and_special" and m_care == "elderly_and_special")):
            requirement_score += w["special_cases"]
            req_explanations.append(f"Client needs {c_special} care, maid has experience.")
        else:
            penalties += w["special_cases"]
            pen_explanations.append(f"Client needs {c_special} care, maid lacks or did not specify experience.")
    else:
        neutral_explanations.append("Client did not specify special care needs.")

    # Pets
    c_pets = row.get("clientmts_pet_type", "no_pets")
    m_pets = row.get("maidmts_pet_type", "unspecified")
    pet_handling = row.get("maidpref_pet_handling", "unspecified")
    if c_pets != "no_pets":
        requirement_max += w["pets"]
        if ((c_pets == "cat" and m_pets != "refuses_cat" and pet_handling in ["cats", "both"]) or
            (c_pets == "dog" and m_pets != "refuses_dog" and pet_handling in ["dogs", "both"]) or
            (c_pets == "both" and m_pets != "refuses_both_pets" and pet_handling == "both")):
            requirement_score += w["pets"]
            req_explanations.append(f"Client has {c_pets}, maid accepts and can handle them.")
        else:
            penalties += w["pets"]
            pen_explanations.append(f"Client has {c_pets}, maid refuses or did not specify handling.")
    else:
        neutral_explanations.append("Client did not specify pet preference.")

    # Day-off Policy
    c_dayoff = row.get("clientmts_dayoff_policy", "unspecified")
    m_dayoff = row.get("maidmts_dayoff_policy", "unspecified")
    if c_dayoff != "unspecified":
        requirement_max += w["dayoff"]
        if m_dayoff != "refuses_fixed_sunday":
            requirement_score += w["dayoff"]
            req_explanations.append("Day-off policy is acceptable.")
        else:
            penalties += w["dayoff"]
            pen_explanations.append("Day-off policy mismatch.")
    else:
        neutral_explanations.append("Client did not specify day-off policy.")

    # Living Arrangement
    c_living = row.get("clientmts_living_arrangement", "unspecified")
    m_living = row.get("maidmts_living_arrangement", "unspecified")
    m_travel = row.get("maidpref_travel", "unspecified")
    if c_living != "unspecified":
        requirement_max += w["living"]
        if ("private_room" in c_living and "requires_no_private_room" not in m_living) or \
           ("abu_dhabi" in c_living and "refuses_abu_dhabi" not in m_living):
            requirement_score += w["living"]
            req_explanations.append("Living arrangement accepted.")
        else:
            penalties += w["living"]
            pen_explanations.append("Living arrangement mismatch or maid did not specify.")
    else:
        neutral_explanations.append("Client did not specify living arrangement.")
        if m_travel == "travel_and_relocate":
            bonus_explanations.append("Maid is flexible for travel/relocation.")

    # Nationality
    c_nat = row.get("clientmts_nationality_preference", "any")
    m_nat = str(row.get("maid_nationality", "unspecified"))
    if c_nat != "any":
        requirement_max += w["nationality"]
        if c_nat in m_nat:
            requirement_score += w["nationality"]
            req_explanations.append("Nationality preference matched.")
        else:
            penalties += w["nationality"]
            pen_explanations.append("Nationality preference not matched or unspecified.")
    else:
        neutral_explanations.append("Client did not specify nationality preference.")

    # Cuisine
    c_cuisine = row.get("clientmts_cuisine_preference", "unspecified")
    m_cooking = str(row.get("cooking_group", "not_specified"))
    if c_cuisine != "unspecified":
        requirement_max += w["cuisine"]
        c_set = set(c_cuisine.split("+"))
        m_set = set(m_cooking.split("+"))
        if c_set & m_set:
            requirement_score += w["cuisine"]
            req_explanations.append("Cuisine preference matched.")
        else:
            penalties += w["cuisine"]
            pen_explanations.append("Cuisine preference mismatch or maid unspecified.")
    else:
        neutral_explanations.append("Client did not specify cuisine preference.")
        if "multi" in m_cooking:
            bonus_explanations.append("Maid has multi-cuisine experience.")

    # ----- PENALTIES -----
    if row.get("maidpref_smoking", "unspecified") != "non_smoker":
        penalties += w["smoking"]
        pen_explanations.append("Maid is a smoker or unspecified (penalty).")

    maid_personality = str(row.get("maidpref_personality", "unspecified"))
    if "bad_attitude" in maid_personality:
        penalties += w["attitude"]
        pen_explanations.append("Maid shows negative attitude (penalty).")
    elif "no_attitude" in maid_personality:
        bonus_explanations.append("Maid does not have attitude (bonus).")

    # ----- BONUSES -----
    if row.get("maidpref_smoking") == "non_smoker":
        bonus_explanations.append("Non-smoker")
    if row.get("num_languages", 1) > 1:
        bonus_explanations.append(f"Speaks {row.get('num_languages')} languages")
    if "veg_friendly" in maid_personality:
        bonus_explanations.append("Veg-friendly")
    if "energetic" in maid_personality:
        bonus_explanations.append("Energetic")
    if "polite" in maid_personality:
        bonus_explanations.append("Polite")
    if "cooperative" in maid_personality:
        bonus_explanations.append("Cooperative")
    if row.get("maidpref_education") not in ["unspecified", None]:
        bonus_explanations.append(f"Education: {row.get('maidpref_education')}")
    if "elderly" in m_care or "special_needs" in m_care:
        bonus_explanations.append("Extra caregiving skills")

    # ----- FINAL SCORE -----
    requirement_pct = (requirement_score / requirement_max * 100) if requirement_max > 0 else 0
    # Each bonus worth ~+2 points
    final_score = max(0, min(100, requirement_pct - penalties * 100 + len(bonus_explanations) * 2))

    return pd.Series({
        "requirement_pct": round(requirement_pct, 2),
        "final_score": round(final_score, 2),
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
