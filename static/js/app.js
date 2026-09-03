import { createDataTable, createErrorTable } from "./mng_table.js";

// Riferimenti DOM statici
const fileInput = document.getElementById("FileInput");
const btnValidate = document.getElementById("btnValidate");
const btnReset = document.getElementById("btnReset");
const fileName = document.getElementById("fileName");
const outputArea = document.getElementById("outputArea");
const errorArea = document.getElementById("errorArea");
const azurePipelineSection = document.getElementById("azurePipelineSection");
const stepAzureAuth = document.getElementById("stepAzureAuth");

// Helper per riferimenti DOM dinamici (evita elementi scollegati dopo il reset)
const getBtnUpload = () => document.getElementById("btnUpload");
const getAzureAuthStatus = () => document.getElementById("azureAuthStatus");

// Stato RITM dal backend
let ritmData = [];

// --- EVENT LISTENERS ---

fileInput.addEventListener("change", () => {
  if (fileInput.files?.length > 0) {
    fileName.textContent = fileInput.files[0].name;
    btnReset.style.display = "block";
  } else {
    resetFileInput();
  }
});

btnReset.addEventListener("click", resetFileInput);
btnValidate.addEventListener("click", handleValidation);

// Event Delegation per gestire il click di #btnUpload anche dopo la ricreazione dell'HTML
stepAzureAuth.addEventListener("click", (e) => {
  if (e.target && e.target.id === "btnUpload") {
    handleUpload();
  }
});

// --- FUNZIONI LOGICHE ---

function resetFileInput() {
  fileInput.value = "";
  fileName.textContent = "Nessun file selezionato";
  btnReset.style.display = "none";
  azurePipelineSection.style.display = "none";
  outputArea.style.display = "none";
  errorArea.style.display = "none";
  ritmData = [];

  // Ripristina lo Step 1 iniziale
  stepAzureAuth.innerHTML = `
    <div class="step-header">
      <div class="step-number">1</div>
      <div class="step-info">
        <h3>Elaborazione Ritm</h3>
      </div>
      <div class="step-action">
        <button id="btnUpload" class="primary-btn" type="button">Avvia Azure</button>
      </div>
      <div class="step-status">
        <span id="azureAuthStatus" class="status-badge status-pending">In attesa</span>
      </div>
    </div>
  `;
}

async function handleValidation() {
  const file = fileInput.files[0];
  if (!file) {
    alert("Seleziona un file!");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  try {
    const response = await fetch("/validate", {
      method: "POST",
      body: formData,
    });
    const result = await response.json();

    ritmData = result.data || [];

    if (result.valid) {
      createDataTable(result, outputArea);
      outputArea.style.display = "block";
      errorArea.style.display = "none";
      azurePipelineSection.style.display = "block";
      console.log("Dati della RITM raccolti:", ritmData);
    } else {
      createErrorTable(result, errorArea);
      outputArea.style.display = "none";
      errorArea.style.display = "block";
      azurePipelineSection.style.display = "none";
    }
  } catch (error) {
    errorArea.textContent = "Errore di rete: " + error.message;
    errorArea.style.display = "block";
  }
}

async function handleUpload() {
  // Controllo preventivo PRIMA di modificare la UI
  if (ritmData.length === 0) {
    alert("Nessun dato valido da inviare. Esegui prima la validazione.");
    return;
  }

  const btnUpload = getBtnUpload();
  const azureAuthStatus = getAzureAuthStatus();

  // Stato UI: Caricamento
  if (btnUpload) btnUpload.disabled = true;
  if (azureAuthStatus) {
    azureAuthStatus.textContent = "Processing";
    azureAuthStatus.className = "status-badge status-running";
  }

  try {
    const response = await fetch("/upload", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ritmData),
    });

    const result = await response.json();

    if (response.ok && result.status === "success") {
      azurePipelineSection.style.display = "block";
      outputArea.style.display = "block";
      errorArea.style.display = "none";

      if (btnUpload) btnUpload.style.display = "none";
      if (azureAuthStatus) {
        azureAuthStatus.textContent = "Done";
        azureAuthStatus.className = "status-badge status-success";
      }

      result.details?.steps?.forEach((step, index) => createSteps(step, index, true));
      console.log("Provisioning Azure completato con successo:", result);
    } else {
      handleUploadError(result.details);
      if (result.details) console.error("Dettagli errore dal server:", result.details);
    }
  } catch (error) {
    handleUploadError(error.message || error);
    console.error("Errore di fetch:", error);
  }
}

function handleUploadError(errorMsg) {
  const btnUpload = getBtnUpload();
  const azureAuthStatus = getAzureAuthStatus();

  azurePipelineSection.style.display = "block";
  if (btnUpload) btnUpload.style.display = "none";
  if (azureAuthStatus) {
    azureAuthStatus.textContent = "Error";
    azureAuthStatus.className = "status-badge status-error";
  }

  createSteps(errorMsg, 0, false);
}

function createSteps(step, index, isSuccess = true) {
  const divHeader = document.createElement("div");
  divHeader.classList.add("step-header");

  if (isSuccess) {
    divHeader.innerHTML = `
      <div class="step-number">${index + 2}</div>
      <div class="step-info">
        <h3>${step}</h3>
      </div>
      <div class="step-status">
        <span class="status-badge status-success">Done</span>
      </div>
    `;
  } else {
    divHeader.innerHTML = `
      <div class="step-info" style="color: white; margin-top: 30px; padding: 20px; border: 1px solid red; background-color: #ff9191;">
        <h3>${step}</h3>
      </div>
    `;
  }

  stepAzureAuth.appendChild(divHeader);
}