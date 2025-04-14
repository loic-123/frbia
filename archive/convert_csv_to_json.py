def batch_convert_all_csv(input_dir, output_dir):
    import pandas as pd
    import json
    from pathlib import Path

    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_files = list(input_dir.glob("*.csv"))
    print(f"🔍 {len(csv_files)} fichier(s) trouvés dans {input_dir}")

    for csv_path in csv_files:
        try:
            df = pd.read_csv(csv_path, sep="$", header=None, encoding="utf-8")
            if df.shape[1] < 8:
                print(f"⚠️  Fichier ignoré (colonnes insuffisantes) : {csv_path.name}")
                continue
            df.columns = ["Question", "A", "B", "C", "D", "Correct Answer", "Image URL", "Explanation"]

            data = []
            for _, row in df.iterrows():
                item = {
                    "question": str(row["Question"]).strip(),
                    "a": str(row["A"]).strip(),
                    "b": str(row["B"]).strip(),
                    "c": str(row["C"]).strip(),
                    "d": str(row["D"]).strip(),
                    "correct": str(row["Correct Answer"]).strip().upper(),
                    "image": None if str(row["Image URL"]).strip().lower() in ["", "none", "null", "nan", "undefined"] else str(row["Image URL"]).strip(),
                    "explanation": str(row["Explanation"]).strip()
                }
                data.append(item)

            json_path = output_dir / csv_path.with_suffix(".json").name
            with open(json_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            print(f"✅ Export JSON : {json_path.name}")
        except Exception as e:
            print(f"❌ Erreur fichier {csv_path.name} : {e}")

    print("🎉 Conversion JSON terminée.")
