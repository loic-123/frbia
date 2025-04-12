import streamlit as st
import pandas as pd
import os
import json
import csv
import zipfile
from pathlib import Path
import anthropic
import io

# 📁 Préparation du dossier de sortie persistant
OUTPUT_DIR = Path("out")
OUTPUT_DIR.mkdir(exist_ok=True)

def get_selected_prompt():
    try:
        with open("selected_prompt.txt", "r", encoding="utf-8") as f:
            choice = f.read().strip()
            return "V1" if choice == "V1" else "V2"
    except FileNotFoundError:
        return "V1"  # Valeur par défaut


# 🧹 Nettoyage du champ image
def clean_image(image_field):
    if isinstance(image_field, str) and image_field.strip().lower() in ["", "none", "null", "nan", "undefined"]:
        return None
    return image_field.strip()

# 🔁 Conversion ligne CSV → dictionnaire JSON
def parse_csv_line(line, expected_fields=8):
    while len(line) < expected_fields:
        line.append("")
    return {
        "question": line[0].strip(),
        "a": line[1].strip(),
        "b": line[2].strip(),
        "c": line[3].strip(),
        "d": line[4].strip(),
        "correct": line[5].strip().upper(),
        "image": clean_image(line[6]),
        "explanation": line[7].strip()
    }

# 🧠 Génération du prompt Claude
def generate_prompt(row, version="V1"):
    try:
        correct_letter = row[5].strip().upper()
        if correct_letter not in ['A', 'B', 'C', 'D']:
            return "INVALID"
        answer_text = row["ABCDE".index(correct_letter)+1].strip()
        question_text = row[0].strip()
        if not question_text or not answer_text:
            return "INVALID"
        if version == "V2":
            return (
                "Tu es un professeur en aéronautique chargé d'aider un élève de 3e qui prépare le Brevet d’Initiation Aéronautique (BIA). "
                "Explique en 2 à 3 phrases pourquoi la réponse suivante est scientifiquement correcte, en utilisant les termes techniques vu dans le cadre du BIA et"
                "adaptés à un jeune public, et en vulgarisant si nécessaire. "
                "L’explication doit être concise, rigoureuse, sans retour à la ligne, sans reformuler la question ni mentionner les mauvaises réponses. "
                f"Voici la question et sa bonne réponse :\n"
                f"Question : {question_text}\n"
                f"Bonne réponse : {answer_text}\n"
                "Réponds uniquement par l’explication finale à afficher dans un QCM en ligne."
            )
        else:
            return (
                f"Explique de manière scientifique et précise, en 2 à 3 phrases adaptées au niveau d'un élève de 3e, "
                f"pourquoi la réponse suivante est correcte : "
                f"Question : {question_text} "
                f"Réponse correcte : {answer_text} "
                f"Ta réponse ne doit contenir que l'explication, sans retour à la ligne ni remarque supplémentaire."
            )
    except:
        return "INVALID"

# ⚙️ Traitement d’un fichier CSV
def process_csv_bytes(file_bytes, filename, client):
    base_name = Path(filename).stem
    lines = list(csv.reader(file_bytes.decode("utf-8").splitlines(), delimiter="$"))
    if lines and "question" in lines[0][0].lower():
        lines = lines[1:]

    enriched = []
    progress_bar = st.progress(0.0, text=f"Génération des explications ({filename})")
    for idx, line in enumerate(lines):
        if len(line) < 7:
            line += [""] * (7 - len(line))
        prompt_version = get_selected_prompt()
        prompt = generate_prompt(line, version=prompt_version)
        if prompt == "INVALID":
            explanation = "[ERREUR - Prompt non généré]"
        else:
            try:
                message = client.messages.create(
                    model="claude-3-7-sonnet-20250219",
                    max_tokens=256,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                explanation = message.content[0].text.strip().replace("\n", " ")
            except Exception as e:
                explanation = f"[ERREUR - {str(e)}]"
        line.append(explanation)
        enriched.append(line)
        progress_bar.progress((idx + 1) / len(lines), text=f"{idx+1}/{len(lines)} explications générées ({filename})")

    # 💾 Sauvegarde CSV
    csv_path = OUTPUT_DIR / f"{base_name}_enriched.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, delimiter="$").writerows(enriched)

    # 💾 Sauvegarde JSON
    json_path = OUTPUT_DIR / f"{base_name}.json"
    with open(json_path, "w", encoding="utf-8") as f_json:
        json.dump([parse_csv_line(row) for row in enriched], f_json, ensure_ascii=False, indent=2)

    return csv_path, json_path

# 🌐 Interface utilisateur
st.set_page_config(page_title="🧠 Générateur BIA", layout="centered")
st.title("🧠 Générateur d’explications BIA avec Claude")
st.markdown("Transforme des questions BIA en explications pédagogiques pour les élèves de 3e grâce à Claude 3.7 Sonnet.")

api_key = st.text_input("🔑 Clé API Claude (Anthropic)", type="password")
uploaded_files = st.file_uploader("📂 Charge un ou plusieurs fichiers CSV (séparateur $)", type="csv", accept_multiple_files=True)

# Mémoire persistante
if "results" not in st.session_state:
    st.session_state.results = []

# 🔘 Lancement du traitement
if api_key and uploaded_files:
    client = anthropic.Anthropic(api_key=api_key)
    if st.button("🧠 Générer les explications pour tous les fichiers"):
        for file in uploaded_files:
            file_bytes = file.read()
            with st.spinner(f"Traitement de {file.name}..."):
                csv_path, json_path = process_csv_bytes(file_bytes, file.name, client)
                st.session_state.results.append((file.name, csv_path, json_path))

# 📂 Affichage des résultats
if st.session_state.results:
    for fname, csv_path, json_path in st.session_state.results:
        with st.expander(f"📁 Résultat pour {fname}", expanded=True):
            with open(csv_path, "rb") as f_csv:
                st.download_button("⬇ Télécharger le CSV", f_csv.read(), file_name=csv_path.name, mime="text/csv", key=f"csv-{csv_path.name}")
            with open(json_path, "rb") as f_json:
                st.download_button("⬇ Télécharger le JSON", f_json.read(), file_name=json_path.name, mime="application/json", key=f"json-{json_path.name}")

    # 📦 Archive globale ZIP
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for _, _, json_path in st.session_state.results:
            zipf.write(json_path, arcname=json_path.name)
    zip_buffer.seek(0)
    st.download_button("📦 Télécharger tous les JSON (.zip)", data=zip_buffer, file_name="export_json.zip", mime="application/zip", key="zip-all")
    st.success("✅ Tous les fichiers ont été générés avec succès !")
