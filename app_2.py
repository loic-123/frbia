import streamlit as st
import pandas as pd
import os
import json
import csv
import zipfile
from pathlib import Path
import anthropic

# Préparation du dossier de sortie
out_dir = Path("out")
out_dir.mkdir(exist_ok=True)

# Nettoyage champ image
def clean_image(image_field):
    if isinstance(image_field, str) and image_field.strip().lower() in ["", "none", "null", "nan", "undefined"]:
        return None
    return image_field.strip()

# Conversion d'une ligne CSV en dictionnaire
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

# Génère un prompt pour Claude
def generate_prompt(row, idx):
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

# Traitement d'un fichier CSV unique
def process_csv_file(uploaded_file, client):
    base_name = Path(uploaded_file.name).stem
    csv_reader = csv.reader(uploaded_file.read().decode("utf-8").splitlines(), delimiter="$")
    lines = list(csv_reader)

    # Suppression éventuelle du header
    if lines and "question" in lines[0][0].lower():
        lines = lines[1:]

    st.write(f"📄 Traitement de **{uploaded_file.name}** ({len(lines)} questions)")
    enriched_lines = []
    progress_bar = st.progress(0, text="Génération des explications...")

    for idx, line in enumerate(lines):
        if len(line) < 7:
            line += [""] * (7 - len(line))
        prompt = generate_prompt(line, idx)
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
        enriched_lines.append(line)
        progress_bar.progress((idx + 1) / len(lines), text=f"{idx+1}/{len(lines)} explications générées")

    # Enregistrement CSV enrichi
    csv_out_path = out_dir / f"{base_name}_enriched.csv"
    with open(csv_out_path, "w", encoding="utf-8", newline="") as f_out:
        writer = csv.writer(f_out, delimiter="$")
        writer.writerows(enriched_lines)

    # Enregistrement JSON
    json_data = [parse_csv_line(row) for row in enriched_lines]
    json_out_path = out_dir / f"{base_name}.json"
    with open(json_out_path, "w", encoding="utf-8") as f_json:
        json.dump(json_data, f_json, ensure_ascii=False, indent=2)

    return csv_out_path, json_out_path

# Création archive zip avec tous les JSON
def zip_all_json_files():
    zip_path = out_dir / "json_exports.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for json_file in out_dir.glob("*.json"):
            zipf.write(json_file, arcname=json_file.name)
    return zip_path

# ========== INTERFACE STREAMLIT ==========
st.set_page_config(page_title="Générateur BIA", layout="centered")
st.title("🧠 Générateur d’explications BIA avec Claude")

api_key = st.text_input("🔑 Clé API Claude (Anthropic)", type="password")
uploaded_files = st.file_uploader("📂 Charge un ou plusieurs fichiers CSV (séparateur $)", type="csv", accept_multiple_files=True)

if api_key and uploaded_files:
    client = anthropic.Anthropic(api_key=api_key)
    if st.button("🧠 Générer toutes les explications"):
        for f in uploaded_files:
            with st.expander(f"📁 Résultat pour {f.name}", expanded=True):
                csv_path, json_path = process_csv_file(f, client)
                with open(csv_path, "rb") as f_csv:
                    st.download_button(
                        label="⬇ Télécharger le CSV enrichi",
                        data=f_csv.read(),
                        file_name=csv_path.name,
                        mime="text/csv",
                        key=f"csv-{csv_path.name}"
                    )

                with open(json_path, "rb") as f_json:
                    st.download_button(
                        label="⬇ Télécharger le JSON",
                        data=f_json.read(),
                        file_name=json_path.name,
                        mime="application/json",
                        key=f"json-{json_path.name}"
    )


        zip_path = zip_all_json_files()
        with open(zip_path, "rb") as zip_file:
            st.download_button(
                "📦 Télécharger tous les JSON en .zip",
                data=zip_file.read(),
                file_name="json_exports.zip",
                mime="application/zip",
                key="zip_download"
            )

