from pydantic import BaseModel


class IndexerCreate(BaseModel):
    name: str = ""
    url: str = ""
    api_key: str | None = None
    protocol: str = "torznab"
    enabled: bool = True
    # M12: "torznab" | "newznab" | a native slug; `preset` is the catalog entry it came from
    implementation: str | None = None
    preset: str | None = None


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


class ScoredReleaseOut(ReleaseOut):
    quality: str
    is_best: bool = False


class MovieCreate(BaseModel):
    tmdb_id: int
    title: str
    year: int | None = None
    overview: str | None = None
    poster_path: str | None = None


class MovieOut(MovieCreate):
    id: int
    has_file: bool

    class Config:
        from_attributes = True


class GrabRequest(BaseModel):
    download_url: str
    release_title: str


class DownloadRecordOut(BaseModel):
    id: int
    movie_id: int | None = None
    episode_id: int | None = None
    release_title: str
    info_hash: str | None = None  # key into /torrents for live progress
    status: str

    class Config:
        from_attributes = True


class SeriesCreate(BaseModel):
    tvmaze_id: int
    tmdb_id: int | None = None
    title: str
    year: int | None = None
    overview: str | None = None
    poster_path: str | None = None


class SeriesOut(SeriesCreate):
    id: int

    class Config:
        from_attributes = True


class EpisodeOut(BaseModel):
    id: int
    series_id: int
    season_number: int
    episode_number: int
    title: str | None = None
    air_date: str | None = None
    has_file: bool

    class Config:
        from_attributes = True
