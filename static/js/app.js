import { createDataTable, createErrorTable } from "./mng_table.js";

// Get references to the DOM elements
const csvFileInput = document.getElementById("csvFileInput");
const btnValidate = document.getElementById("btnValidate");
const btnUpload = document.getElementById("btnUpload");
const btnReset = document.getElementById("btnReset");
const fileName = document.getElementById("fileName");
const outputArea = document.getElementById("outputArea");
const errorArea = document.getElementById("errorArea");

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
  btnUpload.style.display = "none";
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
      btnUpload.style.display = "block";
    } else {
      // Crea la tabella con gli Errori
      createErrorTable(result, errorArea);
      // SET UI
      outputArea.style.display = "none";
      errorArea.style.display = "block";
      btnUpload.style.display = "none";
    }
  } catch (error) {
    errorArea.textContent = "Errore di rete: " + error.message;
    errorArea.style.display = "block";
  }
});


