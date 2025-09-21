import streamlit as st
import pandas as pd

# ------------------------------
# Page Config
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
# HELPER FUNCTIONS WITH EXPLANATIONS
# -------------------------------

def score_household_kids(client, maid, exp):
    w = THEME_WEIGHTS["household_kids"]
    if client == "unspecified":
        return None, "Neutral: client did not specify household type"
    if client == "baby":
        if maid in ["refuses_baby", "refuses_baby_and_kids"]:
            return 0, "Mismatch: maid refuses baby care"
        else:
            return w, "Match: client has baby, maid accepts"
    if client == "many_kids":
        if maid in ["refuses_many_kids", "refuses_baby_and_kids"]:
            return 0, "Mismatch: maid refuses many kids"
        else:
            return w, "Match: client has many kids, maid accepts"
    if client == "baby_and_kids":
        if maid in ["refuses_baby_and_kids", "refuses_baby", "refuses_many_kids"]:
            return 0, "Mismatch: maid refuses baby_and_kids"
        else:
            return w, "Match: client has baby_and_kids, maid accepts"
    return None, "Neutral"

def score_special_cases(client, maid):
    w = THEME_WEIGHTS["special_cases"]
    if client == "unspecified":
        return None, "Neutral: client did not specify special cases"
    if client == "elderly":
        if maid in ["elderly_experienced", "elderly_and_special"]:
            return w, "Match: elderly supported"
        elif maid == "special_needs":
            return int(w * 0.6), "Partial: client elderly, maid only has special_needs"
    if client == "special_needs":
        if maid in ["special_needs", "elderly_and_special"]:
            return w, "Match: special needs supported"
        elif maid == "elderly_experienced":
            return int(w * 0.6), "Partial: client special_needs, maid only elderly"
    if client == "elderly_and_special":
        if maid == "elderly_and_special":
            return w, "Perfect match: elderly + special needs"
        elif maid in ["elderly_experienced", "special_needs"]:
            return int(w * 0.6), "Partial: maid covers only one"
    return None, "Neutral"

def score_pets(client, maid, handling):
    w = THEME_WEIGHTS["pets"]
    if client == "unspecified":
        return None, "Neutral: client did not specify pets"
    if client == "cat":
        if maid in ["refuses_cat", "refuses_both_pets"]:
            return 0, "Mismatch: maid refuses cats"
        else:
            return w, "Match: cats allowed"
    if client == "dog":
        if maid in ["refuses_dog", "refuses_both_pets"]:
            return 0, "Mismatch: maid refuses dogs"
        else:
            return w, "Match: dogs allowed"
    if client == "both":
        if maid in ["refuses_both_pets", "refuses_cat", "refuses_dog"]:
            return 0, "Mismatch: maid refuses one or both pets"
        else:
            return w, "Match: both cats & dogs allowed"
    return None, "Neutral"

def score_living(client, maid):
    w = THEME_WEIGHTS["living"]
    if client == "unspecified":
        return None, "Neutral: client did not specify living arrangement"
    if client in ["private_room", "live_out+private_room"]:
        return w, "Match: private room available"
    if client in ["private_room+abu_dhabi", "live_out+private_room+abu_dhabi"]:
        if "refuses_abu_dhabi" in maid:
            return 0, "Mismatch: maid refuses Abu Dhabi"
        else:
            return w, "Match: Abu Dhabi accepted"
    return None, "Neutral"

def score_nationality(client, maid):
    w = THEME_WEIGHTS["nationality"]
    if client == "any":
        return w, "Match: client accepts any nationality"
    prefs = client.split("+")
    prefs = [p.strip().replace(" maid", "").replace(" nationality", "") for p in prefs]
    if maid in prefs:
        return w, f"Match: maid nationality {maid} in client preference"
    if maid == "indian":
        return 0, "Mismatch: indian only allowed if client=any"
    return 0, f"Mismatch: maid nationality {maid} not in client preference"

def score_cuisine(client, maid_flags):
    w = THEME_WEIGHTS["cuisine"]
    if client == "unspecified":
        return None, "Neutral: client did not specify cuisine"
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
        return 0, "Mismatch: none of the requested cuisines matched"
    elif matches == len(prefs):
        return w, "Perfect match: all cuisines covered"
    else:
        return int(w * (matches / len(prefs))), f"Partial: {matches}/{len(prefs)} cuisines covered"

def calculate_bonus(row):
    bonus = 0
    reasons = []
    if row.get("maidspeaks_arabic") == 1:
        bonus += 2
        reasons.append("Arabic language (+2)")
    if row.get("years_of_experience", 0) >= 5:
        bonus += 3
        reasons.append("5+ years experience (+3)")
    if row.get("maidpref_smoking") == "non_smoker":
        bonus += 1
        reasons.append("Non-smoker (+1)")
    return min(bonus, BONUS_CAP), reasons

def calculate_score(row):
    theme_scores = {}
    scores = []
    max_weights = []

    # household & kids
    s, r = score_household_kids(row["clientmts_household_type"], row["maidmts_household_type"], row["maidpref_kids_experience"])
    theme_scores["Household & Kids Reason"] = r
    if s is not None:
        scores.append(s)
        max_weights.append(THEME_WEIGHTS["household_kids"])

    # special cases
    s, r = score_special_cases(row["clientmts_special_cases"], row["maidpref_caregiving_profile"])
    theme_scores["Special Cases Reason"] = r
    if s is not None:
        scores.append(s)
        max_weights.append(THEME_WEIGHTS["special_cases"])

    # pets
    s, r = score_pets(row["clientmts_pet_type"], row["maidmts_pet_type"], row["maidpref_pet_handling"])
    theme_scores["Pets Reason"] = r
    if s is not None:
        scores.append(s)
        max_weights.append(THEME_WEIGHTS["pets"])

    # living arrangement
    s, r = score_living(row["clientmts_living_arrangement"], row["maidmts_living_arrangement"])
    theme_scores["Living Reason"] = r
    if s is not None:
        scores.append(s)
        max_weights.append(THEME_WEIGHTS["living"])

    # nationality
    s, r = score_nationality(row["clientmts_nationality_preference"], row["maid_grouped_nationality"])
    theme_scores["Nationality Reason"] = r
    if s is not None:
        scores.append(s)
        max_weights.append(THEME_WEIGHTS["nationality"])

    # cuisine
    maid_flags = {
        "maid_cooking_lebanese": row["maid_cooking_lebanese"],
        "maid_cooking_khaleeji": row["maid_cooking_khaleeji"],
        "maid_cooking_international": row["maid_cooking_international"]
    }
    s, r = score_cuisine(row["clientmts_cuisine_preference"], maid_flags)
    theme_scores["Cuisine Reason"] = r
    if s is not None:
        scores.append(s)
        max_weights.append(THEME_WEIGHTS["cuisine"])

    if not scores:
        return 0, "Neutral", theme_scores, []

    base_score = sum(scores) / sum(max_weights) * 100
    bonus, bonus_reasons = calculate_bonus(row)
    final_score = min(base_score + bonus, 100)

    unsuitable = (
        (row["clientmts_pet_type"] != "unspecified" and "Mismatch" in theme_scores["Pets Reason"]) or
        (row["clientmts_living_arrangement"] != "unspecified" and "Mismatch" in theme_scores["Living Reason"]) or
        (row["clientmts_household_type"] != "unspecified" and "Mismatch" in theme_scores["Household & Kids Reason"]) or
        (row["clientmts_nationality_preference"] != "any" and "Mismatch" in theme_scores["Nationality Reason"])
    )

    return round(final_score, 1), "Not Suitable" if unsuitable else "Suitable", theme_scores, bonus_reasons

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

    st.write("### Matching Scores (Key Fields Only)")
    results = []
    for _, row in df.iterrows():
        score, status, reasons, bonus_reasons = calculate_score(row)
        result_row = {
            "client_name": row["client_name"],
            "maid_id": row["maid_id"],
            "Final Score %": score,
            "Status": status,
            **reasons,
            "Bonus Reasons": ", ".join(bonus_reasons) if bonus_reasons else "None"
        }
        results.append(result_row)

    results_df = pd.DataFrame(results)
    st.dataframe(results_df)

    # Expanders for detailed reasons
    st.write("### Detailed Explanations")
    for i, row in results_df.iterrows():
        with st.expander(f"Client {row['client_name']} & Maid {row['maid_id']} → {row['Final Score %']}% | {row['Status']}"):
            st.write("**Household & Kids:**", row["Household & Kids Reason"])
            st.write("**Special Cases:**", row["Special Cases Reason"])
            st.write("**Pets:**", row["Pets Reason"])
            st.write("**Living:**", row["Living Reason"])
            st.write("**Nationality:**", row["Nationality Reason"])
            st.write("**Cuisine:**", row["Cuisine Reason"])
            st.write("**Bonus:**", row["Bonus Reasons"])

    st.download_button("Download Results CSV", results_df.to_csv(index=False).encode("utf-8"), "matching_results.csv", "text/csv")
