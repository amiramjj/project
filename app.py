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
            if exp in ["lessthan2", "above2", "both"]:
                return int(w * 1.2), "Bonus: maid has kids experience despite refusal (baby)"
            return 0, "Mismatch: maid refuses baby care"
        elif exp in ["lessthan2", "above2", "both"]:
            return int(w * 1.2), "Bonus: maid has kids experience, client has baby"
        else:
            return w, "Match: client has baby, maid accepts"
    if client == "many_kids":
        if maid in ["refuses_many_kids", "refuses_baby_and_kids"]:
            if exp in ["lessthan2", "above2", "both"]:
                return int(w * 1.2), "Bonus: maid has kids experience despite refusal (many kids)"
            return 0, "Mismatch: maid refuses many kids"
        elif exp in ["lessthan2", "above2", "both"]:
            return int(w * 1.2), "Bonus: maid has kids experience, client has many kids"
        else:
            return w, "Match: client has many kids, maid accepts"
    if client == "baby_and_kids":
        if maid in ["refuses_baby_and_kids", "refuses_baby", "refuses_many_kids"]:
            if exp in ["lessthan2", "above2", "both"]:
                return int(w * 1.2), "Bonus: maid has kids experience despite refusal (baby_and_kids)"
            return 0, "Mismatch: maid refuses baby_and_kids"
        elif exp in ["lessthan2", "above2", "both"]:
            return int(w * 1.2), "Bonus: maid has kids experience, client has baby_and_kids"
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
            if handling in ["cats", "both"]:
                return int(w * 1.2), "Bonus: maid reports cat handling despite refusal"
            return 0, "Mismatch: maid refuses cats"
        elif handling in ["cats", "both"]:
            return int(w * 1.2), "Bonus: maid has cat handling experience"
        else:
            return w, "Match: cats allowed"
    if client == "dog":
        if maid in ["refuses_dog", "refuses_both_pets"]:
            if handling in ["dogs", "both"]:
                return int(w * 1.2), "Bonus: maid reports dog handling despite refusal"
            return 0, "Mismatch: maid refuses dogs"
        elif handling in ["dogs", "both"]:
            return int(w * 1.2), "Bonus: maid has dog handling experience"
        else:
            return w, "Match: dogs allowed"
    if client == "both":
        if maid in ["refuses_both_pets", "refuses_cat", "refuses_dog"]:
            if handling in ["cats", "dogs", "both"]:
                return int(w * 1.2), "Bonus: maid reports pet handling despite refusal"
            return 0, "Mismatch: maid refuses one or both pets"
        elif handling == "both":
            return int(w * 1.2), "Bonus: maid prefers handling both cats & dogs"
        else:
            return w, "Match: both cats & dogs allowed"
    return None, "Neutral"

def score_living(client, maid):
    w = THEME_WEIGHTS["living"]
    if client == "unspecified":
        return None, "Neutral: client did not specify living arrangement"

    # Client requires private room
    if client in ["private_room", "live_out+private_room"]:
        return w, "Match: private room requirement satisfied"

    # Client requires Abu Dhabi posting
    if client in ["private_room+abu_dhabi", "live_out+private_room+abu_dhabi"]:
        if "refuses_abu_dhabi" in maid:
            return 0, "Mismatch: maid refuses Abu Dhabi"
        else:
            return w, "Match: Abu Dhabi posting acceptable"

    return None, "Neutral"

def score_nationality(client, maid):
    w = THEME_WEIGHTS["nationality"]
    if client == "any":
        return w, f"Match: client accepts any nationality, maid is {maid}"
    mapping = {
        "filipina": "filipina",
        "ethiopian maid": "ethiopian",
        "west african nationality": "west_african"
    }
    prefs = client.split("+")
    prefs = [mapping.get(p.strip(), p.strip()) for p in prefs]
    if maid in prefs:
        return w, f"Match: client prefers {client}, maid is {maid}"
    if maid == "indian":
        return 0, "Mismatch: client does not accept indian nationality"
    return 0, f"Mismatch: client prefers {client}, maid is {maid}"

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
        return 0, "Mismatch: no requested cuisines matched"
    if matches == len(prefs):
        return w, "Perfect match: all cuisines covered"
    if len(prefs) == 2 and matches == 1:
        return int(w * 0.6), "Partial match: 1 of 2 cuisines covered"
    if len(prefs) == 3:
        if matches == 2:
            return int(w * 0.8), "Partial match: 2 of 3 cuisines covered"
        if matches == 1:
            return int(w * 0.5), "Weak partial match: 1 of 3 cuisines covered"
    return int(w * (matches / len(prefs))), f"Partial match: {matches} of {len(prefs)} cuisines covered"

def score_bonuses(row):
    bonuses, explanations = 0, []
    langs = []
    if row.get("maidspeaks_arabic", 0) == 1:
        bonuses += 1; langs.append("Arabic")
    if row.get("maidspeaks_english", 0) == 1:
        bonuses += 1; langs.append("English")
    if row.get("maidspeaks_french", 0) == 1:
        bonuses += 1; langs.append("French")
    if langs:
        explanations.append("Bonus: speaks " + ", ".join(langs))
    exp = row.get("years_of_experience", 0)
    if exp >= 5:
        bonuses += 2; explanations.append(f"Bonus: {exp} years experience")
    elif exp >= 2:
        bonuses += 1; explanations.append(f"Bonus: {exp} years experience")
    edu = row.get("maidpref_education", "unspecified")
    if edu in ["school", "both", "university"]:
        bonuses += 1; explanations.append(f"Bonus: education = {edu}")
    pers = row.get("maidpref_personality", "unspecified")
    if pers != "unspecified":
        bonuses += 1; explanations.append(f"Bonus: personality = {pers.replace('+', ', ')}")
    travel = row.get("maidpref_travel", "unspecified")
    if travel == "travel":
        bonuses += 1; explanations.append("Bonus: open to travel")
    elif travel in ["relocate", "travel_and_relocate"]:
        bonuses += 2; explanations.append("Bonus: open to travel & relocation")
    smoking = row.get("maidpref_smoking", "unspecified")
    if smoking == "non_smoker":
        bonuses += 1; explanations.append("Bonus: non-smoker")
    return min(bonuses, BONUS_CAP), explanations

def calculate_score(row):
    theme_scores = {}
    scores, max_weights = [], []
    s, r = score_household_kids(row["clientmts_household_type"], row["maidmts_household_type"], row["maidpref_kids_experience"])
    theme_scores["Household & Kids Reason"] = r
    if s is not None: scores.append(s); max_weights.append(THEME_WEIGHTS["household_kids"])
    s, r = score_special_cases(row["clientmts_special_cases"], row["maidpref_caregiving_profile"])
    theme_scores["Special Cases Reason"] = r
    if s is not None: scores.append(s); max_weights.append(THEME_WEIGHTS["special_cases"])
    s, r = score_pets(row["clientmts_pet_type"], row["maidmts_pet_type"], row["maidpref_pet_handling"])
    theme_scores["Pets Reason"] = r
    if s is not None: scores.append(s); max_weights.append(THEME_WEIGHTS["pets"])
    s, r = score_living(row["clientmts_living_arrangement"], row["maidmts_living_arrangement"])
    theme_scores["Living Reason"] = r
    if s is not None: scores.append(s); max_weights.append(THEME_WEIGHTS["living"])
    s, r = score_nationality(row["clientmts_nationality_preference"], row["maid_grouped_nationality"])
    theme_scores["Nationality Reason"] = r
    if s is not None: scores.append(s); max_weights.append(THEME_WEIGHTS["nationality"])
    maid_flags = {
        "maid_cooking_lebanese": row["maid_cooking_lebanese"],
        "maid_cooking_khaleeji": row["maid_cooking_khaleeji"],
        "maid_cooking_international": row["maid_cooking_international"]
    }
    s, r = score_cuisine(row["clientmts_cuisine_preference"], maid_flags)
    theme_scores["Cuisine Reason"] = r
    if s is not None: scores.append(s); max_weights.append(THEME_WEIGHTS["cuisine"])
    if not scores:
        return 0, "Neutral", theme_scores, []
    base_score = sum(scores) / sum(max_weights) * 100
    bonus, bonus_reasons = score_bonuses(row)
    final_score = min(base_score + bonus, 100)
    return round(final_score, 1), theme_scores, bonus_reasons

# -------------------------------
# STREAMLIT APP
# -------------------------------
st.title("Client–Maid Matching Score Calculator")

uploaded_file = st.file_uploader("Upload your dataset (CSV or Excel)", type=["csv", "xlsx"])
if uploaded_file:
    df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
    st.write("### Matching Scores (Key Fields Only)")
    results = []
    for _, row in df.iterrows():
        score, reasons, bonus_reasons = calculate_score(row)
        result_row = {
            "client_name": row["client_name"],
            "maid_id": row["maid_id"],
            "Final Score %": score,
            **reasons,
            "Bonus Reasons": ", ".join(bonus_reasons) if bonus_reasons else "None"
        }
        results.append(result_row)
    results_df = pd.DataFrame(results)
    st.dataframe(results_df)
    st.write("### Detailed Explanations")
    
    # Create a dropdown of all client–maid pairs
    pair_options = results_df.apply(lambda r: f"{r['client_name']} ↔ {r['maid_id']} ({r['Final Score %']}% | {r['Status']})", axis=1)
    selected_pair = st.selectbox("Select a Client–Maid Pair", pair_options)
    
    # Show explanations for the selected pair
    if selected_pair:
        row = results_df.iloc[pair_options.tolist().index(selected_pair)]
        st.subheader(f"Explanation for {row['client_name']} ↔ {row['maid_id']}")
        st.write("**Household & Kids:**", row["Household & Kids Reason"])
        st.write("**Special Cases:**", row["Special Cases Reason"])
        st.write("**Pets:**", row["Pets Reason"])
        st.write("**Living:**", row["Living Reason"])
        st.write("**Nationality:**", row["Nationality Reason"])
        st.write("**Cuisine:**", row["Cuisine Reason"])
        st.write("**Bonus:**", row["Bonus Reasons"])

    st.download_button("Download Results CSV", results_df.to_csv(index=False).encode("utf-8"), "matching_results.csv", "text/csv")
