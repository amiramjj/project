import streamlit as st
import pandas as pd

# -------------------------------
# Blueprint Scoring Function with Explanations
# -------------------------------
def blueprint_score(row):
    requirement_score = 0.0
    requirement_max = 0.0
    penalties = 0.0
    bonuses = []

    req_explanations = []
    pen_explanations = []

    # ----- REQUIREMENTS -----
    # Household type
    c_house = row.get("clientmts_household_type", "unspecified")
    m_house = row.get("maidmts_household_type", "unspecified")
    if c_house != "unspecified":
        requirement_max += 0.7
        if (c_house == "baby" and m_house != "refuses_baby") or \
           (c_house == "many_kids" and m_house != "refuses_many_kids") or \
           (c_house == "baby_and_kids" and m_house != "refuses_baby_and_kids"):
            requirement_score += 0.7
            req_explanations.append(f"Client wants {c_house}, maid accepts.")
        else:
            penalties += 0.7
            pen_explanations.append(f"Client wants {c_house}, but maid refuses.")

    # Special cases
    c_special = row.get("clientmts_special_cases", "unspecified")
    m_care = row.get("maidpref_caregiving_profile", "unspecified")
    if c_special != "unspecified":
        requirement_max += 0.7
        if (c_special == "elderly" and m_care in ["elderly_experienced", "elderly_and_special"]) or \
           (c_special == "special_needs" and m_care in ["special_needs", "elderly_and_special"]) or \
           (c_special == "elderly_and_special" and m_care == "elderly_and_special"):
            requirement_score += 0.7
            req_explanations.append(f"Client needs {c_special} care, maid has experience.")
        else:
            penalties += 0.7
            pen_explanations.append(f"Client needs {c_special} care, maid lacks experience.")

    # Day-off policy
    c_dayoff = row.get("clientmts_dayoff_policy", "unspecified")
    m_dayoff = row.get("maidmts_dayoff_policy", "unspecified")
    if c_dayoff != "unspecified":
        requirement_max += 0.6
        if m_dayoff != "refuses_fixed_sunday":
            requirement_score += 0.6
            req_explanations.append("Day-off policy is acceptable.")
        else:
            penalties += 0.6
            pen_explanations.append("Day-off policy mismatch.")

    # Living arrangement
    c_living = row.get("clientmts_living_arrangement", "unspecified")
    m_living = row.get("maidmts_living_arrangement", "unspecified")
    if c_living != "unspecified":
        requirement_max += 0.6
        if ("private_room" in c_living and "requires_no_private_room" not in m_living):
            requirement_score += 0.6
            req_explanations.append("Living arrangement accepted.")
        else:
            penalties += 0.6
            pen_explanations.append("Living arrangement mismatch.")

    # Pets
    c_pets = row.get("clientmts_pet_type", "no_pets")
    m_pets = row.get("maidmts_pet_type", "unspecified")
    if c_pets != "no_pets":
        requirement_max += 0.6
        if (c_pets == "cat" and m_pets != "refuses_cat") or \
           (c_pets == "dog" and m_pets != "refuses_dog") or \
           (c_pets == "both" and m_pets != "refuses_both_pets"):
            requirement_score += 0.6
            req_explanations.append(f"Client has {c_pets}, maid accepts.")
        else:
            penalties += 0.6
            pen_explanations.append(f"Client has {c_pets}, maid refuses.")

    # Nationality
    if row.get("clientmts_nationality_preference", "any") != "any":
        requirement_max += 0.3
        if row["clientmts_nationality_preference"] in str(row.get("maid_nationality", "")):
            requirement_score += 0.3
            req_explanations.append("Nationality preference matched.")

    # Cuisine
    c_cuisine = row.get("clientmts_cuisine_preference", "unspecified")
    m_cooking = str(row.get("cooking_group", "not_specified"))
    if c_cuisine != "unspecified" and m_cooking != "not_specified":
        requirement_max += 0.3
        c_set = set(c_cuisine.split("+"))
        m_set = set(m_cooking.split("+"))
        if c_set & m_set:
            requirement_score += 0.3
            req_explanations.append("Cuisine preference matched.")

    # ----- PENALTIES (red flags) -----
    if row.get("maidpref_smoking") != "non_smoker":
        penalties += 0.3
        pen_explanations.append("Maid is a smoker (penalty).")

    if "attitude" in str(row.get("maidpref_personality", "")):
        penalties += 0.3
        pen_explanations.append("Maid shows negative attitude (penalty).")

    # ----- BONUSES -----
    bonuses = []
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
st.title("Client–Maid Matching Score (Blueprint with Explanations)")

uploaded_file = st.file_uploader("Upload your dataset (Excel or CSV)", type=["xlsx", "csv"])

if uploaded_file:
    if uploaded_file.name.endswith(".xlsx"):
        df = pd.read_excel(uploaded_file, sheet_name="Sheet1")
    else:
        df = pd.read_csv(uploaded_file)

    st.write("### Dataset Preview", df.head())

    # Apply scoring
    results = df.apply(blueprint_score, axis=1)
    results = pd.concat([df[["client_name", "maid_id"]], results], axis=1)

    st.write("### Scoring Results with Explanations", results.head(50))

    # Allow download
    csv = results.to_csv(index=False).encode("utf-8")
    st.download_button("Download Full Results", csv, "scoring_results.csv", "text/csv")

    # Expandable per-row detailed explanation
    st.write("### Detailed Explanations")
    for idx, row in results.head(10).iterrows():
        with st.expander(f"Client {row['client_name']} – Maid {row['maid_id']}"):
            st.markdown(f"**Final Score:** {row['final_score']:.1f}%")
            st.markdown("✅ **Requirements Matched:**")
            st.write(row["requirements"] if row["requirements"] else "None")
            st.markdown("❌ **Penalties / Mismatches:**")
            st.write(row["penalties"] if row["penalties"] else "None")
            st.markdown("🌟 **Bonus Traits:**")
            st.write(row["bonuses"] if row["bonuses"] else "None")
