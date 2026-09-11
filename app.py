
from flask import Flask, jsonify, render_template, request
from pydantic import ValidationError

from models import RITModel
from azure_service import AzureKeyVaultService
from processing import error_response, validate_file_data

from azure.core.exceptions  import (
    ResourceExistsError
)

app = Flask(__name__)

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

    # Controllo estensione
    if not file.filename.endswith(('.xlsx', '.xls')):
        return error_response("Formato file non valido. Caricare un file .xls")
    
    return validate_file_data(file)


@app.route("/upload", methods=["POST"])
def upload_file():
    """
    Riceve i dati del model RITM già validati in precedenza (formato JSON)
    ed esegue gli step di verifica e configurazione su Azure uno alla volta.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Nessun dato JSON ricevuto"}), 400
        
             # Converti immediatamente i dict in oggetti RITModel
        ritm_models = RITModel(**data[0])
        steps = []
        
        # Inizializzazione Azure Key Vault Service
        azure_service = AzureKeyVaultService(subscription_id=ritm_models.subscription)
        
        # ==========================================
        # STEP 1: Verifica autenticazione Azure
        # ==========================================
        print("\n=== INIZIO STEP 1: Verifica Autenticazione Azure ===")
        connection_status = azure_service.check_connection()
        print(f"✓ Autenticazione verificata con successo")
        print(f"  Subscription ID: {connection_status.get('subscription_id')}")
        print(f"  Tenant ID: {connection_status.get('tenant_id')}")
        print(f"  Credential Type: {connection_status.get('credential_type')}")
        print("=== FINE STEP 1 ===\n")
        
        # ==========================================
        # STEP 2: Verifica stato subscription
        # ==========================================
        print("\n=== INIZIO STEP 2: Verifica stato subscription ===")
        sub_info = azure_service.check_status_subscription(ritm_models.subscription)
        print(f"  Subscription INFO: {str(sub_info)}")
        print(f"  Subscription STATUS: {sub_info.state}")
        if sub_info.state.lower() == "disabled":
            operation = azure_service.enable_subscription(ritm_models.subscription)
            print(f"  Subscription NEW INFO: {str(operation)}")
            steps.append('Subscription riattivata')
        if sub_info.state.lower() == "warned":
            raise ValueError("SubScription in stato Warned")
        else:
            steps.append('Subscription già attiva')
        
        
        # ==========================================
        # STEP 3: Esempio di utilizzo dei dati RITModel
        # ==========================================
        print("\n=== INIZIO STEP 2: Elaborazione dati RITModel ===")
        #PRINT
        print(f"Key Vault: {ritm_models.keyvault_name}")
        print(f"Resource Group: {ritm_models.resource_group}")
        print(f"Region: {ritm_models.region}")
        print("=== FINE STEP 2 ===\n")
        
        # ==========================================
        # STEP 4: Esempio di utilizzo dei dati RITModel
        # ==========================================
        print("\n=== INIZIO STEP 3: Stampa lista dei Resource Group ===")
        print(f"Check se il resource group esiste: {ritm_models.resource_group}")

        # 1. Gestione Resource Group
        rs_exist = azure_service.check_resource_group(
            resource_group_name=ritm_models.resource_group
            )
        if not rs_exist.get("exists", False):
            print(f"Creazione Resource Group: {ritm_models.resource_group}...")
            azure_service.create_resource_group(
                resource_group_name=ritm_models.resource_group,
                location=ritm_models.region 
            )
            steps.append('Resource Group Creata')
        else:
            steps.append('Resource Group Esistente')
        
        # 2. Gestione Key Vault
        vault_status = azure_service.check_vault_exists(
            resource_group_name=ritm_models.resource_group, 
            vault_name=ritm_models.keyvault_name
        )
        
        
        if not vault_status.get("exists", False):
            print(f"Creazione Key Vault: {ritm_models.keyvault_name}...")
            azure_service.create_or_update_vault(
                resource_group_name=ritm_models.resource_group,
                vault_name=ritm_models.keyvault_name,
                location=ritm_models.region,
                acronimo=ritm_models.acronimo,
                servizio=ritm_models.servizio
            )
            steps.append('KeyVault Creato')
        else:
            steps.append('KeyVault Esistente')
                
        print(f"Esito = {rs_exist}")
        print("=== FINE STEP 3 ===\n")
        # ==========================================
        # Risposta finale al frontend
        # ==========================================
        return jsonify({
            "status": "success",
            "message": f"Check completati. File processato.",
            "details": {
                "subscription_id": connection_status["subscription_id"],
                "tenant_id": connection_status["tenant_id"],
                "credential_type": connection_status["credential_type"],
                "steps" : steps
            }
        }), 200
    
    except ResourceExistsError as e:
        if "VaultAlreadyExists" in str(e) or (e.error and e.error.code == "VaultAlreadyExists"):
            print(f"⚠️ Il nome del vault è già occupato. Dettaglio: {e.message}")
            return jsonify({"error": "Errore di Azure", "details": 'Nome del KeyVault già usato'}), 517
            
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
