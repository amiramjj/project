import streamlit as st
import pandas as pd

# ------------------------------
# Page Config: Full Width Layout
# -------------------------------
st.set_page_config(layout="wide")
# -------------------------------
# CONFIG
# -------------------------------
THEME_WEIGHTS = {
    "household_kids": 9,
    "special_cases": 8,
    "pets": 8,
    "living": 9,
    "nationality": 8,
    "cuisine": 6
}

BONUS_CAP = 10  # max total bonus %

# -------------------------------
# HELPER FUNCTIONS
# -------------------------------

def score_household_kids(client, maid, exp):
    w = THEME_WEIGHTS["household_kids"]
    if client == "unspecified":
        return None
    if client == "baby":
        if maid in ["refuses_baby", "refuses_baby_and_kids"]:
            return 0
        else:
            return w
    if client == "many_kids":
        if maid in ["refuses_many_kids", "refuses_baby_and_kids"]:
            return 0
        else:
            return w
    if client == "baby_and_kids":
        if maid in ["refuses_baby_and_kids", "refuses_baby", "refuses_many_kids"]:
            return 0
        else:
            return w
    return None

def score_special_cases(client, maid):
    w = THEME_WEIGHTS["special_cases"]
    if client == "unspecified":
        return None
    if client == "elderly":
        if maid in ["elderly_experienced", "elderly_and_special"]:
            return w
        elif maid == "special_needs":
            return int(w * 0.6)
    if client == "special_needs":
        if maid in ["special_needs", "elderly_and_special"]:
            return w
        elif maid == "elderly_experienced":
            return int(w * 0.6)
    if client == "elderly_and_special":
        if maid == "elderly_and_special":
            return w
        elif maid in ["elderly_experienced", "special_needs"]:
            return int(w * 0.6)
    return None

def score_pets(client, maid, handling):
    w = THEME_WEIGHTS["pets"]
    if client == "unspecified":
        return None
    if client == "cat":
        if maid in ["refuses_cat", "refuses_both_pets"]:
            return 0
        else:
            return w + 1 if handling in ["cats", "both"] else w
    if client == "dog":
        if maid in ["refuses_dog", "refuses_both_pets"]:
            return 0
        else:
            return w + 1 if handling in ["dogs", "both"] else w
    if client == "both":
        if maid in ["refuses_both_pets", "refuses_cat", "refuses_dog"]:
            return 0
        else:
            return w + 1 if handling == "both" else w
    return None

def score_living(client, maid):
    w = THEME_WEIGHTS["living"]
    if client == "unspecified":
        return None
    if client in ["private_room", "live_out+private_room"]:
        return w
    if client in ["private_room+abu_dhabi", "live_out+private_room+abu_dhabi"]:
        if "refuses_abu_dhabi" in maid:
            return 0
        else:
            return w
    return None

def score_nationality(client, maid):
    w = THEME_WEIGHTS["nationality"]
    if client == "any":
        return w
    prefs = client.split("+")
    prefs = [p.strip().replace(" maid", "").replace(" nationality", "") for p in prefs]
    if maid in prefs:
        return w
    # indian only matches if client = any
    if maid == "indian":
        return 0
    return 0

def score_cuisine(client, maid_flags):
    w = THEME_WEIGHTS["cuisine"]
    if client == "unspecified":
        return None
    prefs = client.split("+")
    prefs = [p.strip() for p in prefs]
    matches = 0
    if "lebanese" in prefs and maid_flags.get("maid_cooking_lebanese", 0) == 1:
        matches += 1
    if "khaleeji" in prefs and maid_flags.get("maid_cooking_khaleeji", 0) == 1:
        matches += 1
    if "international" in prefs and maid_flags.get("maid_cooking_international", 0) == 1:
        matches += 1
    if matches == 0:
        return 0
    return int(w * (matches / len(prefs)))

def calculate_bonus(row):
    bonus = 0
    if row.get("maidspeaks_arabic") == 1:
        bonus += 2
    if row.get("years_of_experience", 0) >= 5:
        bonus += 3
    if row.get("maidpref_smoking") == "non_smoker":
        bonus += 1
    return min(bonus, BONUS_CAP)

def calculate_score(row):
    scores = []
    max_weights = []

    # household & kids
    s = score_household_kids(row["clientmts_household_type"], row["maidmts_household_type"], row["maidpref_kids_experience"])
    if s is not None:
        scores.append(s)
        max_weights.append(THEME_WEIGHTS["household_kids"])

    # special cases
    s = score_special_cases(row["clientmts_special_cases"], row["maidpref_caregiving_profile"])
    if s is not None:
        scores.append(s)
        max_weights.append(THEME_WEIGHTS["special_cases"])

    # pets
    s = score_pets(row["clientmts_pet_type"], row["maidmts_pet_type"], row["maidpref_pet_handling"])
    if s is not None:
        scores.append(s)
        max_weights.append(THEME_WEIGHTS["pets"])

    # living arrangement
    s = score_living(row["clientmts_living_arrangement"], row["maidmts_living_arrangement"])
    if s is not None:
        scores.append(s)
        max_weights.append(THEME_WEIGHTS["living"])

    # nationality
    s = score_nationality(row["clientmts_nationality_preference"], row["maid_grouped_nationality"])
    if s is not None:
        scores.append(s)
        max_weights.append(THEME_WEIGHTS["nationality"])

    # cuisine
    maid_flags = {
        "maid_cooking_lebanese": row["maid_cooking_lebanese"],
        "maid_cooking_khaleeji": row["maid_cooking_khaleeji"],
        "maid_cooking_international": row["maid_cooking_international"]
    }
    s = score_cuisine(row["clientmts_cuisine_preference"], maid_flags)
    if s is not None:
        scores.append(s)
        max_weights.append(THEME_WEIGHTS["cuisine"])

    if not scores:
        return 0, "Neutral"

    base_score = sum(scores) / sum(max_weights) * 100
    bonus = calculate_bonus(row)
    final_score = min(base_score + bonus, 100)

    # flag not suitable if any theme with 0 in deal-breaker category
    unsuitable = (
        (row["clientmts_pet_type"] != "unspecified" and score_pets(row["clientmts_pet_type"], row["maidmts_pet_type"], row["maidpref_pet_handling"]) == 0) or
        (row["clientmts_living_arrangement"] != "unspecified" and score_living(row["clientmts_living_arrangement"], row["maidmts_living_arrangement"]) == 0) or
        (row["clientmts_household_type"] != "unspecified" and score_household_kids(row["clientmts_household_type"], row["maidmts_household_type"], row["maidpref_kids_experience"]) == 0) or
        (row["clientmts_nationality_preference"] != "any" and score_nationality(row["clientmts_nationality_preference"], row["maid_grouped_nationality"]) == 0)
    )

    return round(final_score, 1), "Not Suitable" if unsuitable else "Suitable"

# -------------------------------
# STREAMLIT APP
# -------------------------------
st.title("Client–Maid Matching Score Calculator")

uploaded_file = st.file_uploader("Upload your dataset (CSV or Excel)", type=["csv", "xlsx"])

if uploaded_file:
    if uploaded_file.name.endswith(".csv"):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)

    st.write("### Raw Data")
    st.dataframe(df.head())

    st.write("### Matching Scores")
    results = []
    for _, row in df.iterrows():
        score, status = calculate_score(row)
        results.append({"Final Score %": score, "Status": status})

    results_df = pd.concat([df, pd.DataFrame(results)], axis=1)
    st.dataframe(results_df)

    st.download_button("Download Results CSV", results_df.to_csv(index=False).encode("utf-8"), "matching_results.csv", "text/csv")
