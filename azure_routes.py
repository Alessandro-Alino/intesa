""" from flask import Blueprint, request, jsonify
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError
from azure_service import AzureKeyVaultService

# Definizione del Blueprint con prefisso opzionale
azure_bp = Blueprint("azure_api", __name__, url_prefix="/api/azure")

# Inizializzazione del servizio Key Vault
try:
    vault_service = AzureKeyVaultService()
except Exception as e:
    vault_service = None
    print(f"Errore inizializzazione Azure Key Vault: {e}")


@azure_bp.route("/secrets", methods=["POST"])
def create_secret():
    
    if not vault_service:
        return jsonify({"error": "Servizio Azure Key Vault non configurato."}), 500

    data = request.get_json()
    if not data or "name" not in data or "value" not in data:
        return jsonify({"error": "I campi 'name' e 'value' sono obbligatori."}), 400

    try:
        secret = vault_service.set_secret(data["name"], data["value"])
        return jsonify({
            "message": "Segreto creato con successo",
            "name": secret.name,
            "version": secret.properties.version
        }), 201
    except HttpResponseError as e:
        return jsonify({"error": "Errore Azure", "details": str(e)}), 500


@azure_bp.route("/secrets/<secret_name>", methods=["GET"])
def get_secret(secret_name):
    
    if not vault_service:
        return jsonify({"error": "Servizio Azure Key Vault non configurato."}), 500

    try:
        secret_value = vault_service.get_secret(secret_name)
        return jsonify({
            "name": secret_name,
            "value": secret_value
        }), 200
    except ResourceNotFoundError:
        return jsonify({"error": f"Segreto '{secret_name}' non trovato."}), 404
    except HttpResponseError as e:
        return jsonify({"error": "Errore Azure", "details": str(e)}), 500


@azure_bp.route("/secrets/<secret_name>", methods=["DELETE"])
def delete_secret(secret_name):
    
    if not vault_service:
        return jsonify({"error": "Servizio Azure Key Vault non configurato."}), 500

    try:
        vault_service.delete_secret(secret_name)
        return jsonify({"message": f"Segreto '{secret_name}' eliminato con successo."}), 200
    except ResourceNotFoundError:
        return jsonify({"error": f"Segreto '{secret_name}' non trovato."}), 404
    except HttpResponseError as e:
        return jsonify({"error": "Errore Azure", "details": str(e)}), 500 """