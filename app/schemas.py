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


class ReleaseOut(BaseModel):
    title: str
    download_url: str
    indexer_name: str
    size: int | None = None
    seeders: int | None = None
    peers: int | None = None

    class Config:
        from_attributes = True
