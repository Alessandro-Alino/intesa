import csv


def elabora_csv(filepath):
    """
    Legge il CSV, esegue controlli di base e restituisce un dizionario
    con i risultati. Qui si possono aggiungere facilmente altre funzioni.
    """
    risultati = {"righe_totali": 0, "colonne": [], "prime_righe": [], "errori": []}

    try:
        with open(filepath, mode="r", encoding="utf-8") as f:
            lettore = csv.reader(f)
            # Leggi l'intestazione (se presente)
            try:
                intestazione = next(lettore)
                risultati["colonne"] = intestazione
            except StopIteration:
                risultati["errori"].append("Il file è vuoto.")
                return risultati

            # Conta righe e salva le prime 5 per anteprima
            righe = list(lettore)
            risultati["righe_totali"] = len(righe)
            risultati["prime_righe"] = righe[:5]

            # Controlli aggiuntivi (esempio: presenza di colonne obbligatorie)
            if "id" not in intestazione and "nome" not in intestazione:
                risultati["errori"].append(
                    "Mancano colonne 'id' o 'nome' (esempio di controllo)."
                )

            # Altri controlli personalizzati...
            # Esempio: controlla che non ci siano righe vuote
            for i, riga in enumerate(righe, start=2):  # +1 per l'intestazione
                if all(campo.strip() == "" for campo in riga):
                    risultati["errori"].append(f"Riga {i} completamente vuota.")

    except Exception as e:
        risultati["errori"].append(f"Errore durante la lettura del file: {str(e)}")

    return risultati
