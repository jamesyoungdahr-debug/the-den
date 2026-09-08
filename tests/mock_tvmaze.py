"""Stand-in for the real (free, no-key) TVmaze API, for offline testing."""

from fastapi import FastAPI

app = FastAPI()


@app.get("/search/shows")
def search_shows(q: str):
    return [
        {
            "show": {
                "id": 169,
                "name": q,
                "premiered": "2008-01-20",
                "summary": f"<p>A mock series matching '{q}'.</p>",
                "image": {"medium": "http://mock/poster.jpg"},
            }
        }
    ]


@app.get("/shows/{show_id}/episodes")
def episodes(show_id: int):
    return [
        {"season": 1, "number": 1, "name": "S1 Episode 1", "airdate": "2008-02-01"},
        {"season": 1, "number": 2, "name": "S1 Episode 2", "airdate": "2008-02-08"},
        {"season": 2, "number": 1, "name": "S2 Episode 1", "airdate": "2009-02-01"},
        {"season": 2, "number": 2, "name": "S2 Episode 2", "airdate": "2009-02-08"},
    ]
