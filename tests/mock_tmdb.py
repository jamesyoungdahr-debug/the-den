"""Stand-in for TMDB's search/movie API so we can test without a real API key."""

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
