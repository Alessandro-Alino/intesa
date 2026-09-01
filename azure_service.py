import os
from dotenv import load_dotenv
import requests

from azure.identity import ClientSecretCredential, DefaultAzureCredential
from azure.mgmt.keyvault import KeyVaultManagementClient
from azure.mgmt.resource.resources import ResourceManagementClient
from azure.core.exceptions import ResourceNotFoundError, HttpResponseError

from azure.mgmt.keyvault.models import (
    AccessPolicyEntry,
    NetworkRuleSet,
    Permissions,
    PublicNetworkAccess,
    SecretPermissions,
    Sku,
    SkuName,
    VaultCreateOrUpdateParameters,
    VaultProperties,
    Vault 
)

load_dotenv()

class AzureKeyVaultService:
    def __init__(self,subscription_id: str):
        
        self.subscription_id = subscription_id 
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.client_id = os.getenv("AZURE_CLIENT_ID")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET")
        self.databricks_app_id = os.getenv("DATABRICKS_APP_ID")
                
        # ========================================
        # Configurazione Credenziali 
        # ========================================
        if self.tenant_id and self.client_id and self.client_secret:
            self.credential = ClientSecretCredential(
                tenant_id=self.tenant_id,
                client_id=self.client_id,
                client_secret=self.client_secret,
            )
        else:
            self.credential = DefaultAzureCredential()
            
        # Client per Key Vault e ResourceGroup
        if self.subscription_id:
            self.mgmt_client = KeyVaultManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id
                )
            self.resource_group_client = ResourceManagementClient(
                credential = self.credential,
                subscription_id=self.subscription_id
                )
        else:
            self.mgmt_client = None
            self.resource_client = None

    # ========================================
    # GESTIONE KEY VAULT
    # ========================================
    def create_or_update_vault(
        self,
        resource_group_name: str,
        vault_name: str,
        location: str,
        acronimo: str,
        servizio:   str
    ) -> Vault:
        """Crea o aggiorna un'istanza di Key Vault in un Resource Group."""
        if not self.mgmt_client:
            raise ValueError("KeyVaultManagementClient o tenant_id non configurati.")

        databrick_params = []

        if servizio == 'Databricks':
            databrick_id = self.get_databricks_object_id()
            databrick_params = [
                   AccessPolicyEntry(
                       tenant_id=self.tenant_id,
                       object_id=databrick_id,
                       permissions=Permissions(
                           secrets=[SecretPermissions.get, SecretPermissions.list]
                       ),
                   )]
            
        params = VaultCreateOrUpdateParameters(
            location=location,
            properties=VaultProperties(
                tenant_id=self.tenant_id,
                sku=Sku(family="A", name=SkuName.standard.name), #TODO ricordare di cambiare in premium
                enable_soft_delete=True,
                soft_delete_retention_in_days=90,
                enable_purge_protection=True,
                enable_rbac_authorization=False,
                public_network_access=PublicNetworkAccess.DISABLED,
                network_acls=NetworkRuleSet(
                    bypass="AzureServices",
                    default_action="Deny",
                ),
                access_policies=databrick_params,
                ),
            tags={"acronimo":acronimo}
        )
        poller = self.mgmt_client.vaults.begin_create_or_update(
            resource_group_name=resource_group_name,
            vault_name=vault_name,
            parameters=params,
        )
        return poller.result()
        
        
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
        except ResourceNotFoundError:
            return {
                "exists": False,
                "vault_name": vault_name,
                "resource_group": resource_group_name,
                "message": f"Key Vault '{vault_name}' non trovato."
            }

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
        
    # ========================================
    # GESTIONE RESOURCE GROUP
    # ========================================
    def check_resource_group(self, resource_group_name: str) -> dict:
        """
        Verifica se il Resource Group è accessibile su Azure.
        Interroga ARM listando le risorse o i vault nel gruppo.
        """
        try:
            exists = self.resource_group_client.resource_groups.check_existence(resource_group_name)
            return {
                "exists": exists,
                "resource_group": resource_group_name
            }
        except HttpResponseError as e:
            return {
                "exists": False,
                "resource_group": resource_group_name,
                "error": str(e)
            }
        
    def create_resource_group(self, resource_group_name: str,location:str) -> dict:
        """
        Creazione di un nuovo Resource Group.
        """
        try:
            # CORREZIONE: Aggiunto parametro parameters con la location
            rg = self.resource_group_client.resource_groups.create_or_update(
                resource_group_name=resource_group_name,
                parameters={"location": location}
            )
            return {"status": "success", "name": rg.name, "location": rg.location}
        except HttpResponseError as e:
            raise ValueError(f"Impossibile creare il Resource Group: {e.message}") from e
        

    # ========================================
    # GESTIONE DATABRICKS 
    # ========================================
    
    def get_databricks_object_id(self):
        try:
            token = self.credential.get_token("https://graph.microsoft.com/.default").token

            graph_url = f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '{self.databricks_app_id}'"
            headers = {"Authorization": f"Bearer {token}"}

            response = requests.get(graph_url, headers=headers)
            response.raise_for_status() # Lancia eccezione se lo status non è 200
            
            data = response.json()
            if not data.get("value"):
                raise ValueError("Nessun service principal trovato per l'appId fornito.")
                
            return data["value"][0]["id"]
            
        except Exception as e:
            raise ValueError(f"Errore nella chiamata a Microsoft Graph: {str(e)}") from e
            