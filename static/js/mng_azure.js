
const azureAuthStatus = document.getElementById("azureAuthStatus");
const azureAuthDetails = document.getElementById("azureAuthDetails");
const azureAuthMessage = document.getElementById("azureAuthMessage");
const btnCheckAzureAuth = document.getElementById("btnCheckAzureAuth");

// Aggiorna la card dello Step 1 (Autenticazione & Accesso Azure).
export function updateAzureStep1(stepData) {
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
      <span>${stepData.message || "Impossibile autenticarsi su Azure con le credenziali fornite."}</span>
    `;
  }
}
