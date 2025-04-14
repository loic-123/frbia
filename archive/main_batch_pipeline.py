from generate_explanation_api_claude import process_folder_batch
from archive.convert_csv_to_json import batch_convert_all_csv

if __name__ == "__main__":
    # Étape 1 : Génération des explications
    process_folder_batch(
        input_dir="questions_csv_raw",
        output_dir="questions_csv_explanations",
        api_key="key"
    )

    # Étape 2 : Conversion en JSON
    batch_convert_all_csv(
        input_dir="questions_csv_explanations",
        output_dir="questions_json_ready"
    )
