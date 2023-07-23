from pydantic import Field as PydanticField
from pydantic_settings import BaseSettings


class Config(BaseSettings):
    port: int = 8084
    host: str = "0.0.0.0"
    form_name: str = "prisons"
    description: str = ""
    nats_servers: list[str] = PydanticField(default=["nats://localhost:4222"])

    dsn: str = "sqlite+aiosqlite:///local_db.sqlite"
