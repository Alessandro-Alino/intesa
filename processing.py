from flask import jsonify
import openpyxl

from pydantic import ValidationError
from models import RITModel, ValidationErrorDetail, ValidationResponse


def validate_file_data(file):
    """
    Funzione di supporto per convalidare i dati contenuti nel file Excel.
    """
    valid_rows = []
    invalid_rows = []

    try:
        wb = openpyxl.load_workbook(file, data_only=True)
        ws = wb["Azure KeyVault"]

        # Estrae i valori verticali (D5:D15)
        valori = [cell[0].value for cell in ws["D5:D15"]]

        chiavi = list(RITModel.model_fields.keys())
        dati_dict = dict(zip(chiavi, valori))

        rit_instance = RITModel(**dati_dict)
        valid_rows.append(rit_instance)

    except ValidationError as e:
        invalid_rows.append(
            ValidationErrorDetail(
                errors=e.errors()
            )
        )
    except Exception as e:
        # Cattura eventuali altri errori (es. foglio mancante, file corrotto)
        return jsonify({
            "valid": False,
            "message": f"Errore durante la lettura del file: {str(e)}",
            "data": [],
            "errors": []
        }), 400

    # Verifica lo stato basandosi sugli errori collezionati
    if not invalid_rows and valid_rows:
        response = ValidationResponse(
            valid=True,
            message=f"✓ Validazione completata: tutte le {len(valid_rows)} righe sono valide.",
            data=valid_rows
        )
        status_code = 200
    else:
        response = ValidationResponse(
            valid=False,
            message=f"✗ Validazione completata: {len(valid_rows)} righe valide, {len(invalid_rows)} con errori.",
            errors=invalid_rows
        )
        status_code = 400

    return jsonify(response.model_dump()), status_code


# --- Helper per risposte di errore ---
def error_response(message: str, status: int = 400):
    resp = ValidationResponse(
        valid=False,
        message=message
    )
    return jsonify(resp.model_dump()), status