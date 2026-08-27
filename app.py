import io
import time

import pandas as pd
from flask import Flask, jsonify, render_template, request
from pydantic import ValidationError

import azure_functions
from models import RITModel, ValidationErrorDetail, ValidationResponse
from azure_service import AzureKeyVaultService
from azure_functions import AzureFunctions

app = Flask(__name__)

# Inizializzazione Azure Key Vault Service
try:
    azure_service = AzureKeyVaultService()
except Exception as e:
    azure_service = None
    print(f"Attenzione: AzureKeyVaultService non inizializzato: {e}")

# Inizializza la classe AzureFunctions passando il servizio
azure_functions = AzureFunctions(azure_service)

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
    try:
        data = request.get_json()
        
        # Converti immediatamente i dict in oggetti RITModel
        ritm_models = [RITModel(**item) for item in data]
        ritm_models = ritm_models[0]
        # ==========================================
        # STEP 1: Verifica autenticazione Azure
        # ==========================================
        print("\n=== INIZIO STEP 1: Verifica Autenticazione Azure ===")
        connection_status = azure_functions.check_azure_authentication()
        print(f"✓ Autenticazione verificata con successo")
        print(f"  Subscription ID: {connection_status.get('subscription_id')}")
        print(f"  Tenant ID: {connection_status.get('tenant_id')}")
        print(f"  Credential Type: {connection_status.get('credential_type')}")
        print("=== FINE STEP 1 ===\n")
        
        # ==========================================
        # STEP 2: Esempio di utilizzo dei dati RITModel
        # ==========================================
        print("\n=== INIZIO STEP 2: Elaborazione dati RITModel ===")
        #PRINT
        print(f"Key Vault: {ritm_models.keyvault_name}")
        print(f"Resource Group: {ritm_models.resource_group}")
        print(f"Region: {ritm_models.region}")
        print("=== FINE STEP 2 ===\n")
        
        # ==========================================
        # STEP 3: Esempio di utilizzo dei dati RITModel
        # ==========================================
        print("\n=== INIZIO STEP 3: Stampa lista dei Resource Group ===")
        #PRINT
        print(f"Check se il resource group esiste: {ritm_models.resource_group}")
        rs_exist = azure_service.check_resource_group(resource_group_name=ritm_models.resource_group)
        print(f"Esito = {rs_exist}")
        print("=== FINE STEP 3 ===\n")
        
        # ==========================================
        # Risposta finale al frontend
        # ==========================================
        return jsonify({
            "status": "success",
            "message": f"Check completati. {len(ritm_models)} elementi processati.",
            "details": {
                "subscription_id": connection_status["subscription_id"],
                "tenant_id": connection_status["tenant_id"],
                "credential_type": connection_status["credential_type"],
                "processed_items": len(ritm_models)
            }
        }), 200
        
    except (ValueError, ValidationError) as e:
        print(f"❌ Errore di validazione dati: {str(e)}")
        return jsonify({"error": "Errore di validazione dati", "details": str(e)}), 400
        
    except ConnectionError as e:
        print(f"❌ Errore di connessione Azure: {str(e)}")
        return jsonify({"error": "Errore di connessione Azure", "details": str(e)}), 500
        
    except Exception as e:
        print(f"❌ Errore imprevisto: {str(e)}")
        return jsonify({"error": f"Errore imprevisto: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True)
