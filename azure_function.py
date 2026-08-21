from typing import Optional
from azure_service import AzureKeyVaultService

try:
    azure_service = AzureKeyVaultService()
except Exception as e:
    azure_service = None
    print(f"Attenzione: AzureKeyVaultService non inizializzato in azure_function: {e}")


def azure_check_connection() -> dict:
    """
    STEP 1: Autenticazione & Accesso Azure.
    Verifica la configurazione delle credenziali e l'accesso effettivo ad Azure.
    """
    
    try:
        if not azure_service:
            raise ValueError("AzureKeyVaultService non configurato o non disponibile.")
        auth_res = azure_service.check_connection()
        return {
            "step": 1,
            "id": "auth",
            "name": "Autenticazione & Accesso Azure",
            "status": "success",
            "message": auth_res.get("message", "Autenticazione Azure riuscita. Token di accesso ottenuto."),
            "details": auth_res
        }
    except Exception as e:
        return {
            "step": 1,
            "id": "auth",
            "name": "Autenticazione & Accesso Azure",
            "status": "error",
            "message": f"Errore durante l'autenticazione ad Azure: {e!s}",
            "details": {}
        }


def azure_list_key_vaults(resource_group_name: Optional[str] = None) -> dict:
    """
    STEP 2: Verifica lista Key Vault disponibili.
    Elenca i Key Vault presenti nella Subscription o nello specifico Resource Group.
    """

    try:
        if not azure_service:
            raise ValueError("AzureKeyVaultService non configurato o non disponibile.")

        vaults = azure_service.list_vaults(resource_group_name=resource_group_name)
        
        vault_list = []
        for v in vaults:
            rg = resource_group_name
            if not rg and v.id and "/resourceGroups/" in v.id:
                try:
                    rg = v.id.split("/resourceGroups/")[1].split("/")[0]
                except Exception:
                    rg = "N/D"

            sku_name = "standard"
            vault_uri = None
            if hasattr(v, "properties") and v.properties:
                if hasattr(v.properties, "sku") and v.properties.sku:
                    sku_name = v.properties.sku.name
                if hasattr(v.properties, "vault_uri"):
                    vault_uri = v.properties.vault_uri

            vault_list.append({
                "name": v.name,
                "location": v.location,
                "resource_group": rg or "N/D",
                "sku": sku_name,
                "vault_uri": vault_uri
            })

        count = len(vault_list)
        return {
            "step": 2,
            "id": "list_vaults",
            "name": "Lista Key Vault disponibili",
            "status": "success",
            "message": f"Trovati {count} Key Vault disponibili su Azure." if count > 0 else "Nessun Key Vault trovato.",
            "details": {
                "count": count,
                "resource_group": resource_group_name,
                "vaults": vault_list
            }
        }
    except Exception as e:
        return {
            "step": 2,
            "id": "list_vaults",
            "name": "Lista Key Vault disponibili",
            "status": "error",
            "message": f"Errore durante il recupero dei Key Vault: {e!s}",
            "details": {
                "resource_group": resource_group_name
            }
        }
