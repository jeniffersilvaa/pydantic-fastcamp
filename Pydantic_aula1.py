from enum import auto, IntFlag
from typing import Any
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    SecretStr,
    ValidationError,
)

# Define um conjunto de papéis (roles) usando IntFlag, que permite combinar múltiplos papéis.
# IntFlag é útil para permissões, onde um utilizador pode ter várias permissões simultaneamente.
class Role(IntFlag):
    # auto() atribui automaticamente um valor inteiro sequencial (potências de 2) a cada membro.
    # Author = 1
    Author = auto()
    # Editor = 2
    Editor = auto()
    # Developer = 4
    Developer = auto()
    # Admin é uma combinação de Author, Editor e Developer (1 | 2 | 4 = 7).
    # Isso significa que um Admin tem todas as permissões dos outros papéis.
    Admin = Author | Editor | Developer

# Define o modelo de dados para um utilizador usando Pydantic BaseModel.
# Pydantic é uma biblioteca de validação de dados que permite definir a estrutura dos dados
# e validar automaticamente os tipos e formatos.
class User(BaseModel):
    # Campo 'name' do tipo string. Field é usado para adicionar metadados como exemplos.
    name: str = Field(examples=["Arjan"])
    # Campo 'email' do tipo EmailStr (um tipo Pydantic para validação de formato de email).
    # 'description' fornece uma descrição para documentação (e.g., em APIs).
    # 'frozen=True' torna este campo imutável após a criação do objeto User.
    email: EmailStr = Field(
        examples=["example@arjancodes.com"],
        description="The email address of the user",
        frozen=True,
    )
    # Campo 'password' do tipo SecretStr (um tipo Pydantic para lidar com informações sensíveis).
    # SecretStr garante que o valor não seja exposto facilmente (e.g., em logs).
    password: SecretStr = Field(
        examples=["Password123"], description="The password of the user"
    )
    # Campo 'role' do tipo Role (o IntFlag que definimos acima).
    # 'default=None' indica que o papel é opcional e, se não for fornecido, será None.
    role: Role = Field(default=None, description="The role of the user")

# Função para validar dados de utilizador usando o modelo Pydantic.
# Recebe um dicionário de dados e tenta validá-lo contra o modelo User.
def validate(data: dict[str, Any]) -> None:
    try:
        # Tenta criar uma instância de User a partir dos dados fornecidos.
        # Pydantic automaticamente valida os tipos e formatos aqui.
        user = User.model_validate(data)
        # Se a validação for bem-sucedida, imprime o objeto User.
        print(user)
    except ValidationError as e:
        # Se a validação falhar (e.g., email inválido, campo em falta),
        # uma ValidationError é capturada.
        print("User is invalid")
        # Itera sobre os erros de validação e imprime cada um.
        for error in e.errors():
            print(error)

# Função principal para demonstrar a validação.
def main() -> None:
    # Dados válidos para um utilizador.
    good_data = {
        "name": "Arjan",
        "email": "example@arjancodes.com",
        "password": "Password123",
    }
    # Dados inválidos para um utilizador (email com formato incorreto, password em falta).
    bad_data = {"email": "<bad data>", "password": "<bad data>"}

    # Valida os dados válidos.
    validate(good_data)
    print("\n---\n") # Separador para melhor visualização
    # Valida os dados inválidos.
    validate(bad_data)

# Garante que a função main() é chamada apenas quando o script é executado diretamente.
if __name__ == "__main__":
    main()