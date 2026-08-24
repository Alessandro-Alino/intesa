from azure_service import AzureKeyVaultService
from models import RITModel

class AzureFunctions:
    def __init__(self, azure_service: 'AzureKeyVaultService'):
        self.azure_service = azure_service

    # ==========================================
    # Ricezione e Validazione del Payload
    # ==========================================
    def validate_rit_models(self, data: list[dict]) -> list['RITModel']:
        """Valida il payload JSON e lo converte in lista di RITModel."""
        if not isinstance(data, list):
            raise ValueError("Il payload deve essere una lista di oggetti.")
        
        return [RITModel(**item) for item in data]

    # ==========================================
    # Health Check delle credenziali Azure
    # ==========================================
    def check_azure_authentication(self) -> dict:
        """Verifica che le credenziali Azure siano valide e ottenibili."""
        status = self.azure_service.check_connection()
        
        if not status.get("authenticated"):
            raise ConnectionError("Autenticazione Azure fallita o token non valido.")
            
        return status