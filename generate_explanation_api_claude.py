def process_folder_batch(input_dir, output_dir, api_key, model="claude-3-7-sonnet-20250219"):
    import csv
    import pandas as pd
    import anthropic
    import logging
    import time
    from tqdm import tqdm
    from pathlib import Path

    client = anthropic.Anthropic(api_key=api_key)
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # === Setup du logging ===
    logging.basicConfig(
        filename="generation_batch.log",
        filemode="w",
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    # === Fonction de parsing robuste du CSV ===
    def load_csv_with_robust_parsing(path, expected_fields=7):
        rows = []
        with open(path, "r", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter="$")
            for i, line in enumerate(reader):
                if len(line) == expected_fields:
                    rows.append(line)
                elif len(line) == 1 and "$" in line[0]:  # Cas encapsulé entre guillemets
                    # On tente de recouper manuellement
                    split_line = line[0].split("$")
                    if len(split_line) == expected_fields:
                        rows.append(split_line)
                    else:
                        logging.warning(f"Ligne {i+1} mal formée (après split): {line}")
                else:
                    logging.warning(f"Ligne {i+1} ignorée (colonnes: {len(line)}): {line}")
        return rows

    # Fonction pour générer le prompt
    def generate_prompt(row, idx):
        try:
            # Vérification que 'Correct Answer' existe et est de type texte
            raw_letter = row.get('Correct Answer', None)
            if pd.isnull(raw_letter):
                logging.warning(f"Ligne {idx} : champ 'Correct Answer' manquant ou vide.")
                return "INVALID"

            if not isinstance(raw_letter, str):
                logging.warning(f"Ligne {idx} : 'Correct Answer' non texte ({type(raw_letter)}).")
                return "INVALID"

            correct_letter = raw_letter.strip().upper()
            if correct_letter not in ['A', 'B', 'C', 'D']:
                logging.warning(f"Ligne {idx} : lettre de réponse invalide '{correct_letter}'.")
                return "INVALID"

            # Vérifier si la colonne de réponse existe
            if correct_letter not in row or pd.isnull(row[correct_letter]):
                logging.warning(f"Ligne {idx} : colonne réponse '{correct_letter}' manquante ou vide.")
                return "INVALID"

            answer_text = str(row[correct_letter]).strip()
            question_text = str(row.get('Question', '')).strip()

            if not question_text or not answer_text:
                logging.warning(f"Ligne {idx} : question ou réponse vide après nettoyage.")
                return "INVALID"

            logging.info(f"Ligne {idx} : génération du prompt avec réponse '{correct_letter}'.")
            return (
                f"Explique de manière scientifique et précise, en 2 à 3 phrases adaptées au niveau d'un élève de 3e, pourquoi la réponse suivante est correcte : "
                f"Question : {question_text} "
                f"Réponse correcte : {answer_text} "
                f"Ta réponse ne doit contenir que l'explication, sans retour à la ligne ni remarque supplémentaire."
            )

        except Exception as e:
            logging.error(f"Ligne {idx} : exception inattendue dans generate_prompt : {e}")
            return "INVALID"


    # === Liste des modèles disponibles avec la clé API ===
    try:
        available_models = client.models.list()
        logging.info("Modèles disponibles :")
        for model in available_models.data:
            logging.info(f"- {model}")

    except Exception as e:
        logging.error(f"Erreur lors de la récupération des modèles disponibles : {e}")
        available_models = []


    # === Traitement batch de tous les fichiers ===
    for csv_file in input_dir.glob("*.csv"):
        logging.info(f"🔍 Traitement du fichier : {csv_file.name}")
        data = load_csv_with_robust_parsing(csv_file)
        
        df = pd.DataFrame(data, columns=[
            "Question", "A", "B", "C", "D", "Correct Answer", "Image URL"
        ])
        df["explanation"] = ""

        for idx in tqdm(range(len(df)), desc=f"{csv_file.name}"):
            row = df.iloc[idx]
            prompt = generate_prompt(row, idx)
            if prompt == "INVALID":
                df.at[idx, "explanation"] = "[ERREUR - Prompt non généré]"
                continue

            try:
                logging.info(f"Traitement de la ligne {idx+1}/{len(df)} : {row['Question'][:60]}...")
                
                # Appel à l'API Claude
                message = client.messages.create(
                    model="claude-3-7-sonnet-20250219",
                    max_tokens=256,
                    temperature=0.3,
                    messages=[{"role": "user", "content": prompt}]
                )
                explanation = message.content[0].text.strip().replace("\n", " ")
                df.at[idx, "explanation"] = explanation
                logging.info(f"Ligne {idx+1} : OK")

            except Exception as e:
                logging.error(f"Ligne {idx+1} : erreur API {e}")
                df.at[idx, "explanation"] = "[ERREUR - API]"

            time.sleep(0.5)

        # Sauvegarde du fichier enrichi
        output_file = output_dir / csv_file.name.replace(".csv", "_with_explanations.csv")
        df.to_csv(output_file, sep="$", index=False, header=False, encoding="utf-8")
        logging.info(f"✅ Exporté : {output_file}\n")

    print("🎉 Traitement batch terminé.")