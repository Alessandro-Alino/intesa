from functools import wraps
from flask import Flask, jsonify, redirect, render_template, request, url_for
from pydantic import ValidationError

from models import RITModel
from azure_service import AzureKeyVaultService
from processing import error_response, validate_file_data, get_token_from_request

from azure.core.exceptions import ResourceExistsError

app = Flask(__name__)

@app.route("/", methods=["GET"])
def index():
    """Mostra la pagina di login / landing"""
    return render_template("login.html")


@app.route("/azure", methods=["GET"])
def index_azure():
    token = get_token_from_request()

    if not token:
        print("Nessun token trovato. Reindirizzamento a /")
        return redirect(url_for("index"))

    print("Token valido trovato lato Python:", token[:25] + "...")
    return render_template("index.html", token=token)


@app.route("/validate", methods=["POST"])
def validate_file():
    """Rotta dedicata solo alla convalida del file excel."""
    if "file" not in request.files:
        return error_response("Nessun file inviato.")

    file = request.files["file"]
    if file.filename == "":
        return error_response("Nessun file selezionato.")

    if not file.filename.endswith((".xlsx", ".xls")):
        return error_response("Formato file non valido. Caricare un file .xlsx o .xls")

    return validate_file_data(file)


@app.route("/upload", methods=["POST"])
def upload_file():
    """
    Riceve i dati del model RITM già validati in precedenza (formato JSON)
    ed esegue gli step di verifica e configurazione su Azure tramite il token del FE.
    """
    token = get_token_from_request()
    if not token:
        return jsonify({"error": "Non autorizzato. Access token mancante o non valido."}), 401

    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Nessun dato JSON ricevuto"}), 400

        # Supporta sia una lista di record [{'subscription': ...}] sia un singolo dict
        record_data = data[0] if isinstance(data, list) else data
        ritm_models = RITModel(**record_data)
        steps = []

        # Inizializzazione Azure Key Vault Service con il Token ricevuto dal FE
        azure_service = AzureKeyVaultService(
            subscription_id=ritm_models.subscription,
            access_token=token
        )

        # ==========================================
        # STEP 1: Verifica autenticazione Azure
        # ==========================================
        print("\n=== INIZIO STEP 1: Verifica Autenticazione Azure ===")
        connection_status = azure_service.check_connection()
        if not connection_status.get("authenticated", False):
            raise ConnectionError(connection_status.get("message", "Token non valido per Azure ARM"))

        print("✓ Autenticazione verificata con successo")
        print(f"  Subscription ID: {connection_status.get('subscription_id')}")
        print(f"  Tenant ID: {connection_status.get('tenant_id')}")
        print("=== FINE STEP 1 ===\n")

        # ==========================================
        # STEP 2: Verifica stato subscription
        # ==========================================
        print("\n=== INIZIO STEP 2: Verifica stato subscription ===")
        sub_info = azure_service.check_status_subscription(ritm_models.subscription)
        print(f"  Subscription INFO: {sub_info}")

        if isinstance(sub_info, dict) and not sub_info.get("exists", True):
            raise ValueError(f"Impossibile accedere alla Subscription: {sub_info.get('error')}")

        # Estrae lo state sia da dict sia da model SDK
        sub_state = (
            sub_info.get("state") if isinstance(sub_info, dict)
            else getattr(sub_info, "state", "")
        ) or ""

        sub_state_lower = str(sub_state).lower()
        if sub_state_lower == "disabled":
            operation = azure_service.enable_subscription(ritm_models.subscription)
            print(f"  Subscription NEW INFO: {operation}")
            steps.append("Subscription riattivata")
        elif sub_state_lower == "warned":
            raise ValueError("Subscription in stato Warned")
        else:
            steps.append(f"Subscription attiva (stato: {sub_state})")

        # ==========================================
        # STEP 3: Gestione Resource Group
        # ==========================================
        print("\n=== INIZIO STEP 3: Verifica Resource Group ===")
        rs_exist = azure_service.check_resource_group(resource_group_name=ritm_models.resource_group)

        if not rs_exist.get("exists", False):
            print(f"Resource Group: {ritm_models.resource_group} Non esiste")
            raise ValueError("Resource Group non esistente")
        else:
            steps.append(f"Resource Group: {ritm_models.resource_group} trovata")

        # ==========================================
        # STEP 4: Gestione Key Vault
        # ==========================================
        print("\n=== INIZIO STEP 4: Verifica Key Vault ===")
        vault_status = azure_service.check_vault_exists(
            resource_group_name=ritm_models.resource_group,
            vault_name=ritm_models.keyvault_name,
        )

        if not vault_status.get("exists", False):
            print(f"Creazione Key Vault: {ritm_models.keyvault_name}...")
            azure_service.create_or_update_vault(
                resource_group_name=ritm_models.resource_group,
                vault_name=ritm_models.keyvault_name,
                location=ritm_models.region,
                acronimo=ritm_models.acronimo,
                servizio=ritm_models.servizio,
            )
            steps.append("KeyVault Creato")
        else:
            steps.append("KeyVault Esistente")
            raise ValueError("KeyVault esistente")

        # ==========================================
        # Risposta finale al frontend
        # ==========================================
        return jsonify({
            "status": "success",
            "message": "Operazioni completate con successo.",
            "details": {
                "subscription_id": connection_status.get("subscription_id"),
                "tenant_id": connection_status.get("tenant_id"),
                "steps": steps,
            },
        }), 200

    except ResourceExistsError as e:
        if "VaultAlreadyExists" in str(e) or (getattr(e, "error", None) and e.error.code == "VaultAlreadyExists"):
            print(f"⚠️ Il nome del vault è già occupato: {e.message}")
            return jsonify({"error": "Errore di Azure", "details": "Nome del KeyVault già usato a livello globale"}), 409
        return jsonify({"error": "Risorsa Azure già esistente", "details": str(e)}), 409

    except (ValueError, ValidationError) as e:
        print(f"❌ Errore di validazione: {str(e)}")
        return jsonify({"error": "Errore di validazione dati", "details": str(e)}), 400

    except ConnectionError as e:
        print(f"❌ Errore connessione/autenticazione: {str(e)}")
        return jsonify({"error": "Errore di autenticazione Azure", "details": str(e)}), 401

    except Exception as e:
        print(f"❌ Errore imprevisto: {str(e)}")
        return jsonify({"error": f"Errore imprevisto: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(debug=True)