# Documentazione Tecnica: AzureKeyVaultService

Un'architettura completa per l'interazione con **Azure Key Vault** in ambiente Python, strutturata per separare la gestione dell'infrastruttura (**Control Plane**) dalla gestione dei dati sensibili (**Data Plane**).

---

## 📋 Indice dei Contenuti

1. [Panoramica Generale](#1-panoramica-generale)
2. [Architettura del Codice](#2-architettura-del-codice)
3. [Analisi Dettagliata dei Componenti](#3-analisi-dettagliata-dei-componenti)
   - [Configurazione e Inizializzazione](#inizializzazione-e-autenticazione)
   - [Pattern Lazy Initialization](#pattern-lazy-initialization)
   - [Data Plane: Gestione dei Segreti](#data-plane-gestione-dei-segreti)
   - [Control Plane: Gestione del Key Vault](#control-plane-gestione-del-key-vault)
4. [Prerequisiti e Dipendenze](#4-prerequisiti-e-dipendenze)
5. [Guida all'Uso ed Esempi Pratici](#5-guida-alluso-ed-esempi-pratici)
6. [Best Practice di Sicurezza](#6-best-practice-di-sicurezza)

---

## 1. Panoramica Generale

La classe `AzureKeyVaultService` funge da **wrapper ad alto livello** per l'SDK ufficiale di Azure per Python (`azure-identity`, `azure-keyvault-secrets`, `azure-mgmt-keyvault`). 

Il suo scopo primario è astrarre e semplificare le interazioni con il servizio Azure Key Vault, fornendo un'interfaccia unificata per:
* **Provisioning e gestione delle risorse**: Creazione, lettura e tracciamento dei Key Vault all'interno di un Resource Group.
* **Ciclo di vita dei segreti**: Inserimento, lettura sicura, elencazione ed eliminazione delle credenziali.
* **Autenticazione Flessibile**: Supporto sia per credenziali esplicite (Service Principal / App Registration) che per strategie trasparenti (Managed Identity, Azure CLI, credenziali di sistema).

---

## 2. Architettura del Codice

La classe suddivide nettamente le operazioni in due ambiti operativi distinti:

```
                          ┌───────────────────────────┐
                          │   AzureKeyVaultService    │
                          └─────────────┬─────────────┘
                                        │
             ┌──────────────────────────┴──────────────────────────┐
             ▼                                                     ▼
  ┌─────────────────────┐                               ┌─────────────────────┐
  │     Data Plane      │                               │    Control Plane    │
  │   (SecretClient)    │                               │(KeyVaultMgmtClient) │
  ├─────────────────────┤                               ├─────────────────────┤
  │ - set_secret()      │                               │ - create_vault()    │
  │ - get_secret()      │                               │ - get_vault()       │
  │ - delete_secret()   │                               │ - list_vaults()     │
  │ - list_secrets()    │                               │                     │
  └─────────────────────┘                               └─────────────────────┘
```

---

## 3. Analisi Dettagliata dei Componenti

### Inizializzazione e Autenticazione

#### `__init__(self, vault_url, subscription_id, tenant_id, client_id, client_secret)`

Il costruttore implementa un meccanismo di risoluzione delle credenziali a due livelli:

1. **Risoluzione dei parametri**: Controlla se i valori vengono passati direttamente all'istanza. In caso contrario, effettua il fallback leggendo le variabili d'ambiente tramite `os.getenv()`.
2. **Selezione della strategia di autenticazione**:
   * **Explicit Credentials (`ClientSecretCredential`)**: Utilizzato se `tenant_id`, `client_id` e `client_secret` sono tutti disponibili. È ideale per ambienti di sviluppo locale con Service Principal dedicato.
   * **Implicit/Fallback Credentials (`DefaultAzureCredential`)**: Se le credenziali esplicite non sono fornite, il sistema tenta automaticamente:
     1. Variabili d'ambiente standard Azure.
     2. **Workload / Managed Identity** (se eseguito in un'App Service, VM o cluster AKS su Azure).
     3. Credenziali dell'utente connesso tramite **Azure CLI** (`az login`).

---

### Pattern Lazy Initialization

Le proprietà `secret_client` e `mgmt_client` utilizzano il pattern **Lazy Initialization** (inizializzazione ritardata) con i decorator `@property`.

```python
@property
def secret_client(self) -> SecretClient: ...

@property
def mgmt_client(self) -> KeyVaultManagementClient: ...
```

#### Vantaggi della Lazy Initialization:
* **Efficienza delle risorse**: I client dell'SDK Azure vengono istanziati unicamente quando viene eseguito un metodo che ne richiede il rispettivo contesto.
* **Isolamento degli errori**: Se un'applicazione deve gestire soltanto i segreti (Data Plane), non fallirà all'avvio se manca `AZURE_SUBSCRIPTION_ID` (richiesto solo per il Control Plane).

---

### Data Plane: Gestione dei Segreti

Questi metodi operano sui dati sensibili archiviati nel Vault tramite la proprietà `secret_client`.

| Metodo | Firma | Descrizione | Gestione Eccezioni |
| :--- | :--- | :--- | :--- |
| `set_secret` | `(name: str, value: str)` | Salva o aggiorna un segreto. | Propaga eccezioni SDK |
| `get_secret` | `(name: str) -> Optional[str]` | Recupera il valore del segreto. | Cattura `ResourceNotFoundError` e restituisce `None`. |
| `delete_secret` | `(name: str)` | Avvia la cancellazione asincrona. | Restituisce un poller LRO (`KeyVaultSecretPoller`). |
| `list_secrets` | `() -> List[SecretProperties]` | Elenca i metadati di tutti i segreti. | Restituisce la lista delle proprietà senza i valori visibili. |

---

### Control Plane: Gestione del Key Vault

Questi metodi operano sulle risorse infrastrutturali di Azure tramite la proprietà `mgmt_client`.

#### `create_or_update_vault(resource_group_name, vault_name, location, tenant_id)`
Crea un nuovo Key Vault o aggiorna la configurazione di uno esistente. Applica di default le seguenti impostazioni:
* **SKU Standard**: `SkuName.standard.name` (famiglia "A").
* **Soft Delete**: Abilitato con un periodo di retention di **90 giorni** (protezione contro eliminazioni accidentali).
* **RBAC Authorization**: `enable_rbac_authorization=True`. Delega la gestione delle autorizzazioni al sistema Azure RBAC anziché alle classiche Access Policies.

#### `get_vault(resource_group_name, vault_name)`
Recupera le informazioni e lo stato operativo del Vault. Se il Vault non esiste, cattura `ResourceNotFoundError` e restituisce `None`.

#### `list_vaults(resource_group_name)`
Restituisce un elenco completo delle risorse Key Vault presenti all'interno dello specifico Resource Group.

---

## 4. Prerequisiti e Dipendenze

Per utilizzare questo script, è necessario installare i seguenti pacchetti Python:

```bash
pip install azure-identity azure-keyvault-secrets azure-mgmt-keyvault python-dotenv
```

### Struttura del file `.env` suggerita

```env
AZURE_KEYVAULT_URL="https://<tuo-vault-name>.vault.azure.net/"
AZURE_SUBSCRIPTION_ID="00000000-0000-0000-0000-000000000000"
AZURE_TENANT_ID="00000000-0000-0000-0000-000000000000"
AZURE_CLIENT_ID="00000000-0000-0000-0000-000000000000"
AZURE_CLIENT_SECRET="vostro_secret_di_sp"
```

---

## 5. Guida all'Uso ed Esempi Pratici

### Esempio 1: Gestione dei Segreti (Data Plane)

```python
from azure_service import AzureKeyVaultService

# Inizializzazione che usa le variabili dal file .env
kv_service = AzureKeyVaultService()

# 1. Scrittura di un segreto
kv_service.set_secret("DatabasePassword", "P@ssw0rdSecure2026!")
print("Segreto salvato con successo.")

# 2. Lettura del segreto
db_pass = kv_service.get_secret("DatabasePassword")
print(f"Valore recuperato: {db_pass}")

# 3. Elenco di tutti i segreti
secrets = kv_service.list_secrets()
for s in secrets:
    print(f"Nome segreto: {s.name}, Abilitato: {s.enabled}")

# 4. Eliminazione
kv_service.delete_secret("DatabasePassword")
```

### Esempio 2: Creazione di un Key Vault (Control Plane)

```python
from azure_service import AzureKeyVaultService

kv_service = AzureKeyVaultService(
    subscription_id="11111111-2222-3333-4444-555555555555"
)

# Creazione di un nuovo Key Vault in West Europe
vault = kv_service.create_or_update_vault(
    resource_group_name="rg-production",
    vault_name="kv-prod-app-01",
    location="westeurope"
)

print(f"Vault creato con ID: {vault.id}")
```

---

## 6. Best Practice di Sicurezza

1. **Uso di Managed Identity in Produzione**: In ambienti di staging/produzione su Azure (App Service, VM, AKS), rimuovere `AZURE_CLIENT_ID` e `AZURE_CLIENT_SECRET` dal `.env`. Lo script utilizzerà automaticamente `DefaultAzureCredential` tramite Managed Identity, eliminando la necessità di archiviare credenziali nel codice.
2. **Principio del Minimo Privilegio (RBAC)**:
   * Per le operazioni sui segreti, assegnare il ruolo **Key Vault Secrets Officer** (o *Secrets User* per sola lettura).
   * Per la creazione dei Vault, assegnare il ruolo **Key Vault Contributor** a livello di Resource Group.
3. **Gestione dei Log**: Evitare di stampare nei log o in console il valore restituito da `get_secret()`.
