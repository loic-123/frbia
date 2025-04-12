# app_compare_prompts.py
import streamlit as st
import csv
import anthropic
import random

# Prompt 1
def prompt_v1(question, answer):
    return (
        f"Explique de manière scientifique et précise, en 2 à 3 phrases adaptées au niveau d'un élève de 3e, "
        f"pourquoi la réponse suivante est correcte : "
        f"Question : {question} "
        f"Réponse correcte : {answer} "
        f"Ta réponse ne doit contenir que l'explication, sans retour à la ligne ni remarque supplémentaire."
    )

# Prompt 2
def prompt_v2(question, answer):
    return (
        "Tu es un professeur en aéronautique chargé d'aider un élève de 3e qui prépare le Brevet d’Initiation Aéronautique (BIA). "
        "Explique en 2 à 3 phrases pourquoi la réponse suivante est scientifiquement correcte, en utilisant les termes techniques vu dans le cadre du BIA et"
        "adaptés à un jeune public, et en vulgarisant si nécessaire. "
        "L’explication doit être concise, rigoureuse, sans retour à la ligne, sans reformuler la question ni mentionner les mauvaises réponses. "
        f"Voici la question et sa bonne réponse :\n"
        f"Question : {question}\n"
        f"Bonne réponse : {answer}\n"
        "Réponds uniquement par l’explication finale à afficher dans un QCM en ligne."
    )

# Appel Claude API
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

# Configuration Streamlit
st.set_page_config(page_title="🔬 Comparateur de prompts BIA", layout="centered")
st.title("🔬 Comparateur de prompts pour les explications du BIA")

# Auth + upload
api_key = st.text_input("🔑 Clé API Claude (Anthropic)", type="password")
uploaded_file = st.file_uploader("📄 Charge un fichier CSV BIA (séparateur $)", type="csv")

# Session
if "index" not in st.session_state:
    st.session_state.index = 0
    st.session_state.lines = []
    st.session_state.scores = []

# Traitement
if api_key and uploaded_file:
    if not st.session_state.lines:
        reader = csv.reader(uploaded_file.read().decode("utf-8").splitlines(), delimiter="$")
        lines = list(reader)
        if lines and "question" in lines[0][0].lower():
            lines = lines[1:]
        st.session_state.lines = lines

    index = st.session_state.index
    lines = st.session_state.lines
    total = len(lines)

    if index < total:
        row = lines[index]
        while len(row) < 7:
            row.append("")
        q_text = row[0].strip()
        correct = row[5].strip().upper()
        if correct not in "ABCD":
            st.warning("❌ Mauvais format de réponse")
        else:
            answer = row["ABCDE".index(correct)+1].strip()
            client = anthropic.Anthropic(api_key=api_key)

            exp1 = get_explanation(prompt_v1(q_text, answer), client)
            exp2 = get_explanation(prompt_v2(q_text, answer), client)

            pair = [("Prompt V1", exp1), ("Prompt V2", exp2)]
            random.shuffle(pair)

            st.markdown(f"### Question {index+1}/{total}")
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
            st.code(
                "Explique de manière scientifique et précise, en 2 à 3 phrases adaptées au niveau d'un élève de 3e, "
                "pourquoi la réponse suivante est correcte : "
                "Question : [texte] Réponse correcte : [texte] "
                "Ta réponse ne doit contenir que l'explication, sans retour à la ligne ni remarque supplémentaire.",
                language="markdown"
            )

            st.markdown("### 🧑‍🏫 Prompt V2 utilisé :")
            st.code(
                "Tu es un expert en aéronautique chargé d'aider un élève de 3e qui prépare le BIA (Brevet d’Initiation Aéronautique). "
                "Explique en 2 à 3 phrases pourquoi la réponse suivante est scientifiquement correcte, en utilisant des termes techniques "
                "adaptés à un jeune public, et en vulgarisant si nécessaire. "
                "L’explication doit être concise, rigoureuse, sans retour à la ligne, sans reformuler la question ni mentionner les mauvaises réponses. "
                "Voici la question et sa bonne réponse :\n"
                "Question : ...\nBonne réponse : ...\n"
                "Réponds uniquement par l’explication finale à afficher dans un QCM en ligne.",
                language="markdown"
            )

        if st.button("🔄 Recommencer"):
            st.session_state.index = 0
            st.session_state.lines = []
            st.session_state.scores = []

