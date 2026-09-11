"""Stand-in for the parts of TMDB The Den uses: movie search (M2), and Discover's rails,
multi-search and details (M11d). No API key needed; whatever key is sent is ignored.

Run: python -m uvicorn tests.mock_tmdb:app --port 8081   with TMDB_BASE_URL=http://127.0.0.1:8081
"""

from fastapi import FastAPI, Response

app = FastAPI()

MOVIES = [
    {"id": 27205, "title": "Inception", "release_date": "2010-07-15", "overview": "A thief who steals secrets through dreams.", "poster_path": "/mock-inception.jpg", "backdrop_path": "/mock-inception-bd.jpg", "vote_average": 8.4, "vote_count": 35000, "genre_ids": [28, 878]},
    {"id": 693134, "title": "Dune: Part Two", "release_date": "2024-02-27", "overview": "Paul Atreides unites with the Fremen.", "poster_path": "/mock-dune2.jpg", "backdrop_path": "/mock-dune2-bd.jpg", "vote_average": 8.2, "vote_count": 6000, "genre_ids": [878, 12]},
    {"id": 872585, "title": "Oppenheimer", "release_date": "2023-07-19", "overview": "The story of J. Robert Oppenheimer.", "poster_path": "/mock-opp.jpg", "backdrop_path": "/mock-opp-bd.jpg", "vote_average": 8.1, "vote_count": 9000, "genre_ids": [18, 36]},
]
TV = [
    {"id": 95396, "name": "Severance", "first_air_date": "2022-02-17", "overview": "Office workers whose memories are split.", "poster_path": "/mock-sev.jpg", "backdrop_path": "/mock-sev-bd.jpg", "vote_average": 8.7, "vote_count": 2000, "genre_ids": [18, 9648]},
    {"id": 1, "name": "Under the Dome", "first_air_date": "2013-06-24", "overview": "A town sealed off by a dome.", "poster_path": "/mock-dome.jpg", "backdrop_path": "/mock-dome-bd.jpg", "vote_average": 6.5, "vote_count": 800, "genre_ids": [18, 878]},
]
GENRES = {28: "Action", 878: "Science Fiction", 12: "Adventure", 18: "Drama", 36: "History", 9648: "Mystery"}


def _with_type(items, kind):
    return [{**i, "media_type": kind} for i in items]


@app.get("/search/movie")
def search_movie(query: str, api_key: str = ""):
    hits = [m for m in MOVIES if query.lower() in m["title"].lower()] or [{**MOVIES[0], "title": query}]
    return {"results": hits}


@app.get("/search/multi")
def search_multi(query: str, api_key: str = "", include_adult: str = "false"):
    q = query.lower()
    hits = _with_type([m for m in MOVIES if q in m["title"].lower()], "movie") + _with_type([t for t in TV if q in t["name"].lower()], "tv")
    hits.append({"id": 500, "name": "Some Person", "media_type": "person"})  # must be ignored
    return {"results": hits}


@app.get("/trending/all/{window}")
def trending(window: str, api_key: str = ""):
    return {"results": _with_type(MOVIES[1:2], "movie") + _with_type(TV[:1], "tv") + _with_type(MOVIES[2:], "movie")}


@app.get("/movie/popular")
def popular_movies(api_key: str = ""):
    return {"results": MOVIES}


@app.get("/movie/upcoming")
def upcoming_movies(api_key: str = ""):
    return {"results": MOVIES[1:]}


@app.get("/tv/popular")
def popular_tv(api_key: str = ""):
    return {"results": TV}


@app.get("/tv/on_the_air")
def on_the_air(api_key: str = ""):
    return {"results": TV[:1]}


def _details(base: dict, kind: str) -> dict:
    others = [m for m in (MOVIES if kind == "movie" else TV) if m["id"] != base["id"]]
    return {
        **base,
        "genres": [{"id": g, "name": GENRES[g]} for g in base.get("genre_ids", [])],
        "tagline": "A mock tagline.",
        "status": "Released" if kind == "movie" else "Returning Series",
        "credits": {"cast": [{"name": "Mock Actor", "character": "Lead", "profile_path": None}, {"name": "Another Actor", "character": "Support", "profile_path": None}]},
        "videos": {"results": [{"site": "YouTube", "type": "Trailer", "key": "mock-trailer"}]},
        "recommendations": {"results": others},
        "external_ids": {"imdb_id": "tt1375666" if kind == "movie" else "tt2270789", "tvdb_id": 264492 if kind == "tv" else None},
    }


@app.get("/movie/{movie_id}")
def movie_details(movie_id: int, api_key: str = "", append_to_response: str = ""):
    base = next((m for m in MOVIES if m["id"] == movie_id), None)
    if base is None:
        return Response(status_code=404)
    return {**_details(base, "movie"), "runtime": 148}


@app.get("/tv/{tv_id}")
def tv_details(tv_id: int, api_key: str = "", append_to_response: str = ""):
    base = next((t for t in TV if t["id"] == tv_id), None)
    if base is None:
        return Response(status_code=404)
    return {
        **_details(base, "tv"),
        "number_of_seasons": 2, "number_of_episodes": 19, "networks": [{"name": "Mock TV"}], "in_production": True,
        "seasons": [
            {"season_number": 0, "name": "Specials", "episode_count": 2, "air_date": None, "poster_path": None},
            {"season_number": 1, "name": "Season 1", "episode_count": 9, "air_date": "2022-02-17", "poster_path": None},
            {"season_number": 2, "name": "Season 2", "episode_count": 10, "air_date": "2025-01-17", "poster_path": None},
        ],
    }
