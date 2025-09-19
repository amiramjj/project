import streamlit as st
import pandas as pd

# ------------------------------
# Page Config: Full Width Layout
# -------------------------------
st.set_page_config(layout="wide")

# -------------------------------
# Define weights
# -------------------------------
w = {
    "household": 0.8,
    "special_cases": 0.8,
    "pets": 0.7,
    "dayoff": 0.7,
    "living": 0.7,
    "nationality": 0.5,
    "cuisine": 0.4,
    "smoking": 0.4,
    "attitude": 0.4,
}

# -------------------------------
# Scoring function
# -------------------------------
def blueprint_score(row, w):
    requirement_score = 0.0
    requirement_max = 0.0
    penalties = 0.0

    req_explanations, pen_explanations, bonus_explanations, neutral_explanations = [], [], [], []

    # ---- Household & Kids ----
    c_house = row.get("clientmts_household_type", "unspecified")
    m_house = row.get("maidmts_household_type", "unspecified")
    kids_exp = row.get("maidpref_kids_experience", "unspecified")
    if c_house != "unspecified":
        requirement_max += w["household"]
        if ((c_house == "baby" and m_house != "refuses_baby" and kids_exp in ["lessthan2", "both"]) or
            (c_house == "many_kids" and m_house != "refuses_many_kids" and kids_exp in ["above2", "both"]) or
            (c_house == "baby_and_kids" and m_house != "refuses_baby_and_kids" and kids_exp == "both")):
            requirement_score += w["household"]
            req_explanations.append(f"Client requires {c_house}, maid matches with experience.")
        else:
            penalties += w["household"]
            pen_explanations.append(f"Client requires {c_house}, maid does not meet this need.")
    else:
        neutral_explanations.append("Client did not specify household type.")
        # Bonus if maid has kids experience anyway
        if kids_exp in ["lessthan2", "above2", "both"]:
            bonus_explanations.append(f"Maid has kids experience ({kids_exp}).")

    # ---- Special Care ----
    c_special = row.get("clientmts_special_cases", "unspecified")
    m_care = row.get("maidpref_caregiving_profile", "unspecified")
    if c_special != "unspecified":
        requirement_max += w["special_cases"]
        if ((c_special == "elderly" and m_care in ["elderly_experienced", "elderly_and_special"]) or
            (c_special == "special_needs" and m_care in ["special_needs", "elderly_and_special"]) or
            (c_special == "elderly_and_special" and m_care == "elderly_and_special")):
            requirement_score += w["special_cases"]
            req_explanations.append(f"Client requires {c_special} care, maid has relevant experience.")
        else:
            penalties += w["special_cases"]
            pen_explanations.append(f"Client requires {c_special} care, maid lacks relevant experience.")
    else:
        neutral_explanations.append("Client did not specify special care needs.")
        # Bonus if maid has care profile anyway
        if m_care in ["elderly_experienced", "special_needs", "elderly_and_special"]:
            bonus_explanations.append(f"Maid has {m_care.replace('_',' ')} experience.")

    # ---- Pets ----
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
            pen_explanations.append(f"Client has {c_pets}, maid cannot handle them.")
    else:
        neutral_explanations.append("Client did not specify pet preference.")
        if pet_handling in ["cats", "dogs", "both"]:
            bonus_explanations.append(f"Maid can handle pets: {pet_handling}.")

    # ---- Day-off ----
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

    # ---- Living Arrangement ----
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
            pen_explanations.append("Living arrangement does not meet client’s requirement.")
    else:
        neutral_explanations.append("Client did not specify living arrangement.")
        if m_travel == "travel_and_relocate":
            bonus_explanations.append("Maid is flexible for travel/relocation.")

    # ---- Nationality ----
    c_nat_raw = str(row.get("clientmts_nationality_preference", "any")).strip().lower()
    m_nat_raw = str(row.get("maid_grouped_nationality", "unspecified")).lower()
    
    # Normalization map
    norm_map = {
        "ethiopian": "ethiopian", "ethiopian maid": "ethiopian",
        "filipina": "filipina", "filipina maid": "filipina",
        "west_african": "west_african", "west african": "west_african",
        "west african nationality": "west_african", "west_african_nationality": "west_african"
    }
    
    # Normalize maid nationalities
    m_nat_cleaned = []
    for n in m_nat_raw.split("+"):
        n = n.strip().replace("_", " ")  # unify underscores vs spaces
        n = norm_map.get(n, n)          # normalize if in map
        m_nat_cleaned.append(n)
    m_nat_set = set(filter(None, m_nat_cleaned))
    
    # Normalize client preference
    c_nat = norm_map.get(c_nat_raw, c_nat_raw)
    
    if c_nat not in ["any", "unspecified"]:
        requirement_max += w["nationality"]
        if c_nat in m_nat_set:
            requirement_score += w["nationality"]
            req_explanations.append("Nationality preference matched.")
        else:
            penalties += w["nationality"]
            pen_explanations.append(
                f"Client requires {c_nat}, maid nationalities are {', '.join(m_nat_set) if m_nat_set else 'none'}."
            )
    else:
        neutral_explanations.append("Client did not specify nationality preference.")



    # ---- Cuisine ----
    c_cuisine = row.get("clientmts_cuisine_preference", "unspecified").lower()
    maid_cuisines = {
        "khaleeji": row.get("maid_cooking_khaleeji", 0),
        "lebanese": row.get("maid_cooking_lebanese", 0),
        "international": row.get("maid_cooking_international", 0),
        "not_specified": row.get("maid_cooking_not_specified", 0),
    }
    if c_cuisine != "unspecified":
        requirement_max += w["cuisine"]
        client_cuisines = [c.strip().lower() for c in c_cuisine.split("+")]
        if any(maid_cuisines.get(c, 0) == 1 for c in client_cuisines):
            requirement_score += w["cuisine"]
            req_explanations.append(f"Client requires {', '.join(client_cuisines)}, maid can cook at least one.")
        else:
            penalties += w["cuisine"]
            pen_explanations.append(f"Client requires {', '.join(client_cuisines)}, maid cannot cook these.")
    else:
        neutral_explanations.append("Client did not specify cuisine preference.")
        maid_known = [c for c, v in maid_cuisines.items() if v == 1 and c != "not_specified"]
        if maid_known:
            bonus_explanations.append(f"Maid can cook: {', '.join(maid_known)}.")

    # ---- Bonus Traits (only if client did not require them) ----
    client_prefs = str(row.get("client_mts_at_hiring", "")).lower()
    maid_personality = str(row.get("maidpref_personality", "unspecified"))

    if "non-smoker" not in client_prefs and row.get("maidpref_smoking") == "non_smoker":
        bonus_explanations.append("Maid is a non-smoker")
    if "no_attitude" in maid_personality and "attitude" not in client_prefs:
        bonus_explanations.append("Maid does not have attitude")
    if "polite" in maid_personality and "polite" not in client_prefs:
        bonus_explanations.append("Maid is polite")
    if "cooperative" in maid_personality and "cooperative" not in client_prefs:
        bonus_explanations.append("Maid is cooperative")
    if "energetic" in maid_personality and "energetic" not in client_prefs:
        bonus_explanations.append("Maid is energetic")
    if "veg_friendly" in maid_personality and "veg" not in c_cuisine:
        bonus_explanations.append("Maid is veg-friendly")
    if row.get("num_languages", 1) > 1:
        bonus_explanations.append(f"Maid speaks {row.get('num_languages')} languages")
    if row.get("maidpref_education") not in ["unspecified", None] and "education" not in client_prefs:
        bonus_explanations.append(f"Education: {row.get('maidpref_education')}")

    # ----- FINAL SCORE -----
    requirement_pct = (requirement_score / requirement_max * 100) if requirement_max > 0 else 0
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
# Streamlit Layout
# -------------------------------
st.title("🧾 Client–Maid Matching Score Dashboard")

uploaded_file = st.file_uploader("Upload your dataset (CSV or Excel)", type=["csv", "xlsx"])
if uploaded_file is not None:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.success(f"Loaded dataset with {len(df)} rows.")

    # Apply scoring to all rows
    results = df.apply(lambda row: blueprint_score(row, w), axis=1)
    df_results = pd.concat([df[["client_name", "maid_id"]], results], axis=1)

    # Show overview table
    st.subheader("📊 Final Scores Overview")    
    # Filter box
    search_term = st.text_input("Search by Client or Maid ID").lower()
    
    if search_term:
        filtered_df = df_results[
            df_results["client_name"].str.lower().str.contains(search_term) |
            df_results["maid_id"].astype(str).str.lower().str.contains(search_term)
        ]
    else:
        filtered_df = df_results
    
    st.dataframe(filtered_df[["client_name", "maid_id", "final_score"]].head(30))
    
    # ---- 7. Download full results ----
    csv = df_results.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="⬇️ Download Full Results as CSV",
        data=csv,
        file_name="matching_scores.csv",
        mime="text/csv",
    )
    
    # ---- 8. Interactive details ----
    st.subheader("🔍 Inspect Match Details")
    if not filtered_df.empty:
        selected_row = st.selectbox(
            "Select a client-maid pair:",
            filtered_df.index,
            format_func=lambda idx: f"{filtered_df.loc[idx, 'client_name']} | Maid {filtered_df.loc[idx, 'maid_id']}"
        )
    
        if selected_row is not None:
            row = filtered_df.loc[selected_row]
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
