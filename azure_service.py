import os
import requests
from dotenv import load_dotenv

from azure.core.credentials import AccessToken, TokenCredential
from azure.mgmt.keyvault import KeyVaultManagementClient
from azure.mgmt.resource.resources import ResourceManagementClient
from azure.mgmt.subscription import SubscriptionClient
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
    Vault,
)

load_dotenv()


class StaticAccessTokenCredential(TokenCredential):
    """
    Adapter che incapsula il Bearer token ricevuto dal FE
    e lo rende compatibile con tutti gli SDK di Azure Management.
    """
    def __init__(self, token: str):
        self._token = token

    def get_token(self, *scopes, **kwargs) -> AccessToken:
        # Se non si conosce la scadenza esatta, si passa un timestamp fittizio nel futuro (es. 24h)
        # o il valore 'exp' parsato dal payload JWT.
        return AccessToken(self._token, expires_on=2147483647)


class AzureKeyVaultService:
    def __init__(self, subscription_id: str, access_token: str):
        self.subscription_id = subscription_id
        self.access_token = access_token

        # Variabili di configurazione lette da .env (non servono più client_id e client_secret)
        self.tenant_id = os.getenv("AZURE_TENANT_ID")
        self.databricks_app_id = os.getenv("DATABRICKS_APP_ID")
        self.group_id_secret = os.getenv("GROUP_SECRET_PERMISSION")

        # ========================================
        # Configurazione Credenziali tramite Token FE
        # ========================================
        self.credential = StaticAccessTokenCredential(self.access_token)

        # Client SDK Azure
        if self.subscription_id:
            self.sub_client = SubscriptionClient(credential=self.credential)
            self.mgmt_client = KeyVaultManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id,
            )
            self.resource_group_client = ResourceManagementClient(
                credential=self.credential,
                subscription_id=self.subscription_id,
            )
        else:
            self.sub_client = None
            self.mgmt_client = None
            self.resource_group_client = None

    # ========================================
    # GESTIONE KEY VAULT
    # ========================================
    def create_or_update_vault(
        self,
        resource_group_name: str,
        vault_name: str,
        location: str,
        acronimo: str,
        servizio: str,
    ) -> Vault:
        """Crea o aggiorna un'istanza di Key Vault in un Resource Group."""
        if not self.mgmt_client or not self.tenant_id:
            raise ValueError("KeyVaultManagementClient o tenant_id non configurati.")

        secrets_permissions_params: list[AccessPolicyEntry] = []

        if servizio == "Databricks":
            databrick_id = self.get_databricks_object_id()
            secrets_permissions_params.append(
                AccessPolicyEntry(
                    tenant_id=self.tenant_id,
                    object_id=databrick_id,
                    permissions=Permissions(
                        secrets=[SecretPermissions.get, SecretPermissions.list]
                    ),
                )
            )

        # Access policy per il gruppo di sicurezza
        if self.group_id_secret:
            secrets_permissions_params.append(
                AccessPolicyEntry(
                    tenant_id=self.tenant_id,
                    object_id=self.group_id_secret,
                    permissions=Permissions(secrets=[SecretPermissions.all]),
                )
            )

        try:
            params = VaultCreateOrUpdateParameters(
                location=location,
                properties=VaultProperties(
                    tenant_id=self.tenant_id,
                    sku=Sku(family="A", name=SkuName.standard.name),  #TODO ricordare di cambiare in premium
                    enable_soft_delete=True,
                    soft_delete_retention_in_days=90,
                    enable_purge_protection=True,
                    enable_rbac_authorization=False,
                    public_network_access=PublicNetworkAccess.DISABLED,
                    network_acls=NetworkRuleSet(
                        bypass="AzureServices",
                        default_action="Deny",
                    ),
                    access_policies=secrets_permissions_params,  # Corretta lista piatta di AccessPolicyEntry
                ),
                tags={"acronimo": acronimo},
            )
            poller = self.mgmt_client.vaults.begin_create_or_update(
                resource_group_name=resource_group_name,
                vault_name=vault_name,
                parameters=params,
            )
            return poller.result()
        except HttpResponseError as e:
            raise ValueError(str(e)) from e

    def check_vault_exists(self, resource_group_name: str, vault_name: str) -> dict:
        """Verifica se uno specifico Key Vault esiste nel Resource Group."""
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
                "sku": vault.properties.sku.name if vault.properties and vault.properties.sku else None,
            }
        except ResourceNotFoundError:
            return {
                "exists": False,
                "vault_name": vault_name,
                "resource_group": resource_group_name,
                "message": f"Key Vault '{vault_name}' non trovato.",
            }

    # ========================================
    # METODI DI VERIFICA AUTOMATION
    # ========================================
    def check_connection(self) -> dict:
        """Verifica la validità dell'access token tramite il client di Subscription."""
        try:
            # Esegue una chiamata leggera ad ARM per testare il token
            subscriptions = list(self.sub_client.subscriptions.list())
            return {
                "status": "success",
                "subscription_id": self.subscription_id or "Non specificata",
                "tenant_id": self.tenant_id or "N/D",
                "authenticated": True,
                "accessible_subscriptions_count": len(subscriptions),
                "message": "Token valido. Accesso ad Azure ARM confermato.",
            }
        except Exception as e:
            return {
                "status": "failed",
                "authenticated": False,
                "error": str(e),
                "message": "Autenticazione fallita: verificare scadenza e permessi del token.",
            }

    # ========================================
    # GESTIONE SUBSCRIPTION
    # ========================================
    def check_status_subscription(self, subscription: str) -> dict:
        """Verifica lo stato della Subscription."""
        try:
            sub_info = self.sub_client.subscriptions.get(subscription)
            return sub_info.as_dict()
        except HttpResponseError as e:
            return {
                "exists": False,
                "subscription": subscription,
                "error": str(e),
            }

    def enable_subscription(self, subscription: str):
        """Riattiva la subscription."""
        try:
            url = (
                f"https://management.azure.com/subscriptions/"
                f"{subscription}/providers/Microsoft.Subscription/"
                f"subscriptions/{subscription}/enable"
                f"?api-version=2021-10-01"
            )

            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }

            response = requests.post(url, headers=headers)
            if not response.ok:
                raise Exception(
                    f"Errore durante l'abilitazione della subscription: "
                    f"{response.status_code} - {response.text}"
                )

            return response.json() if response.content else None
        except Exception as e:
            return {
                "exists": False,
                "subscription": subscription,
                "error": str(e),
            }

    # ========================================
    # GESTIONE RESOURCE GROUP
    # ========================================
    def check_resource_group(self, resource_group_name: str) -> dict:
        """Verifica se il Resource Group esiste."""
        try:
            exists = self.resource_group_client.resource_groups.check_existence(resource_group_name)
            return {
                "exists": exists,
                "resource_group": resource_group_name,
            }
        except HttpResponseError as e:
            return {
                "exists": False,
                "resource_group": resource_group_name,
                "error": str(e),
            }

    # ========================================
    # GESTIONE DATABRICKS
    # ========================================
    def get_databricks_object_id(self) -> str:
        """
        Recupera l'object ID del Service Principal di Databricks tramite Microsoft Graph.
        NOTA: L'access token passato dal FE deve avere lo scope per Microsoft Graph
        (https://graph.microsoft.com/.default) oppure il flusso On-Behalf-Of (OBO).
        """
        try:
            graph_url = f"https://graph.microsoft.com/v1.0/servicePrincipals?$filter=appId eq '{self.databricks_app_id}'"
            headers = {"Authorization": f"Bearer {self.access_token}"}

            response = requests.get(graph_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            if not data.get("value"):
                raise ValueError("Nessun service principal trovato per l'appId fornito.")

            return data["value"][0]["id"]
        except Exception as e:
            raise ValueError(f"Errore nella chiamata a Microsoft Graph: {str(e)}") from e