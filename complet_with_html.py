import streamlit as st
import csv
import json
import os
import zipfile
import random
import io
from pathlib import Path
import anthropic
import shutil
from time import time

# Chargement du template HTML une seule fois
HTML_TEMPLATE_PATH = Path("loic.html")
html_template = HTML_TEMPLATE_PATH.read_text(encoding="utf-8")


# ======================== PROMPTS ============================
def prompt_v1(question, answer):
    return (
        f"Explique de manière scientifique et précise, en 2 à 3 phrases adaptées au niveau d'un élève de 3e, "
        f"pourquoi la réponse suivante est correcte : "
        f"Question : {question} "
        f"Réponse correcte : {answer} "
        f"Ta réponse ne doit contenir que l'explication, sans retour à la ligne ni remarque supplémentaire."
    )

def prompt_v2(question, answer):
    return (
        "Tu es un professeur en aéronautique chargé d'aider un élève de 3e qui prépare le Brevet d’Initiation Aéronautique (BIA). "
        "Explique en 2 à 3 phrases pourquoi la réponse suivante est scientifiquement correcte, en utilisant les termes techniques vus dans le cadre du BIA "
        "et adaptés à un jeune public, et en vulgarisant si nécessaire. "
        "L’explication doit être concise, rigoureuse, sans retour à la ligne ni mention des mauvaises réponses. "
        f"Voici la question et sa bonne réponse :\n"
        f"Question : {question}\nBonne réponse : {answer}\n"
        "Réponds uniquement par l’explication finale à afficher dans un QCM en ligne."
    )

def get_explanation(prompt, client):
    try:
        response = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=256,
            temperature=0.3,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text.strip().replace("\n", " ")
    except Exception as e:
        return f"[Erreur API : {e}]"

# ============ UTILITAIRES CSV/JSON POUR LA GÉNÉRATION ============
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

def get_selected_prompt():
    try:
        with open("selected_prompt.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "V1"  # Valeur par défaut



def generate_prompt(row, version):
    correct_letter = row[5].strip().upper()
    if correct_letter not in ['A', 'B', 'C', 'D']:
        return "INVALID"
    answer_text = row["ABCDE".index(correct_letter)+1].strip()
    question_text = row[0].strip()
    if not question_text or not answer_text:
        return "INVALID"
    return prompt_v1(question_text, answer_text) if version == "V1" else prompt_v2(question_text, answer_text)

def process_csv_bytes(file_bytes, filename, client, version):
    OUTPUT_DIR = Path("out")
    OUTPUT_DIR.mkdir(exist_ok=True)
    base_name = Path(filename).stem
    lines = list(csv.reader(file_bytes.decode("utf-8").splitlines(), delimiter="$"))
    if lines and "question" in lines[0][0].lower():
        lines = lines[1:]

    enriched = []
    progress_bar = st.progress(0.0, text=f"Génération des explications ({filename})")
    for idx, line in enumerate(lines):
        time.sleep(0.5)  # éviter le timeout
        if len(line) < 7:
            line += [""] * (7 - len(line))
        prompt = generate_prompt(line, version)
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
        progress_bar.progress((idx + 1) / len(lines), text=f"{idx+1}/{len(lines)} explications générées")

    # Sauvegarde
    csv_path = OUTPUT_DIR / f"{base_name}_enriched.csv"
    json_path = OUTPUT_DIR / f"{base_name}.json"
    with open(csv_path, "w", encoding="utf-8", newline="") as f_out:
        csv.writer(f_out, delimiter="$").writerows(enriched)
    with open(json_path, "w", encoding="utf-8") as f_json:
        json.dump([parse_csv_line(row) for row in enriched], f_json, ensure_ascii=False, indent=2)

    return csv_path, json_path

# ====================== INTERFACE ======================
st.set_page_config(page_title="🧠 BIA Claude", layout="wide")
tab1, tab2 = st.tabs(["🔬 Comparer deux prompts", "📄 Générer des fichiers enrichis"])


# --------------- Onglet 1 : Comparateur ----------------
with tab1:
    st.title("🔬 Comparateur de prompts BIA")
    api_key = st.text_input("🔑 Clé API Claude", type="password", key="api1")
    uploaded = st.file_uploader("📄 Fichier CSV BIA (séparateur $)", type="csv", key="file1")

    if api_key and uploaded:
        client = anthropic.Anthropic(api_key=api_key)
        if "index" not in st.session_state:
            st.session_state.index = 0
            st.session_state.lines = []
            st.session_state.scores = []

        if not st.session_state.lines:
            reader = csv.reader(uploaded.read().decode("utf-8").splitlines(), delimiter="$")
            lines = list(reader)
            if lines and "question" in lines[0][0].lower():
                lines = lines[1:]
            st.session_state.lines = lines

        lines = st.session_state.lines
        index = st.session_state.index
        total = len(lines)

        if index < total:
            row = lines[index]
            while len(row) < 7:
                row.append("")
            q_text = row[0].strip()
            correct = row[5].strip().upper()
            answer = row["ABCDE".index(correct)].strip()
            with st.spinner("🧠 Claude génère les deux explications..."):
                exp1 = get_explanation(prompt_v1(q_text, answer), client)
                exp2 = get_explanation(prompt_v2(q_text, answer), client)

            pair = [("Prompt V1", exp1), ("Prompt V2", exp2)]
            random.shuffle(pair)

            st.markdown(f"### Question {index+1}/{total} :")
            st.markdown(f"**{q_text}**")
            st.markdown(f"✅ Réponse correcte : **{answer}**")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"🅰️ {pair[0][1]}")
                if st.button("Je préfère 🅰️", key=f"a{index}"):
                    st.session_state.scores.append(pair[0][0])
                    st.session_state.index += 1
                    st.rerun()
            with col2:
                st.markdown(f"🅱️ {pair[1][1]}")
                if st.button("Je préfère 🅱️", key=f"b{index}"):
                    st.session_state.scores.append(pair[1][0])
                    st.session_state.index += 1
                    st.rerun()
        else:
    
            st.success("🎉 Comparaison terminée ! Résultat :")
            v1 = st.session_state.scores.count("Prompt V1")
            v2 = st.session_state.scores.count("Prompt V2")

            st.markdown(f"🧪 Prompt V1 : {v1} vote(s)")
            st.markdown(f"🎓 Prompt V2 : {v2} vote(s)")

            if v1 > v2:
                st.markdown("🏆 **Prompt V1 préféré**")
            elif v2 > v1:
                st.markdown("🏆 **Prompt V2 préféré**")
            else:
                st.markdown("🤝 Égalité parfaite")

            # 🔍 Affichage explicite des prompts utilisés
            with st.expander("🧠 Afficher les formulations des deux prompts utilisés", expanded=False):
                st.markdown("### ✏️ Prompt V1 utilisé :")
                st.markdown("""
                **Explique de manière scientifique et précise, en 2 à 3 phrases adaptées au niveau d'un élève de 3e,**  
                pourquoi la réponse suivante est correcte.  
                **Question :** [texte]  
                **Réponse correcte :** [texte]  
                Ta réponse ne doit contenir que l’explication, sans retour à la ligne ni remarque supplémentaire.
                """)


                st.markdown("### 🧑‍🏫 Prompt V2 utilisé :")
                st.markdown("""
                **Tu es un expert en aéronautique chargé d'aider un élève de 3e qui prépare le BIA (Brevet d’Initiation Aéronautique).**  
                Explique en 2 à 3 phrases pourquoi la réponse suivante est scientifiquement correcte, en utilisant des termes techniques adaptés à un jeune public, et en vulgarisant si nécessaire.  
                L’explication doit être concise, rigoureuse, sans retour à la ligne, sans reformuler la question ni mentionner les mauvaises réponses.  
                **Voici la question et sa bonne réponse :**  
                Question : ...  
                Bonne réponse : ...  
                Réponds uniquement par l’explication finale à afficher dans un QCM en ligne.
                """)


            # Sauvegarde
            with open("selected_prompt.txt", "w", encoding="utf-8") as f:
                f.write("V1" if v1 >= v2 else "V2")

            st.markdown("🔍 Prompt préféré utilisé pour la génération future : **" + ("V1" if v1 >= v2 else "V2") + "**")

            if st.button("🔄 Recommencer"):
                st.session_state.index = 0
                st.session_state.lines = []
                st.session_state.scores = []

# ---------------- Onglet 2 : Générateur ----------------
with tab2:
    st.title("📄 Générateur de fichiers enrichis BIA")

    api_key2 = st.text_input("🔑 Clé API Claude", type="password", key="api2")
    uploaded_files = st.file_uploader("📂 Charge un ou plusieurs fichiers CSV", type="csv", accept_multiple_files=True, key="file2")
    
    # Lecture du prompt sélectionné (si fichier existe)
    PROMPT_FILE = Path("selected_prompt.txt")
    if PROMPT_FILE.exists():
        previous = PROMPT_FILE.read_text().strip()
        default_index = 0 if previous == "V1" else 1
    else:
        default_index = 0

    # Menu déroulant pour choisir manuellement le prompt
    prompt_choice = st.selectbox(
        "🧠 Choisis le prompt à utiliser pour générer les explications :",
        options=["V1", "V2"],
        index=default_index,
        help="V1 : neutre et synthétique • V2 : contextualisé BIA, plus pédagogique"
    )

    # Affichage du prompt sélectionné
    st.info(f"📌 Prompt sélectionné pour la génération : **{prompt_choice}**")

    # Sauvegarde dans le fichier pour persistance
    PROMPT_FILE.write_text(prompt_choice)

    if "results" not in st.session_state:
        st.session_state.results = []

    PROMPT_FILE = Path("selected_prompt.txt")

    # Lecture de la version précédente si existante
    if PROMPT_FILE.exists():
        previous = PROMPT_FILE.read_text().strip()
        default_index = 0 if previous == "V1" else 1
    else:
        default_index = 0

    if api_key2 and uploaded_files:
        client = anthropic.Anthropic(api_key=api_key2)
        if st.button("🧠 Lancer la génération"):
            version = get_selected_prompt()
            for file in uploaded_files:
                file_bytes = file.read()
                with st.spinner(f"Traitement de {file.name}..."):
                    csv_path, json_path = process_csv_bytes(file_bytes, file.name, client, version)
                    st.session_state.results.append((file.name, csv_path, json_path))

    if st.session_state.results:
        for fname, csv_path, json_path in st.session_state.results:
            with st.expander(f"📁 Résultat pour {fname}", expanded=False):
                st.info(f"📌 Prompt utilisé pour la génération : **{get_selected_prompt()}**")
                with open(csv_path, "rb") as f_csv:
                    st.download_button("⬇ Télécharger CSV", f_csv.read(), file_name=csv_path.name, mime="text/csv", key=f"csv-{fname}")
                with open(json_path, "rb") as f_json:
                    st.download_button("⬇ Télécharger JSON", f_json.read(), file_name=json_path.name, mime="application/json", key=f"json-{fname}")

        # ZIP global
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zipf:
            for _, _, json_path in st.session_state.results:
                zipf.write(json_path, arcname=json_path.name)
        zip_buffer.seek(0)
        st.download_button("📦 Télécharger tous les JSON (.zip)", data=zip_buffer, file_name="export_json.zip", mime="application/zip", key="zip-all")


        # 📦 Génération archive ZIP structurée (avec HTML + JSON)
        def build_zip_with_html(results, template_html):
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zipf:
                for fname, _, json_path in results:
                    base = Path(fname).stem
                    folder = f"{base}/"

                    # Création HTML avec nom de JSON correspondant
                    html_code = template_html.replace("BIA_Annales_2016.json", json_path.name)
                    html_path = json_path.with_suffix(".html")
                    html_path.write_text(html_code, encoding="utf-8")

                    # Ajout au ZIP : dossier + les deux fichiers
                    zipf.write(json_path, arcname=folder + json_path.name)
                    zipf.write(html_path, arcname=folder + html_path.name)

            zip_buffer.seek(0)
            return zip_buffer

        # Bouton téléchargement ZIP structuré
        zip_structured = build_zip_with_html(st.session_state.results, html_template)
        st.download_button(
            "📦 Télécharger tous les dossiers (JSON + HTML)",
            data=zip_structured,
            file_name="quiz_structures.zip",
            mime="application/zip",
            key="zip-html"
        )
