# Azure Key Vault - Guida per Ottenere le Credenziali

## Tabella: Informazioni Tramite Azure CLI

| Variabile | Comando CLI | Output da Utilizzare |
|-----------|-------------|---------------------|
| `AZURE_KEYVAULT_URL` | `az keyvault show --name <nome-vault> --query "properties.vaultUri" --output tsv` | URL completo del vault (es. `https://mia-keyvault.vault.azure.net/`) |
| `AZURE_TENANT_ID` | `az account show --query "tenantId" --output tsv` | ID tenant dell'account Azure |
| `AZURE_CLIENT_ID` | `az ad sp show --id <service-principal-id> --query "appId" --output tsv` | App ID dello Service Principal o dell'app registrata |
| `AZURE_CLIENT_SECRET` | `az ad sp credential reset --id <service-principal-id> --append --query "password" --output tsv` | Password generata per lo Service Principal (mostrata solo alla creazione) |
| `AZURE_SUBSCRIPTION_ID` | `az account show --query "id" --output tsv` | ID della sottoscrizione corrente |

### Nota Importante
Il `AZURE_CLIENT_SECRET` viene mostrato **solo al momento della creazione**. Se lo perdi, devi generarne uno nuovo. Non è possibile recuperarlo dopo la creazione.

---

## Tabella: Informazioni Tramite REST API

| Variabile | Endpoint REST | Parametri Necessari |
|-----------|---------------|---------------------|
| `AZURE_KEYVAULT_URL` | `https://management.azure.com/subscriptions/{subscriptionId}/resourceGroups/{resourceGroupName}/providers/Microsoft.KeyVault/vaults/{vaultName}?api-version=2023-07-01` | Subscription ID, Resource Group Name, Vault Name |
| `AZURE_TENANT_ID` | `https://login.microsoftonline.com/{tenant}/.well-known/openid-configuration` | Tenant ID (può essere noto o estratto dal disco delle identità) |
| `AZURE_CLIENT_ID` | `https://graph.microsoft.com/v1.0/applications?$filter=appId eq '{app-id}'` | Application ID (Client ID) per cercare l'applicazione nell'enrollment |
| `AZURE_CLIENT_SECRET` | `N/A - Non disponibile via REST API` | ⚠️ Non può essere recuperato tramite API, solo generato via CLI/Portal |
| `AZURE_SUBSCRIPTION_ID` | `https://management.azure.com/subscriptions?api-version=2020-01-01` | Token di accesso admin (per elencare tutte le sottoscrizioni) |

### Nota Importante
La `AZURE_CLIENT_SECRET` **NON è mai esposta via REST API** per motivi di sicurezza. Deve essere salvata al momento della creazione. Per ottenere altre informazioni è necessario un token Azure AD con permessi adeguati.
