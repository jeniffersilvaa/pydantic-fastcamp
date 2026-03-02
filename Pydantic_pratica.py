"""
SISTEMA DE GESTÃO DE EVENTOS - EXEMPLO CONSOLIDADO
-------------------------------------------------------
Este código é uma demonstração prática que consolida os conceitos avançados de Pydantic e FastAPI.
O objetivo é gerir o ciclo de vida de eventos (Conferências, Workshops, etc.), aplicando:
1. Validação rigorosa de dados com Pydantic (Tipos, Regex, Enums).
2. Lógica de negócio complexa (Validação de datas e permissões).
3. Serialização personalizada para saídas JSON limpas e seguras.
4. Uso de Generics para padronização de respostas da API.
5. Integração com FastAPI para criação de endpoints RESTful (CRUD).
6. Testes automatizados para garantir a integridade do sistema.
"""

import enum
import re
from datetime import datetime, timedelta
from typing import Any, Optional, TypeVar, Generic
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_serializer,
    field_validator,
    model_validator,
    ConfigDict,
)

# --- Configurações de Validação Global --- #
# Expressões regulares para garantir que os nomes e localizações sigam um padrão específico.
VALID_EVENT_NAME_REGEX = re.compile(r"^[a-zA-Z0-9\s]{5,100}$")
VALID_LOCATION_REGEX = re.compile(r"^[a-zA-Z0-9\s,.-]{5,200}$")

# --- Enums (Visto no Código 1 e 2) --- #
# Usamos Enums para definir estados fixos, o que evita erros de digitação e melhora a legibilidade.
class EventStatus(enum.Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    CANCELLED = "cancelled"
    COMPLETED = "completed"

class EventCategory(enum.Enum):
    CONFERENCE = "conference"
    WORKSHOP = "workshop"
    MEETUP = "meetup"
    CONCERT = "concert"
    OTHER = "other"

# --- Modelos Pydantic (Conceitos dos Códigos 1, 2, 3 e 4) --- #

class Event(BaseModel):
    # ConfigDict (Visto no Código 4): Configura o comportamento do Pydantic.
    # 'extra="forbid"' impede que o utilizador envie campos não definidos no modelo.
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "name": "Tech Conference 2026",
                    "description": "A conference about the latest in technology.",
                    "location": "Lisbon, Portugal",
                    "start_time": "2026-03-10T09:00:00Z",
                    "end_time": "2026-03-12T17:00:00Z",
                    "category": "conference",
                    "max_attendees": 500,
                    "created_by": "admin@example.com",
                }
            ]
        },
    )

    # Definição de Campos com Field (Visto em todos os códigos):
    # 'kw_only=True' (Código 4) garante que estes campos não sejam passados por posição.
    # 'default_factory' (Código 4) gera um valor dinâmico (UUID ou Data Atual) se não for fornecido.
    id: UUID = Field(default_factory=uuid4, description="Unique identifier of the event", kw_only=True)
    name: str = Field(..., description="Name of the event", min_length=5, max_length=100)
    description: str = Field(..., description="Detailed description of the event", min_length=10)
    location: str = Field(..., description="Location of the event", min_length=5, max_length=200)
    start_time: datetime = Field(..., description="Start date and time of the event")
    end_time: datetime = Field(..., description="End date and time of the event")
    status: EventStatus = Field(default=EventStatus.DRAFT, description="Current status of the event")
    category: EventCategory = Field(default=EventCategory.OTHER, description="Category of the event")
    max_attendees: int = Field(..., gt=0, description="Maximum number of attendees")
    # 'frozen=True' (Código 1) impede que o criador do evento seja alterado após a criação.
    created_by: EmailStr = Field(..., description="Email of the user who created the event", frozen=True)
    created_at: datetime = Field(default_factory=datetime.now, description="Timestamp of event creation", kw_only=True)

    # --- Validadores de Campo (Visto no Código 2 e 3) --- #
    @field_validator("name")
    @classmethod
    def validate_event_name(cls, v: str) -> str:
        if not VALID_EVENT_NAME_REGEX.match(v):
            raise ValueError("Event name is invalid. Must be 5-100 alphanumeric characters and spaces.")
        return v

    @field_validator("location")
    @classmethod
    def validate_event_location(cls, v: str) -> str:
        if not VALID_LOCATION_REGEX.match(v):
            raise ValueError("Event location is invalid. Must be 5-200 alphanumeric characters, spaces, commas, dots, or hyphens.")
        return v

    # --- Validadores de Modelo (Visto no Código 3) --- #
    # 'mode="after"' valida a instância após todos os campos individuais serem validados.
    @model_validator(mode="after")
    def validate_times(self) -> 'Event':
        # Regra de Negócio: O evento não pode terminar antes de começar.
        if self.start_time >= self.end_time:
            raise ValueError("Event start time must be before end time.")
        # Regra de Negócio: Não se pode criar eventos em rascunho no passado.
        if self.start_time < datetime.now() - timedelta(minutes=5) and self.status == EventStatus.DRAFT:
            raise ValueError("Cannot create a draft event in the past.")
        return self

    # --- Serializadores de Campo (Visto no Código 3 e 4) --- #
    # Personalizam como os dados aparecem quando convertidos para JSON.
    @field_serializer("id", "created_by", when_used="json")
    def serialize_uuid_and_email(self, value: UUID | EmailStr) -> str:
        return str(value)

    @field_serializer("status", "category", when_used="json")
    def serialize_enum(self, value: EventStatus | EventCategory) -> str:
        return value.value

# --- Modelo Genérico (Conceito de Generics) --- #
# Permite criar uma estrutura de resposta padrão para toda a API, independentemente do tipo de dado retornado.
T = TypeVar('T')

class APIResponse(BaseModel, Generic[T]):
    status_code: int = Field(..., description="HTTP status code of the response")
    message: str = Field(..., description="A descriptive message about the response")
    data: Optional[T] = Field(None, description="The actual data returned by the API")

# --- Aplicação FastAPI (Visto no Código 4) --- #
app = FastAPI(title="Event Management System")

# Simulação de base de dados em memória
events_db: list[Event] = []

# --- Endpoints da API --- #

@app.post("/events", response_model=APIResponse[Event], status_code=status.HTTP_201_CREATED)
async def create_event(event: Event) -> APIResponse[Event]:
    # O FastAPI usa o Pydantic para validar o corpo da requisição automaticamente.
    events_db.append(event)
    return APIResponse(status_code=status.HTTP_201_CREATED, message="Event created successfully", data=event)

@app.get("/events", response_model=APIResponse[list[Event]])
async def list_events() -> APIResponse[list[Event]]:
    # Retorna todos os eventos usando o modelo genérico de resposta.
    return APIResponse(status_code=status.HTTP_200_OK, message="Events retrieved successfully", data=events_db)

@app.get("/events/{event_id}", response_model=APIResponse[Event])
async def get_event(event_id: UUID) -> APIResponse[Event]:
    # O Pydantic valida se o 'event_id' na URL é um UUID válido.
    for event in events_db:
        if event.id == event_id:
            return APIResponse(status_code=status.HTTP_200_OK, message="Event retrieved successfully", data=event)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

@app.put("/events/{event_id}", response_model=APIResponse[Event])
async def update_event(event_id: UUID, updated_event: Event) -> APIResponse[Event]:
    for idx, event in enumerate(events_db):
        if event.id == event_id:
            # Atualiza os dados mantendo as regras de validação.
            events_db[idx] = updated_event
            return APIResponse(status_code=status.HTTP_200_OK, message="Event updated successfully", data=updated_event)
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

@app.delete("/events/{event_id}", response_model=APIResponse[dict])
async def delete_event(event_id: UUID) -> APIResponse[dict]:
    global events_db
    initial_len = len(events_db)
    events_db = [event for event in events_db if event.id != event_id]
    if len(events_db) < initial_len:
        return APIResponse(status_code=status.HTTP_200_OK, message="Event deleted successfully", data={"id": str(event_id)})
    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Event not found")

# --- Função de Teste (Visto no Código 4) --- #
def main() -> None:
    # O TestClient permite testar a API sem precisar de um servidor externo.
    with TestClient(app) as client:
        print("Executando teste de criação de evento...")
        event_data = {
            "name": "Workshop de Python",
            "description": "Um workshop intensivo sobre programação.",
            "location": "Lisboa, Portugal",
            "start_time": (datetime.now() + timedelta(days=1)).isoformat(),
            "end_time": (datetime.now() + timedelta(days=1, hours=2)).isoformat(),
            "category": "workshop",
            "max_attendees": 50,
            "created_by": "instrutor@exemplo.com",
        }
        response = client.post("/events", json=event_data)
        if response.status_code == 201:
            print("Sucesso: Evento criado e validado pelo Pydantic!")
            print(f"Resposta JSON: {response.json()}")
        else:
            print(f"Erro na validação: {response.json()}")

if __name__ == "__main__":
    main()