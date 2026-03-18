"""Shared models and protocol for hotel inventory providers."""

from typing import Literal, Protocol, runtime_checkable
from pydantic import BaseModel, Field


class HotelSearchInput(BaseModel):
    destination: str
    checkin: str                          # dd/mm/aaaa
    checkout: str                         # dd/mm/aaaa
    guests: int
    budget_per_night: float               # máximo em R$
    preferences: list[str] = Field(default_factory=list)


class HotelResult(BaseModel):
    id: str
    nome: str
    cidade: str
    bairro: str
    preco_min: float
    preco_max: float
    amenities: list[str] = Field(default_factory=list)
    nota: float = 7.0                     # 0–10
    tags: list[str] = Field(default_factory=list)
    descricao: str = ""
    link_reserva: str = ""
    telefone: str | None = None
    fonte: Literal["amadeus", "liteapi", "local"] = "local"


@runtime_checkable
class HotelInventoryProvider(Protocol):
    name: str

    def search(self, inp: HotelSearchInput) -> list[HotelResult]:
        ...
