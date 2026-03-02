import enum
import hashlib
import re
from typing import Any, Self
from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    field_serializer,
    field_validator,
    model_serializer,
    model_validator,
    SecretStr,
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
    User = 0 # Um papel base, ou para utilizadores sem permissões especiais.
    Author = 1
    Editor = 2
    Admin = 4
    SuperAdmin = 8


# Define o modelo de dados para um utilizador usando Pydantic BaseModel.
# Pydantic é uma biblioteca de validação de dados que permite definir a estrutura dos dados
# e validar automaticamente os tipos e formatos, além de adicionar validações e serializações personalizadas.
class User(BaseModel):
    # Campo 'name' do tipo string. Field é usado para adicionar metadados como exemplos.
    name: str = Field(examples=["Example"])
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
    # 'exclude=True' significa que este campo será excluído por padrão ao serializar o modelo (e.g., para JSON).
    password: SecretStr = Field(
        examples=["Password123"], description="The password of the user", exclude=True
    )
    # Campo 'role' do tipo Role (o enum.IntFlag que definimos acima).
    # 'default=0' define o papel padrão como 'User'.
    # 'validate_default=True' garante que o valor padrão também passe pelos validadores.
    role: Role = Field(
        description="The role of the user",
        examples=[1, 2, 4, 8],
        default=0,
        validate_default=True,
    )

    # Validador de campo para o atributo 'name'.
    # É executado após a validação de tipo básica do Pydantic.
    @field_validator("name")
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

    # Validador de modelo que é executado ANTES da validação de campo individual.
    # 'mode="before"' significa que ele opera no dicionário de dados brutos antes de criar a instância do modelo.
    @model_validator(mode="before")
    @classmethod
    def validate_user_pre(cls, v: dict[str, Any]) -> dict[str, Any]:
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

    # Validador de modelo que é executado DEPOIS da validação de campo individual e da criação da instância do modelo.
    # 'mode="after"' significa que ele opera na instância do modelo já criada (self).
    @model_validator(mode="after")
    def validate_user_post(self, v: Any) -> Self:
        # Exemplo de validação pós-modelo: apenas 'Arjan' pode ter o papel de Admin.
        if self.role == Role.Admin and self.name != "Arjan":
            raise ValueError("Only Arjan can be an admin")
        return self # Retorna a instância do modelo validada.

    # Serializador de campo para o atributo 'role'.
    # 'when_used="json"' significa que este serializador é usado quando o modelo é serializado para JSON.
    # Ele converte o objeto Role para a sua representação em string (o nome do papel).
    @field_serializer("role", when_used="json")
    @classmethod
    def serialize_role(cls, v: Role) -> str:
        return v.name

    # Serializador de modelo que permite personalizar a saída de todo o modelo.
    # 'mode="wrap"' permite interceptar e modificar o resultado da serialização padrão.
    # 'when_used="json"' significa que este serializador é usado quando o modelo é serializado para JSON.
    @model_serializer(mode="wrap", when_used="json")
    def serialize_user(self, serializer, info) -> dict[str, Any]:
        # Se não houver inclusões ou exclusões específicas (ou seja, serialização padrão para JSON),
        # retorna um dicionário simplificado com apenas 'name' e 'role.name'.
        if not info.include and not info.exclude:
            return {"name": self.name, "role": self.role.name}
        # Caso contrário, usa o serializador padrão do Pydantic.
        return serializer(self)


# Função principal para demonstrar a validação e serialização.
def main() -> None:
    data = {
        "name": "Arjan",
        "email": "example@arjancodes.com",
        "password": "Password123",
        "role": "Admin",
    }
    # Valida os dados e cria uma instância do modelo User.
    user = User.model_validate(data)
    if user:
        # Demonstra a serialização padrão do modelo para um dicionário.
        print(
            "The serializer that returns a dict:",
            user.model_dump(),
            sep="\n",
            end="\n\n",
        )
        # Demonstra a serialização do modelo para JSON, usando os serializadores personalizados.
        print(
            "The serializer that returns a JSON string:",
            user.model_dump(mode="json"),
            sep="\n",
            end="\n\n",
        )
        # Demonstra a serialização para JSON, excluindo o campo 'role'.
        print(
            "The serializer that returns a json string, excluding the role:",
            user.model_dump(exclude=["role"], mode="json"),
            sep="\n",
            end="\n\n",
        )
        # Demonstra a conversão direta do modelo para um dicionário (sem serializadores personalizados).
        print("The serializer that encodes all values to a dict:", dict(user), sep="\n")


# Garante que a função main() é chamada apenas quando o script é executado diretamente.
if __name__ == "__main__":
    main()