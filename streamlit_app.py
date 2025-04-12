import streamlit as st
import pandas as pd
import json
import time
import logging
import anthropic
from io import StringIO

# CONFIG LOGGING
logging.basicConfig(filename="streamlit_claude.log", level=logging.INFO)

# Fonction pour lire un CSV BIA ($ séparateur)
def load_bia_csv(uploaded_file):
    rows = []
    for line in uploaded_file.getvalue().decode("utf-8").splitlines():
        parts = line.strip().split("$")
        if len(parts) >= 7:
            while len(parts) < 8:
                parts.append("")  # Ajouter colonne explanation vide
            rows.append(parts)
    df = pd.DataFrame(rows, columns=[
        "Question", "A", "B", "C", "D", "Correct Answer", "Image URL", "Explanation"
    ])
    return df

# Fonction de prompt
def generate_prompt(row):
    correct = row["Correct Answer"].strip().upper()
    if correct not in ['A', 'B', 'C', 'D']:
        return None
    reponse = str(row[correct]).strip()
    question = str(row["Question"]).strip()
    return (
        f"Explique de manière scientifique et précise, en 2 à 3 phrases adaptées au niveau d'un élève de 3e, pourquoi la réponse suivante est correcte : "
        f"Question : {question} "
        f"Réponse correcte : {reponse} "
        f"Ta réponse ne doit contenir que l'explication, sans retour à la ligne ni remarque supplémentaire."
    )

# Appel Claude pour explication
def generate_explanations(df, api_key, model="claude-3-7-sonnet-20250219"):
    client = anthropic.Anthropic(api_key=api_key)
    df["explanation"] = ""

    for idx, row in df.iterrows():
        prompt = generate_prompt(row)
        if not prompt:
            df.at[idx, "explanation"] = "[ERREUR - prompt invalide]"
            continue
        try:
            response = client.messages.create(
                model=model,
                max_tokens=256,
                temperature=0.3,
                messages=[{"role": "user", "content": prompt}]
            )
            answer = response.content[0].text.strip().replace("\n", " ")
            df.at[idx, "explanation"] = answer
        except Exception as e:
            logging.error(f"Erreur ligne {idx} : {e}")
            df.at[idx, "explanation"] = "[ERREUR]"
        time.sleep(0.6)  # limiter la fréquence

    return df

# Conversion en JSON BIA
def convert_to_json(df):
    data = []
    for _, row in df.iterrows():
        image = str(row["Image URL"]).strip()
        image = None if image.lower() in ["", "nan", "none", "null", "undefined"] else image
        data.append({
            "question": row["Question"].strip(),
            "a": row["A"].strip(),
            "b": row["B"].strip(),
            "c": row["C"].strip(),
            "d": row["D"].strip(),
            "correct": row["Correct Answer"].strip().upper(),
            "image": image,
            "explanation": row["explanation"].strip()
        })
    return json.dumps(data, ensure_ascii=False, indent=2)

# === STREAMLIT INTERFACE ===
st.title("🧠 Générateur d'explications BIA via Claude 3")

with st.sidebar:
    st.markdown("## ⚙️ Paramètres")
    api_key = st.text_input("Clé API Claude", type="password")
    model_choice = st.selectbox("Modèle Claude", [
        "claude-3-7-sonnet-20250219", "claude-3-5-sonnet-20241022"
    ])
    auto_convert_json = st.checkbox("Convertir automatiquement en JSON", True)

uploaded_file = st.file_uploader("📂 Charge un fichier CSV BIA (séparateur $)", type="csv")

if uploaded_file and api_key:
    df = load_bia_csv(uploaded_file)
    st.success(f"{len(df)} questions chargées.")

    if st.button("🚀 Générer les explications avec Claude"):
        df = generate_explanations(df, api_key, model=model_choice)
        st.success("✅ Génération terminée.")
        st.dataframe(df[["Question", "Correct Answer", "explanation"]])

        csv_output = df.to_csv(sep="$", index=False, header=False).encode("utf-8")
        st.download_button("📥 Télécharger CSV enrichi", csv_output, "questions_explained.csv", "text/csv")

        if auto_convert_json:
            json_output = convert_to_json(df)
            st.download_button("📥 Télécharger JSON prêt à l'emploi", json_output, "questions.json", "application/json")
else:
    st.info("🔐 Entrez votre clé API Claude et chargez un fichier CSV pour démarrer.")
