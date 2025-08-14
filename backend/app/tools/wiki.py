import requests

def wiki_lookup(query: str):
    url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + requests.utils.quote(query)
    r = requests.get(url, timeout=6)
    if r.status_code != 200:
        return {"query": query, "summary": None}
    data = r.json()
    return {"query": query, "summary": data.get("extract")}
