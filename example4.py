from datetime import datetime
from typing import Optional
from uuid import uuid4

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from fastapi.testclient import TestClient
from pydantic import BaseModel, EmailStr, Field, field_serializer, UUID4

# Inicializa a aplicação FastAPI.
app = FastAPI()


# Define o modelo de dados para um utilizador usando Pydantic BaseModel.
# Este modelo será usado para validação de dados de entrada e saída na API.
class User(BaseModel):
    # Configuração do modelo Pydantic.
    # "extra": "forbid" significa que o modelo não aceitará campos que não estejam explicitamente definidos.
    model_config = {
        "extra": "forbid",
    }
    # Uma lista estática para simular um armazenamento de utilizadores em memória.
    # Em uma aplicação real, isso seria um banco de dados.
    __users__ = []
    # Campo 'name' do tipo string. '...' indica que é um campo obrigatório.
    name: str = Field(..., description="Name of the user")
    # Campo 'email' do tipo EmailStr (valida automaticamente o formato de email).
    email: EmailStr = Field(..., description="Email address of the user")
    # Lista de amigos, onde cada amigo é identificado por um UUID4.
    # default_factory é usado para criar uma nova lista vazia para cada nova instância do modelo.
    # max_items limita o número de amigos.
    friends: list[UUID4] = Field(
        default_factory=list, max_items=500, description="List of friends"
    )
    # Lista de utilizadores bloqueados, também identificados por UUID4.
    blocked: list[UUID4] = Field(
        default_factory=list, max_items=500, description="List of blocked users"
    )
    # Timestamp de registo do utilizador.
    # Optional indica que pode ser None. default_factory define o valor padrão (data/hora atual).
    # kw_only=True significa que este campo só pode ser passado como argumento de palavra-chave.
    signup_ts: Optional[datetime] = Field(
        default_factory=datetime.now, description="Signup timestamp", kw_only=True
    )
    # ID único do utilizador, gerado automaticamente como um UUID4.
    id: UUID4 = Field(
        default_factory=uuid4, description="Unique identifier", kw_only=True
    )

    # Serializador de campo para o atributo 'id'.
    # 'when_used="json"' significa que este serializador é usado quando o modelo é serializado para JSON.
    # Converte o objeto UUID4 para a sua representação em string.
    @field_serializer("id", when_used="json")
    def serialize_id(self, id: UUID4) -> str:
        return str(id)


# Endpoint GET para obter todos os utilizadores.
# response_model=list[User] garante que a resposta será uma lista de objetos User validados pelo Pydantic.
@app.get("/users", response_model=list[User])
async def get_users() -> list[User]:
    return list(User.__users__)


# Endpoint POST para criar um novo utilizador.
# O corpo da requisição será validado automaticamente como um objeto User.
@app.post("/users", response_model=User)
async def create_user(user: User):
    User.__users__.append(user) # Adiciona o novo utilizador à lista em memória.
    return user # Retorna o utilizador criado.


# Endpoint GET para obter um utilizador específico pelo seu ID.
# user_id é do tipo UUID4, que o Pydantic valida automaticamente.
@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: UUID4) -> User | JSONResponse:
    try:
        # Procura o utilizador na lista pelo ID.
        return next((user for user in User.__users__ if user.id == user_id))
    except StopIteration:
        # Se o utilizador não for encontrado, retorna uma resposta JSON com status 404.
        return JSONResponse(status_code=404, content={"message": "User not found"})


# Função principal para executar testes automatizados da API.
def main() -> None:
    # TestClient é uma ferramenta do FastAPI para testar endpoints sem iniciar um servidor real.
    with TestClient(app) as client:
        # Cria 5 utilizadores de teste.
        for i in range(5):
            response = client.post(
                "/users",
                json={"name": f"User {i}", "email": f"example{i}@arjancodes.com"},
            )
            # Verifica se a requisição foi bem-sucedida (status 200).
            assert response.status_code == 200
            # Verifica se o nome do utilizador na resposta corresponde ao esperado.
            assert response.json()["name"] == f"User {i}", (
                "The name of the user should be User {i}"
            )
            # Verifica se o utilizador tem um ID.
            assert response.json()["id"], "The user should have an id"

            # Valida a resposta JSON contra o modelo User do Pydantic.
            user = User.model_validate(response.json())
            # Verifica se o ID do objeto User corresponde ao ID na resposta JSON.
            assert str(user.id) == response.json()["id"], "The id should be the same"
            # Verifica se o timestamp de registo foi definido.
            assert user.signup_ts, "The signup timestamp should be set"
            # Verifica se as listas de amigos e bloqueados estão vazias.
            assert user.friends == [], "The friends list should be empty"
            assert user.blocked == [], "The blocked list should be empty"

        # Testa o endpoint GET /users para obter todos os utilizadores.
        response = client.get("/users")
        assert response.status_code == 200, "Response code should be 200"
        assert len(response.json()) == 5, "There should be 5 users"

        # Cria mais um utilizador.
        response = client.post(
            "/users", json={"name": "User 5", "email": "example5@arjancodes.com"}
        )
        assert response.status_code == 200
        assert response.json()["name"] == "User 5", (
            "The name of the user should be User 5"
        )
        assert response.json()["id"], "The user should have an id"

        user = User.model_validate(response.json())
        assert str(user.id) == response.json()["id"], "The id should be the same"
        assert user.signup_ts, "The signup timestamp should be set"
        assert user.friends == [], "The friends list should be empty"
        assert user.blocked == [], "The blocked list should be empty"

        # Testa o endpoint GET /users/{user_id} com um ID válido.
        response = client.get(f"/users/{response.json()["id"]}")
        assert response.status_code == 200
        assert response.json()["name"] == "User 5", (
            "This should be the newly created user"
        )

        # Testa o endpoint GET /users/{user_id} com um ID inválido.
        response = client.get(f"/users/{uuid4()}")
        assert response.status_code == 404
        assert response.json()["message"] == "User not found", (
            "We technically should not find this user"
        )

        # Testa a criação de utilizador com um email inválido (Pydantic deve rejeitar).
        response = client.post("/users", json={"name": "User 6", "email": "wrong"})
        assert response.status_code == 422, "The email address is should be invalid"


# Garante que a função main() é chamada apenas quando o script é executado diretamente.
if __name__ == "__main__":
    main()