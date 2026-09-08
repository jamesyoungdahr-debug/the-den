from pydantic import BaseModel


class IndexerCreate(BaseModel):
    name: str
    url: str
    api_key: str | None = None
    protocol: str = "torznab"
    enabled: bool = True


class IndexerOut(IndexerCreate):
    id: int

    class Config:
        from_attributes = True
