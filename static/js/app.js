import { createDataTable, createErrorTable } from "./mng_table.js";

// Get references to the DOM elements
const csvFileInput = document.getElementById("csvFileInput");
const btnValidate = document.getElementById("btnValidate");
const btnUpload = document.getElementById("btnUpload");
const btnReset = document.getElementById("btnReset");
const fileName = document.getElementById("fileName");
const outputArea = document.getElementById("outputArea");
const errorArea = document.getElementById("errorArea");
const azurePipelineSection = document.getElementById("azurePipelineSection");

// RITM dal backend
let ritmData = [];

// File Input Event
csvFileInput.addEventListener("change", () => {
  if (csvFileInput.files && csvFileInput.files.length > 0) {
    const file = csvFileInput.files[0];
    fileName.textContent = file.name;
    btnReset.style.display = "block";
  } else {
    resetFileInput();
  }
});

// Reset Event
btnReset.addEventListener("click", () => {
  resetFileInput();
});

// Reset Function
function resetFileInput() {
  csvFileInput.value = "";
  fileName.textContent = "Nessun file selezionato";
  btnReset.style.display = "none";
  azurePipelineSection.style.display = "none";
  outputArea.style.display = "none";
  errorArea.style.display = "none";
}

// Validation Event
btnValidate.addEventListener("click", async () => {
  const file = csvFileInput.files[0];
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

    if (result.valid) {
      // Crea la tabella con i Dati Validati
      createDataTable(result, outputArea);
      // SET UI
      outputArea.style.display = "block";
      errorArea.style.display = "none";
      azurePipelineSection.style.display = "block";
      // SALVA I DATI DELLA RITM
      ritmData = result.data || [];
      console.log('Dati della RITM raccolti: ' + ritmData)
    } else {
      // Crea la tabella con gli Errori
      createErrorTable(result, errorArea);
      // SET UI
      outputArea.style.display = "none";
      errorArea.style.display = "block";
      azurePipelineSection.style.display = "none";
      // RESET DATI RITM
      ritmData = result.data || [];
    }
  } catch (error) {
    errorArea.textContent = "Errore di rete: " + error.message;
    errorArea.style.display = "block";
  }
});


btnUpload.addEventListener("click", async () => {
  // 1. Preparazione UI: stato di caricamento
  btnUpload.disabled = true;
  btnUpload.textContent = "Elaborazione in corso...";

  // Controllo se la RITM Validata è stata passata
  if (ritmData.length === 0) {
    alert("Nessun dato valido da inviare. Esegui prima la validazione.");
    return;
  }

  try {
    // Payload: inviamo l'array di oggetti già validati
    const payload = ritmData;

    // Chiamata Fetch alla route Flask
    const response = await fetch("/upload", {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify(payload)
    });

    const result = await response.json();

    // Gestione della risposta
    if (response.ok && result.status === "success") {
      // SUCCESSO
      azurePipelineSection.style.display = "block";
      outputArea.style.display = "block";
      errorArea.style.display = "none";
      // LOG
      console.log("Provisioning Azure completato con successo:", result);

    } else {
      // ERRORE DAL BACKEND
      azurePipelineSection.style.display = "none";
      errorArea.style.display = "block";
      errorArea.textContent = `Errore: ${result.error || "Errore sconosciuto dal server"}`;

      if (result.details) {
        console.error("Dettagli errore dal server:", result.details);
      }
    }
  } catch (error) {
    // ERRORE DI RETE
    azurePipelineSection.style.display = "none";
    errorArea.style.display = "block";
    errorArea.textContent = "Errore di rete: " + error.message;
    console.error("Errore di fetch:", error);
  } finally {
    // Ripristino del pulsante
    btnUpload.disabled = false;
    btnUpload.textContent = "Avvia Test Azure";
  }
});