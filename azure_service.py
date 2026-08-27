import os
from typing import Optional, List
from dotenv import load_dotenv
from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.keyvault.secrets import SecretClient, KeyVaultSecret
from azure.mgmt.keyvault import KeyVaultManagementClient
from azure.mgmt.resource.resources import ResourceManagementClient

from azure.mgmt.keyvault.models import (
    Sku,
    SkuName,
    VaultCreateOrUpdateParameters,
    VaultProperties,
    Vault,
)

load_dotenv()

class AzureKeyVaultService:
    def __init__(
        self,
        subscription_id: Optional[str] = None,
        tenant_id: Optional[str] = None,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
    ):
        self.subscription_id = subscription_id or os.getenv("AZURE_SUBSCRIPTION_ID")
        self.tenant_id = tenant_id or os.getenv("AZURE_TENANT_ID")
        client_id = client_id or os.getenv("AZURE_CLIENT_ID")
        client_secret = client_secret or os.getenv("AZURE_CLIENT_SECRET")
                
        # ========================================
        # Configurazione Credenziali 
        # ========================================
        if self.tenant_id and client_id and client_secret:
            self.credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=client_id,
                client_secret=client_secret,
            )
        else:
            self.credential = DefaultAzureCredential()
        
        """# Client per i Resource Group   
        if self.resource_group_client:
            self.resource_group_client = ResourceManagementClient(
                credential = self.credential,
                subscription_id=self.subscription_id,
            )
        else:
            self.resource_group_client = None
            print("AZURE_resource_group_client non impostato: ResourceGroup non disponibile.")"""
        
                
        # Client per Key Vault
        if self.subscription_id:
            self.mgmt_client = KeyVaultManagementClient(
                self.credential, self.subscription_id
            )
        else:
            self.mgmt_client = None
            print("AZURE_SUBSCRIPTION_ID non impostato: KeyVaultManagementClient non disponibile.")

    """# Client per i Secret        
            if self.vault_url:
                self.secret_client = SecretClient(
                    vault_url=self.vault_url, credential=self.credential
                )
            else:
                self.secret_client = None
                print("AZURE_KEYVAULT_URL non impostato: SecretClient non disponibile.")"""
    # ========================================
    # GESTIONE SECRET
    # ========================================
    def set_secret(self, name: str, value: str) -> KeyVaultSecret:
        """Crea o aggiorna un segreto nel Key Vault."""
        if not self.secret_client:
            raise ValueError("SecretClient non inizializzato (manca AZURE_KEYVAULT_URL).")
        return self.secret_client.set_secret(name, value)
    def get_secret(self, name: str) -> str:
        """Recupera il valore di un segreto."""
        if not self.secret_client:
            raise ValueError("SecretClient non inizializzato (manca AZURE_KEYVAULT_URL).")
        return self.secret_client.get_secret(name).value
    def delete_secret(self, name: str):
        """Elimina un segreto."""
        if not self.secret_client:
            raise ValueError("SecretClient non inizializzato (manca AZURE_KEYVAULT_URL).")
        poller = self.secret_client.begin_delete_secret(name)
        return poller.result()
    
    # ========================================
    # GESTIONE KEY VAULT
    # ========================================
    def create_or_update_vault(
        self,
        resource_group_name: str,
        vault_name: str,
        location: str,
    ) -> Vault:
        """Crea o aggiorna un'istanza di Key Vault in un Resource Group."""
        if not self.mgmt_client or not self.tenant_id:
            raise ValueError("KeyVaultManagementClient o tenant_id non configurati.")
        params = VaultCreateOrUpdateParameters(
            location=location,
            properties=VaultProperties(
                tenant_id=self.tenant_id,
                sku=Sku(family="A", name=SkuName.standard.name),
                enable_soft_delete=True,
                soft_delete_retention_in_days=90,
                enable_rbac_authorization=True,
                access_policies=[],
            ),
        )
        poller = self.mgmt_client.vaults.begin_create_or_update(
            resource_group_name=resource_group_name,
            vault_name=vault_name,
            parameters=params,
        )
        return poller.result()
    def get_vault(self, resource_group_name: str, vault_name: str) -> Vault:
        """Recupera le informazioni e lo stato di un Key Vault."""
        if not self.mgmt_client:
            raise ValueError("KeyVaultManagementClient non configurato.")
        return self.mgmt_client.vaults.get(
            resource_group_name=resource_group_name, vault_name=vault_name
        )

    def get_secret_client(self, vault_name_or_url: Optional[str] = None) -> SecretClient:
        """Restituisce un SecretClient per un URL o nome vault specifico, o quello di default."""
        target_url = vault_name_or_url or self.vault_url
        if not target_url:
            raise ValueError("URL o nome del Key Vault non specificato.")
        
        # Se viene passato solo il nome del vault (es. 'kv-isp-test'), costruisci l'URL completo
        if not target_url.startswith("https://"):
            target_url = f"https://{target_url}.vault.azure.net/"
            
        return SecretClient(vault_url=target_url, credential=self.credential)

    # ========================================
    # METODI DI VERIFICA AUTOMATION
    # ========================================
    def check_connection(self) -> dict:
        """Verifica la configurazione delle credenziali e l'accesso effettivo ad Azure tramite token."""
        if not self.credential:
            raise ValueError("Nessuna credenziale configurata.")
        
        # Test di autenticazione: richiediamo un token valido ad Azure
        token = self.credential.get_token("https://management.azure.com/.default")
        
        return {
            "status": "success",
            "subscription_id": self.subscription_id or "Non specificata nel .env",
            "tenant_id": self.tenant_id or "N/D",
            "credential_type": type(self.credential).__name__,
            "authenticated": bool(token.token),
            "message": "Autenticazione Azure riuscita. Token di accesso ottenuto con successo!"
        }

    def check_resource_group(self, resource_group_name: str) -> dict:
        """
        Verifica se il Resource Group è accessibile su Azure.
        Interroga ARM listando le risorse o i vault nel gruppo.
        """
        try:
            # Client per i Resource Group   
            resource_group_client = ResourceManagementClient(
                        credential = self.credential,
                        subscription_id=self.subscription_id,
                    )
            print(f"[AZURE_SERVICE_RS] RS: {resource_group_client}")
            
            rg_exist = resource_group_client.resource_groups.check_existence(resource_group_name=resource_group_name)
            print(f"[AZURE_SERVICE_RS_EXIST] RS_EXIST: {rg_exist}")
            
            if rg_exist:
                # Resorce Group Esiste
                return True
            else:
                # Crea Resorce Group
                return False
            
        except Exception as e:
            err_msg = str(e)
            if "ResourceGroupNotFound" in err_msg or "not found" in err_msg.lower() or "404" in err_msg:
                return {
                    "exists": False,
                    "resource_group": resource_group_name,
                    "message": f"Resource Group '{resource_group_name}' non trovato nella Subscription.",
                    "details": err_msg
                }
            raise e

    def check_vault_exists(self, resource_group_name: str, vault_name: str) -> dict:
        """
        Verifica se uno specifico Key Vault esiste nel Resource Group.
        """
        if not self.mgmt_client:
            raise ValueError("KeyVaultManagementClient non configurato.")

        try:
            vault = self.mgmt_client.vaults.get(
                resource_group_name=resource_group_name, vault_name=vault_name
            )
            return {
                "exists": True,
                "vault_name": vault.name,
                "location": vault.location,
                "vault_uri": vault.properties.vault_uri if vault.properties else None,
                "provisioning_state": vault.properties.provisioning_state if vault.properties else None,
                "sku": vault.properties.sku.name if vault.properties and vault.properties.sku else None
            }
        except Exception as e:
            err_msg = str(e)
            if "ResourceNotFound" in err_msg or "not found" in err_msg.lower() or "404" in err_msg:
                return {
                    "exists": False,
                    "vault_name": vault_name,
                    "resource_group": resource_group_name,
                    "message": f"Key Vault '{vault_name}' non trovato nel Resource Group '{resource_group_name}'."
                }
            raise e

    def secret_operations(self, vault_name_or_url: str, secret_name: str, secret_value: str) -> dict:
        """
        Esegue un test completo di Data Plane: scrittura e lettura di un segreto.
        """
        client = self.get_secret_client(vault_name_or_url)
        # 1. Scrittura
        created_secret = client.set_secret(secret_name, secret_value)
        # 2. Lettura
        retrieved_secret = client.get_secret(secret_name)
        
        return {
            "status": "success",
            "vault": vault_name_or_url,
            "secret_name": created_secret.name,
            "secret_version": created_secret.properties.version if created_secret.properties else None,
            "read_verified": retrieved_secret.value == secret_value,
            "secret_value": retrieved_secret.value
        }

    def list_vaults(self, resource_group_name: Optional[str] = None) -> List[Vault]:
        """Elenca tutti i Key Vault all'interno di un Resource Group o dell'intera Subscription."""
        if not self.mgmt_client:
            raise ValueError("KeyVaultManagementClient non configurato.")
        if resource_group_name:
            return list(
                self.mgmt_client.vaults.list_by_resource_group(
                    resource_group_name=resource_group_name
                )
            )
        try:
            return list(self.mgmt_client.vaults.list_by_subscription())
        except AttributeError:
            return list(self.mgmt_client.vaults.list())