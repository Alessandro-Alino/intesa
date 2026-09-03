/* Crea una tabella per mostrare i dati validati */
export function createDataTable(result, container) {
  // Reset Container
  container.textContent = "";

  const dataList = result.data || [];
  if (dataList.length === 0) {
    container.textContent = "Nessun dato valido da mostrare.";
    return;
  }

  // Per ogni record, crea una tabella verticale
  dataList.forEach((record, index) => {
    // Crea un contenitore per il record
    const recordContainer = document.createElement("div");
    recordContainer.className = "record-container";

    // Titolo del record
    const title = document.createElement("h4");
    title.textContent = `Valori RITM`;
    recordContainer.appendChild(title);

    // Crea la tabella per questo record
    const table = document.createElement("table");
    table.className = "data-table-vertical";

    const tbody = document.createElement("tbody");

    // Itera su ogni campo del record
    const fieldNames = Object.keys(record);
    fieldNames.forEach((field) => {
      const row = document.createElement("tr");

      // Cella del nome del campo (colonna 1)
      const tdField = document.createElement("td");
      tdField.textContent = field;
      tdField.className = "field-name";

      // Cella del valore (colonna 2)
      const tdValue = document.createElement("td");
      const value = record[field];
      tdValue.textContent = value;
      tdValue.className = "field-value";

      row.appendChild(tdField);
      row.appendChild(tdValue);
      tbody.appendChild(row);
    });

    table.appendChild(tbody);
    recordContainer.appendChild(table);
    container.appendChild(recordContainer);

    // Aggiungi un separatore tra i record (se non è l'ultimo)
    if (index < dataList.length - 1) {
      const separator = document.createElement("hr");
      separator.className = "record-separator";
      container.appendChild(separator);
    }
  });
}

/* Crea una tabella degli errori raggruppati per tipo */
export function createErrorTable(result, container) {
  // Reset Container
  container.textContent = "";

  // Se non ci sono errori, mostra un messaggio
  const errorsList = result.errors || [];
  if (errorsList.length === 0) {
    container.textContent = "Nessun errore dettagliato.";
    return;
  }

  // Raggruppa gli errori per tipo (es. "missing", "literal_error", ...)
  const map = new Map();

  errorsList.forEach((rowError) => {
    rowError.errors.forEach((singleError) => {
      const type = singleError.type;
      const field = singleError.loc.join(".");
      if (!map.has(type)) {
        map.set(type, new Set());
      }
      map.get(type).add(field);
    });
  });

  // Crea la tabella
  const table = document.createElement("table");
  table.className = "error-table";

  // Header
  const thead = document.createElement("thead");
  const headerRow = document.createElement("tr");

  const thType = document.createElement("th");
  thType.textContent = "Tipo errore";

  const thValues = document.createElement("th");
  thValues.textContent = "Valori";

  headerRow.appendChild(thType);
  headerRow.appendChild(thValues);
  thead.appendChild(headerRow);
  table.appendChild(thead);

  // Body
  const tbody = document.createElement("tbody");

  for (const [type, fieldsSet] of map) {
    const fields = Array.from(fieldsSet)

    for (let i = 0; i < fields.length; i++) {
      const row = document.createElement("tr");

      // Solo per la prima riga del gruppo: aggiungi la cella del tipo con rowspan
      if (i === 0) {
        const tdType = document.createElement("td");
        tdType.textContent = type;
        tdType.rowSpan = fields.length;
        row.appendChild(tdType);
      }

      // Cella del valore (sempre presente)
      const tdValues = document.createElement("td");
      tdValues.textContent = fields[i];
      row.appendChild(tdValues);

      tbody.appendChild(row);
    }
  }

  table.appendChild(tbody);
  container.appendChild(table);
}
