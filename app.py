import openpyxl

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

def validate_file_data(file):
    """
    Funzione di supporto per convalidare i dati contenuti nel file Excel.
    """
    valid_rows = []
    invalid_rows = []

    try:
        wb = openpyxl.load_workbook(file, data_only=True)
        ws = wb["Azure KeyVault"]

        # Estrae i valori verticali (D5:D15)
        valori = [cell[0].value for cell in ws["D5:D15"]]

        chiavi = list(RITModel.model_fields.keys())
        dati_dict = dict(zip(chiavi, valori))

        rit_instance = RITModel(**dati_dict)
        valid_rows.append(rit_instance)

    except ValidationError as e:
        invalid_rows.append(
            ValidationErrorDetail(
                errors=e.errors()
            )
        )
    except Exception as e:
        # Cattura eventuali altri errori (es. foglio mancante, file corrotto)
        return jsonify({
            "valid": False,
            "message": f"Errore durante la lettura del file: {str(e)}",
            "data": [],
            "errors": []
        }), 400

    # Verifica lo stato basandosi sugli errori collezionati
    if not invalid_rows and valid_rows:
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
    """Rotta dedicata solo alla convalida del file excel."""
    if "file" not in request.files:
        return error_response("Nessun file inviato.")

    file = request.files["file"]
    if file.filename == "":
        return error_response("Nessun file selezionato.")
    
    res = validate_file_data(file)

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
        ritm_models = RITModel(**data[0])
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
