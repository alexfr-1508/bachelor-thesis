import requests

SEARXNG_URL = "http://localhost:5001"

class SearchTool():
    def __init__(self, searxng_url: str = SEARXNG_URL, result_count: int = 5):
            self.searxng_url = searxng_url.rstrip("/")
            self.result_count = result_count

    def search(self, query: str, language: str = "all", time_range: str = ""):
        params = {
            "q": query,
            "format": "json",
            "language": language,
            "time_range": time_range,
        }

        try:
            res = requests.get(f"{self.searxng_url}/search", params=params)
            res.raise_for_status()
            data = res.json()
        except requests.exceptions.ConnectionError:
                    return {"error": "SearXNG not reachable. Is it running on " + self.searxng_url + "?"}
        except Exception as e:
                    return {"error": str(e)}

        results = sorted(data.get("results", []), key=lambda x: x.get("score", 0), reverse=True)

        return {
            "results": [
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "snippet": item.get("content"),
                }
                for item in results[:self.result_count]
            ]
        }

    def return_tool_schema(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "search",
                    "description": "Searches the web via SearXNG and returns relevant results including title, URL and a short snippet.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "The search query."
                            },
                            "language": {
                                "type": "string",
                                "description": "Language filter, e.g. 'de', 'en', or 'all'.",
                                "default": "all"
                            },
                            "time_range": {
                                "type": "string",
                                "description": "Limit results by time: 'day', 'week', 'month', 'year', or '' for no filter.",
                                "default": ""
                            }
                        },
                        "required": ["query"]
                    }
                }
            }
        ]

    def get_tools(self):
        return {
            "search": self.search
        }