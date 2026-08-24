// Selezione degli elementi DOM (una sola volta)
const azureAuthStatus = document.getElementById("azureAuthStatus");
const azureAuthDetails = document.getElementById("azureAuthDetails");
const azureAuthMessage = document.getElementById("azureAuthMessage");
const btnCheckAzureAuth = document.getElementById("btnCheckAzureAuth");

// Funzione per aggiornare la UI dello Step 1
export function azureAuthStep(stepData) {
  if (!azureAuthStatus || !azureAuthDetails || !azureAuthMessage) return;

  azureAuthDetails.style.display = "block";

  if (stepData.status === "success") {
    azureAuthStatus.className = "status-badge status-success";
    azureAuthStatus.textContent = "Connesso ✓";

    const details = stepData.details || {};
    azureAuthMessage.innerHTML = `
      <strong>${stepData.message || "Autenticazione riuscita."}</strong>
      <div style="margin-top: 6px; font-size: 0.9em; color: #475569;">
        <span>Tipo Credenziale: <code>${details.credential_type || "N/D"}</code></span> | 
        <span>Tenant ID: <code>${details.tenant_id || "N/D"}</code></span> | 
        <span>Subscription: <code>${details.subscription_id || "N/D"}</code></span>
      </div>
    `;
  } else {
    azureAuthStatus.className = "status-badge status-error";
    azureAuthStatus.textContent = "Errore ✗";
    azureAuthMessage.innerHTML = `
      <strong style="color: #b91c1c;">Errore di autenticazione ad Azure:</strong><br>
      <span>${stepData.message || "Impossibile autenticarsi su Azure."}</span>
    `;
  }
}

// ==========================================
// EVENT LISTENER PER IL PULSANTE
// ==========================================
btnCheckAzureAuth.addEventListener("click", async () => {
  // 1. Imposta lo stato a "In attesa / Caricamento"
  azureAuthStatus.className = "status-badge status-pending";
  azureAuthStatus.textContent = "Verifica in corso...";
  azureAuthDetails.style.display = "block";
  azureAuthMessage.innerHTML = "Contatto con il server Flask in corso...";
  btnCheckAzureAuth.disabled = true; // Disabilita il pulsante per evitare doppi click

  try {
    // 2. Payload: inviamo un array vuoto per testare SOLO la connessione Azure 
    // (Il backend accetterà 0 elementi ma farà comunque il check delle credenziali)
    const payload = []; 

    // 3. Chiamata Fetch alla route Flask
    const response = await fetch("/upload", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    // 4. Parsing della risposta JSON
    const result = await response.json();

    // 5. Aggiornamento della UI in base all'esito
    if (response.ok && result.status === "success") {
      azureAuthStep({
        status: "success",
        message: result.message,
        details: result.details // Contiene subscription_id, tenant_id, credential_type
      });
    } else {
      azureAuthStep({
        status: "error",
        message: result.error || "Errore sconosciuto dal server",
        details: result.details || {}
      });
    }
  } catch (error) {
    // Gestisce errori di rete (es. server Flask spento)
    azureAuthStep({
      status: "error",
      message: "Impossibile raggiungere il server. Verifica che Flask sia in esecuzione.",
      details: { error: error.message }
    });
  } finally {
    // 6. Riabilita sempre il pulsante alla fine, sia in caso di successo che di errore
    btnCheckAzureAuth.disabled = false;
  }
});