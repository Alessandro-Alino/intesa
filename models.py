from typing import Literal

from pydantic import BaseModel, field_validator
from pydantic_core import ErrorDetails, PydanticCustomError


class RITModel(BaseModel):
    richiedente: str
    capo_ufficio: str
    capo_servizio: str
    po_riferimento: str
    acronimo: str
    ambiente: Literal["TEST", "PRODUZIONE"]
    subscription: Literal["ISP_PROD_KEYVAULT_SEC", "ISP_SYSTEM_KEYVAULT_SEC"]
    resource_group: str
    keyvault_name: str
    region: Literal["Italy North"]
    servizio: str

    # VALIDATOR PER ACRONIMO
    @field_validator("acronimo", mode="before")
    @classmethod
    def check_acronimo(cls, value: str) -> str:
        if len(value) != 5:
            raise PydanticCustomError(
                "acronimo_lunghezza",
                "L'acronimo deve essere lungo almeno 5 caratteri",
                {"lunghezza": 5, "dati": len(value)},
            )

        return value

    # Validator per subscription: uppercase + sostituisce spazi con underscore
    @field_validator("subscription", mode="before")
    @classmethod
    def normalize_subscription(cls, value: str) -> str:
        # Converte in uppercase e sostituisce gli spazi con underscore
        normalized = value.upper().replace(" ", "_")
        return normalized

class ValidationErrorDetail(BaseModel):
    errors: list[dict]

class ValidationResponse(BaseModel):
    valid: bool
    message: str
    data: list[RITModel] = []
    errors: list[ValidationErrorDetail] = []
