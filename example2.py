import enum
import hashlib
import re
from typing import Any

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_validator,
    model_validator,
    SecretStr,
    ValidationError,
)

# Expressão regular para validar senhas:
# - Deve ter pelo menos 8 caracteres.
# - Deve conter pelo menos uma letra minúscula (a-z).
# - Deve conter pelo menos uma letra maiúscula (A-Z).
# - Deve conter pelo menos um dígito (0-9).
VALID_PASSWORD_REGEX = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$")

# Expressão regular para validar nomes:
# - Deve conter apenas letras (maiúsculas ou minúsculas).
# - Deve ter pelo menos 2 caracteres de comprimento.
VALID_NAME_REGEX = re.compile(r"^[a-zA-Z]{2,}$")


# Define um conjunto de papéis (roles) usando enum.IntFlag.
# IntFlag permite que um utilizador tenha múltiplos papéis simultaneamente (e.g., Author e Editor).
# Os valores são potências de 2 para facilitar a combinação de papéis usando operadores bit a bit.
class Role(enum.IntFlag):
    Author = 1
    Editor = 2
    Admin = 4
    SuperAdmin = 8


# Define o modelo de dados para um utilizador usando Pydantic BaseModel.
# Pydantic é uma biblioteca de validação de dados que permite definir a estrutura dos dados
# e validar automaticamente os tipos e formatos, além de adicionar validações personalizadas.
class User(BaseModel):
    # Campo 'name' do tipo string. Field é usado para adicionar metadados como exemplos.
    name: str = Field(examples=["Arjan"])
    # Campo 'email' do tipo EmailStr (um tipo Pydantic para validação de formato de email).
    # 'description' fornece uma descrição para documentação (e.g., em APIs).
    # 'frozen=True' torna este campo imutável após a criação do objeto User.
    email: EmailStr = Field(
        examples=["user@arjancodes.com"],
        description="The email address of the user",
        frozen=True,
    )
    # Campo 'password' do tipo SecretStr (um tipo Pydantic para lidar com informações sensíveis).
    # SecretStr garante que o valor não seja exposto facilmente (e.g., em logs).
    password: SecretStr = Field(
        examples=["Password123"], description="The password of the user"
    )
    # Campo 'role' do tipo Role (o enum.IntFlag que definimos acima).
    # 'default=None' indica que o papel é opcional. 'examples' para documentação.
    role: Role = Field(
        default=None, description="The role of the user", examples=[1, 2, 4, 8]
    )

    # Validador de campo para o atributo 'name'.
    # É executado após a validação de tipo básica do Pydantic.
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        # Verifica se o nome corresponde à expressão regular definida.
        if not VALID_NAME_REGEX.match(v):
            # Se não corresponder, levanta um ValueError com uma mensagem descritiva.
            raise ValueError(
                "Name is invalid, must contain only letters and be at least 2 characters long"
            )
        return v # Retorna o valor validado.

    # Validador de campo para o atributo 'role'.
    # 'mode="before"' significa que este validador é executado antes da validação de tipo do Pydantic.
    # Isso permite converter diferentes tipos de entrada (int, str) para o tipo Role.
    @field_validator("role", mode="before")
    @classmethod
    def validate_role(cls, v: int | str | Role) -> Role:
        # Dicionário de operações para converter o valor de entrada para o tipo Role com base no seu tipo.
        op = {int: lambda x: Role(x), str: lambda x: Role[x], Role: lambda x: x}
        try:
            # Tenta aplicar a função de conversão apropriada.
            return op[type(v)](v)
        except (KeyError, ValueError):
            # Se a conversão falhar (e.g., papel inválido), levanta um ValueError.
            raise ValueError(
                f"Role is invalid, please use one of the following: {', '.join([x.name for x in Role])}"
            )

    # Validador de modelo que é executado antes da validação de campo individual.
    # 'mode="before"' significa que ele opera no dicionário de dados brutos antes de criar a instância do modelo.
    @model_validator(mode="before")
    @classmethod
    def validate_user(cls, v: dict[str, Any]) -> dict[str, Any]:
        # Verifica se os campos 'name' e 'password' estão presentes.
        if "name" not in v or "password" not in v:
            raise ValueError("Name and password are required")
        # Verifica se o nome (ignorando maiúsculas/minúsculas) está contido na senha.
        if v["name"].casefold() in v["password"].casefold():
            raise ValueError("Password cannot contain name")
        # Valida a senha usando a expressão regular definida.
        if not VALID_PASSWORD_REGEX.match(v["password"]):
            raise ValueError(
                "Password is invalid, must contain 8 characters, 1 uppercase, 1 lowercase, 1 number"
            )
        # Hash da senha usando SHA256 para segurança antes de armazená-la.
        v["password"] = hashlib.sha256(v["password"].encode()).hexdigest()
        return v # Retorna o dicionário de dados (com a senha em hash).


# Função para validar dados de utilizador usando o modelo Pydantic.
# Recebe um dicionário de dados e tenta validá-lo contra o modelo User.
def validate(data: dict[str, Any]) -> None:
    try:
        # Tenta criar uma instância de User a partir dos dados fornecidos.
        # Pydantic automaticamente valida os tipos e formatos, e executa os validadores definidos.
        user = User.model_validate(data)
        # Se a validação for bem-sucedida, imprime o objeto User.
        print(user)
    except ValidationError as e:
        # Se a validação falhar, uma ValidationError é capturada.
        print("User is invalid:")
        # Imprime o objeto de erro completo, que contém detalhes sobre as falhas de validação.
        print(e)


# Função principal para demonstrar a validação com vários casos de teste.
def main() -> None:
    # Dicionário contendo diferentes conjuntos de dados para teste.
    test_data = dict(
        good_data={
            "name": "Arjan",
            "email": "example@arjancodes.com",
            "password": "Password123",
            "role": "Admin", # Teste com papel válido como string
        },
        bad_role={
            "name": "Arjan",
            "email": "example@arjancodes.com",
            "password": "Password123",
            "role": "Programmer", # Papel inválido
        },
        bad_data={
            "name": "Arjan",
            "email": "bad email", # Email inválido
            "password": "bad password", # Senha inválida
        },
        bad_name={
            "name": "Arjan<-_- >", # Nome inválido (contém caracteres não alfabéticos)
            "email": "example@arjancodes.com",
            "password": "Password123",
        },
        duplicate={
            "name": "Arjan",
            "email": "example@arjancodes.com",
            "password": "Arjan123", # Senha contém o nome
        },
        missing_data={
            "email": "<bad data>", # Faltam 'name' e 'password'
            "password": "<bad data>",
        },
    )

    # Itera sobre os dados de teste, validando cada um e imprimindo o resultado.
    for example_name, data in test_data.items():
        print(example_name)
        validate(data)
        print() # Linha em branco para separar os resultados.


# Garante que a função main() é chamada apenas quando o script é executado diretamente.
if __name__ == "__main__":
    main()