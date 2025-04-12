import streamlit as st
import pandas as pd
import os
import json
import csv
from pathlib import Path
import anthropic
import zipfile
import io

# Dossiers de sortie persistants
OUTPUT_DIR = Path("out")
OUTPUT_DIR.mkdir(exist_ok=True)

# Détection image manquante
def clean_image(image_field):
    if isinstance(image_field, str) and image_field.strip().lower() in ["", "none", "null", "nan", "undefined"]:
        return None
    return image_field.strip()

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

def generate_prompt(row):
    try:
        correct_letter = row[5].strip().upper()
        if correct_letter not in ['A', 'B', 'C', 'D']:
            return "INVALID"
        answer_text = row["ABCDE".index(correct_letter)+1].strip()
        question_text = row[0].strip()
        if not question_text or not answer_text:
            return "INVALID"
        return (
            f"Explique de manière scientifique et précise, en 2 à 3 phrases adaptées au niveau d'un élève de 3e, "
            f"pourquoi la réponse suivante est correcte : "
            f"Question : {question_text} "
            f"Réponse correcte : {answer_text} "
            f"Ta réponse ne doit contenir que l'explication, sans retour à la ligne ni remarque supplémentaire."
        )
    except:
        return "INVALID"

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
        prompt = generate_prompt(line)
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

    # Sauvegarde CSV
    csv_path = OUTPUT_DIR / f"{base_name}_enriched.csv"
    with open(csv_path, "w", encoding="utf-8", newline="") as f:
        csv.writer(f, delimiter="$").writerows(enriched)

    # Sauvegarde JSON
    json_path = OUTPUT_DIR / f"{base_name}.json"
    with open(json_path, "w", encoding="utf-8") as f_json:
        json.dump([parse_csv_line(r) for r in enriched], f_json, ensure_ascii=False, indent=2)

    return csv_path, json_path

# UI
st.set_page_config(page_title="Générateur BIA", layout="centered")
st.title("🧠 Générateur d’explications BIA avec Claude")

api_key = st.text_input("🔑 Clé API Claude (Anthropic)", type="password")
uploaded_files = st.file_uploader("📂 Upload plusieurs fichiers CSV", type="csv", accept_multiple_files=True)

# session_state pour stocker les résultats
if "results" not in st.session_state:
    st.session_state.results = []

# Bouton d’exécution
if api_key and uploaded_files:
    client = anthropic.Anthropic(api_key=api_key)

    if st.button("🧠 Générer les explications pour tous les fichiers"):
        for file in uploaded_files:
            file_bytes = file.read()
            with st.spinner(f"Traitement de {file.name}..."):
                csv_out, json_out = process_csv_bytes(file_bytes, file.name, client)
                st.session_state.results.append((file.name, csv_out, json_out))

# Affichage des résultats
for fname, csv_path, json_path in st.session_state.results:
    with st.expander(f"📁 {fname}", expanded=True):
        with open(csv_path, "rb") as f_csv:
            st.download_button("⬇ Télécharger le CSV", data=f_csv.read(), file_name=csv_path.name, mime="text/csv", key=f"csv-{csv_path.name}")
        with open(json_path, "rb") as f_json:
            st.download_button("⬇ Télécharger le JSON", data=f_json.read(), file_name=json_path.name, mime="application/json", key=f"json-{json_path.name}")

# Zip de tous les JSON
if st.session_state.results:
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zipf:
        for _, _, json_path in st.session_state.results:
            zipf.write(json_path, arcname=json_path.name)
    zip_buffer.seek(0)
    st.download_button("📦 Télécharger tous les JSON (.zip)", data=zip_buffer, file_name="export_json.zip", mime="application/zip", key="zip-all")
