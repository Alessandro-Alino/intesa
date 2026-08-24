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
    try:
        data = request.get_json()
        
        # ==========================================
        # STEP 1: Parsing immediato in RITModel
        # ==========================================
        print("\n=== INIZIO STEP 1: Parsing in RITModel ===")
        
        # Converti immediatamente i dict in oggetti RITModel
        ritm_models = [RITModel(**item) for item in data]
        
        print(f"✓ Parsing completato con successo")
        print(f"  Numero di elementi: {len(ritm_models)}")
        
        # Ora puoi accedere ai campi direttamente come attributi
        if ritm_models:
            first_rit = ritm_models[0]
            print(f"  Primo elemento:")
            print(f"    - Acronimo: {first_rit.acronimo}")
            print(f"    - Resource Group: {first_rit.resource_group}")
            print(f"    - Key Vault: {first_rit.keyvault_name}")
            print(f"    - Ambiente: {first_rit.ambiente}")
        
        print("=== FINE STEP 1 ===\n")
        
        # Pausa di 5 secondi
        print("⏳ Attesa 5 secondi prima del prossimo step...")
        time.sleep(5)
        
        # ==========================================
        # STEP 2: Verifica autenticazione Azure
        # ==========================================
        print("\n=== INIZIO STEP 2: Verifica Autenticazione Azure ===")
        connection_status = azure_functions.check_azure_authentication()
        print(f"✓ Autenticazione verificata con successo")
        print(f"  Subscription ID: {connection_status.get('subscription_id')}")
        print(f"  Tenant ID: {connection_status.get('tenant_id')}")
        print(f"  Credential Type: {connection_status.get('credential_type')}")
        print("=== FINE STEP 2 ===\n")
        
        # ==========================================
        # STEP 3: Esempio di utilizzo dei dati RITModel
        # ==========================================
        print("\n=== INIZIO STEP 3: Elaborazione dati RITModel ===")
        for i, ritm in enumerate(ritm_models, 1):
            print(f"  Elemento {i}:")
            print(f"    - Key Vault: {ritm.keyvault_name}")
            print(f"    - Resource Group: {ritm.resource_group}")
            print(f"    - Region: {ritm.region}")
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
