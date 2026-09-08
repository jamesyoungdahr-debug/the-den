"""Stand-in for TMDB's search/movie and TV APIs so we can test without a real API key."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/search/movie")
def search_movie(query: str, api_key: str = ""):
    return {
        "results": [
            {
                "id": 27205,
                "title": query,
                "release_date": "2010-07-15",
                "overview": f"A mock movie matching '{query}'.",
                "poster_path": "/mock.jpg",
            }
        ]
    }


@app.get("/search/tv")
def search_tv(query: str, api_key: str = ""):
    return {
        "results": [
            {
                "id": 1396,
                "name": query,
                "first_air_date": "2008-01-20",
                "overview": f"A mock series matching '{query}'.",
                "poster_path": "/mock.jpg",
            }
        ]
    }


@app.get("/tv/{tmdb_id}")
def tv_detail(tmdb_id: int, api_key: str = ""):
    return {"id": tmdb_id, "seasons": [{"season_number": 1}, {"season_number": 2}]}


@app.get("/tv/{tmdb_id}/season/{season_number}")
def tv_season(tmdb_id: int, season_number: int, api_key: str = ""):
    return {
        "episodes": [
            {"episode_number": 1, "name": f"S{season_number} Episode 1", "air_date": "2008-02-01"},
            {"episode_number": 2, "name": f"S{season_number} Episode 2", "air_date": "2008-02-08"},
        ]
    }
