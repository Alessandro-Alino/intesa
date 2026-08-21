import io

import pandas as pd
from flask import Flask, jsonify, render_template, request
from pydantic import ValidationError

from models import RITModel, ValidationErrorDetail, ValidationResponse
from azure_service import AzureKeyVaultService
from azure_function import azure_check_connection, azure_list_key_vaults

app = Flask(__name__)

# Inizializzazione Azure Key Vault Service
try:
    azure_service = AzureKeyVaultService()
except Exception as e:
    azure_service = None
    print(f"Attenzione: AzureKeyVaultService non inizializzato: {e}")


# Visualizzare i campi presenti nel file CSV per vedere ✔️
# quali colonne sono presenti e se hanno errori         ✔️
#
# Aggiungere controlli sui campi delle colonne          Da fare
#
# Aggiungere Alert di Conferma                          Da fare
# Aggiungere chiamate API verso Azure                   Da fare ❕
#
#
# Aggiungere scelta del separatore per il file CSV
# Conversione di .xlsx e .csv con separatore ","
# SEMPRE in .csv con separatore ";"
# Sitemazione UI                                        Da fare

# Colonne attese e regole di convalida d'esempio
# REQUIRED_COLUMNS = [
#    "richiedente",
#    "capo_ufficio",
#    "capo_servizio",
#    "po_riferimento",
#    "acronimo",
#    "ambiente",
#    "subscription",
#    "resource_group",
#    "keyvault_name",
#    "region",
#    "servizio",
#]

def validate_csv_data(df):
    """
    Funzione di supporto per convalidare i dati contenuti nel DataFrame.
    Restituisce una lista di stringhe con gli errori trovati.
    """
    # Validazione riga per riga
    records = df.to_dict(orient="records")
    valid_rows = []
    invalid_rows = []

    for index, row in enumerate(records, start=2):
      try:
        model_instance = RITModel(**row)
        valid_rows.append(model_instance)
      except ValidationError as e:
        invalid_rows.append(
          ValidationErrorDetail(
            row=index,
            errors=e.errors()
          )
        )

    # Costruzione della risposta finale
    all_valid = len(invalid_rows) == 0

    if all_valid:
        # SUCCESSO: tutte le righe sono valide
        response = ValidationResponse(
            valid=True,
            message=f"✓ Validazione completata: tutte le {len(valid_rows)} righe sono valide.",
            data=valid_rows
        )
        status_code = 200
    else:
        response = ValidationResponse(
            valid=False,
            message=f"✗ Validazione completata: {len(valid_rows)} righe valide, {len(invalid_rows)} con errori.",
            errors=invalid_rows
        )
        status_code = 400
        print(f"RESPONSE: {response}")
    return jsonify(response.model_dump()), status_code


def isEmpty(colValue):
    value: bool = colValue.isnull().all()
    print(f"isEmpty: {value}\n")
    return value

# --- Helper per risposte di errore ---
def error_response(message: str, status: int = 400):
    resp = ValidationResponse(
        valid=False,
        message=message
    )
    return jsonify(resp.model_dump()), status


@app.route("/", methods=["GET"])
def index():
    """Mostra la pagina di upload"""
    return render_template("index.html")

@app.route("/validate", methods=["POST"])
def validate_file():
    """Rotta dedicata solo alla convalida del file CSV."""

    # 1. Controllo presenza e nome del file
    if "file" not in request.files:
        return error_response("Nessun file inviato.")

    file = request.files["file"]
    if file.filename == "":
        return error_response("Nessun file selezionato.")

    # Lettura del CSV
    try:
        content = file.stream.read().decode("utf-8")
        df = pd.read_csv(io.StringIO(content), sep=";")
    except Exception as e:
        return error_response(f"Errore durante la lettura del file: {e!s}")

    # Controllo che il DataFrame non sia vuoto
    if df.empty:
        return error_response("Il file CSV non contiene dati.")
    # Rimpiazza valori nulli con stringe vuote
    df = df.where(pd.notnull(df), '')
    res = validate_csv_data(df)
    return res


@app.route("/upload", methods=["POST"])
def upload_file():
    """
    Riceve i dati del model RITM già validati in precedenza (formato JSON)
    ed esegue gli step di verifica e configurazione su Azure uno alla volta.
    """
    steps_results = []
    
    # Eventuale payload inviato nel body della richiesta
    payload = request.get_json(silent=True) or {}
    resource_group = payload.get("resource_group") if isinstance(payload, dict) else None

    # ========================================================
    # STEP 1: Autenticazione & Accesso Azure
    # ========================================================
    auth_step = azure_check_connection()
    steps_results.append(auth_step)

    # ========================================================
    # STEP 2: Verifica lista Key Vault disponibili
    # ========================================================
    if auth_step.get("status") == "success":
        vaults_step = azure_list_key_vaults(resource_group_name=resource_group)
        steps_results.append(vaults_step)
    else:
        steps_results.append({
            "step": 2,
            "id": "list_vaults",
            "name": "Lista Key Vault disponibili",
            "status": "skipped",
            "message": "Step saltato: l'autenticazione ad Azure è fallita.",
            "details": {}
        })

    has_errors = any(s["status"] == "error" for s in steps_results)

    return jsonify({
        "success": not has_errors,
        "message": "Tutti gli step sono stati eseguiti con successo." if not has_errors else "Errore durante l'esecuzione degli step.",
        "steps": steps_results
    }), 200 if not has_errors else 400


if __name__ == "__main__":
    app.run(debug=True)
