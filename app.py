import streamlit as st
import pandas as pd

# -------------------------------
# Blueprint Scoring Function with Explanations
# -------------------------------
def blueprint_score(row, w):
    requirement_score = 0.0
    requirement_max = 0.0
    penalties = 0.0

    req_explanations = []
    pen_explanations = []
    bonuses = []

    # ----- REQUIREMENTS -----
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

    # Special cases (elderly / special needs)
    c_special = row.get("clientmts_special_cases", "unspecified")
    m_care = row.get("maidpref_caregiving_profile", "unspecified")
    if c_special != "unspecified":
        requirement_max += w["special_cases"]
        if (c_special == "elderly" and m_care in ["elderly_experienced", "elderly_and_special"]) or \
           (c_special == "special_needs" and m_care in ["special_needs", "elderly_and_special"]) or \
           (c_special == "elderly_and_special" and m_care == "elderly_and_special"):
            requirement_score += w["special_cases"]
            req_explanations.append(f"Client needs {c_special} care, maid has experience.")
        else:
            penalties += w["special_cases"]
            pen_explanations.append(f"Client needs {c_special} care, maid lacks experience.")

    # Day-off policy
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

    # Living arrangement
    c_living = row.get("clientmts_living_arrangement", "unspecified")
    m_living = row.get("maidmts_living_arrangement", "unspecified")
    if c_living != "unspecified":
        requirement_max += w["living"]
        if ("private_room" in c_living and "requires_no_private_room" not in m_living):
            requirement_score += w["living"]
            req_explanations.append("Living arrangement accepted.")
        else:
            penalties += w["living"]
            pen_explanations.append("Living arrangement mismatch.")

    # Pets
    c_pets = row.get("clientmts_pet_type", "no_pets")
    m_pets = row.get("maidmts_pet_type", "unspecified")
    if c_pets != "no_pets":
        requirement_max += w["pets"]
        if (c_pets == "cat" and m_pets != "refuses_cat") or \
           (c_pets == "dog" and m_pets != "refuses_dog") or \
           (c_pets == "both" and m_pets != "refuses_both_pets"):
            requirement_score += w["pets"]
            req_explanations.append(f"Client has {c_pets}, maid accepts.")
        else:
            penalties += w["pets"]
            pen_explanations.append(f"Client has {c_pets}, maid refuses.")

    # Nationality preference
    if row.get("clientmts_nationality_preference", "any") != "any":
        requirement_max += w["nationality"]
        if row["clientmts_nationality_preference"] in str(row.get("maid_nationality", "")):
            requirement_score += w["nationality"]
            req_explanations.append("Nationality preference matched.")

    # Cuisine preference
    c_cuisine = row.get("clientmts_cuisine_preference", "unspecified")
    m_cooking = str(row.get("cooking_group", "not_specified"))
    if c_cuisine != "unspecified" and m_cooking != "not_specified":
        requirement_max += w["cuisine"]
        c_set = set(c_cuisine.split("+"))
        m_set = set(m_cooking.split("+"))
        if c_set & m_set:
            requirement_score += w["cuisine"]
            req_explanations.append("Cuisine preference matched.")

    # ----- PENALTIES (red flags) -----
    if row.get("maidpref_smoking") != "non_smoker":
        penalties += w["smoking"]
        pen_explanations.append("Maid is a smoker (penalty).")

    if "attitude" in str(row.get("maidpref_personality", "")):
        penalties += w["attitude"]
        pen_explanations.append("Maid shows negative attitude (penalty).")

    # ----- BONUSES -----
    if row.get("maidpref_smoking") == "non_smoker":
        bonuses.append("Non-smoker")
    if row.get("num_languages", 1) > 1:
        bonuses.append(f"Speaks {row.get('num_languages')} languages")
    if "veg_friendly" in str(row.get("maidpref_personality", "")):
        bonuses.append("Veg-friendly")
    if "energetic" in str(row.get("maidpref_personality", "")):
        bonuses.append("Energetic")
    if row.get("maidpref_education") not in ["unspecified", None]:
        bonuses.append(f"Education: {row.get('maidpref_education')}")

    # Final score
    requirement_pct = (requirement_score / requirement_max * 100) if requirement_max > 0 else 0
    final_score = max(0, requirement_pct - penalties * 100)

    return pd.Series({
        "requirement_pct": requirement_pct,
        "final_score": final_score,
        "requirements": "; ".join(req_explanations),
        "penalties": "; ".join(pen_explanations),
        "bonuses": ", ".join(bonuses)
    })


# -------------------------------
# Streamlit App
# -------------------------------
st.title("Client–Maid Matching Score (Interactive Blueprint)")

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

    st.write("### Dataset Preview", df.head())

    # Apply scoring
    results = df.apply(lambda row: blueprint_score(row, weights), axis=1)
    results = pd.concat([df[["client_name", "maid_id"]], results], axis=1)

    st.write("### Scoring Results with Explanations", results.head(50))

    # Download button
    csv = results.to_csv(index=False).encode("utf-8")
    st.download_button("Download Full Results", csv, "scoring_results.csv", "text/csv")

    # Expandable explanations
    st.write("### Detailed Explanations (first 10)")
    for idx, row in results.head(10).iterrows():
        with st.expander(f"Client {row['client_name']} – Maid {row['maid_id']}"):
            st.markdown(f"**Final Score:** {row['final_score']:.1f}%")
            st.markdown("✅ **Requirements Matched:**")
            st.write(row["requirements"] if row["requirements"] else "None")
            st.markdown("❌ **Penalties / Mismatches:**")
            st.write(row["penalties"] if row["penalties"] else "None")
            st.markdown("🌟 **Bonus Traits:**")
            st.write(row["bonuses"] if row["bonuses"] else "None")
