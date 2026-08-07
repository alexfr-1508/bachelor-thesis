import requests

class GeoTool:
    def get_location(self, request: str = ""):
        data = requests.get("https://ipinfo.io/json/", timeout=10, verify=False).json()

        return {
            "country": data.get("country"),
            "region": data.get("region"),
            "city": data.get("city"),
            "timezone": data.get("timezone")
        }

    def return_tool_schema(self):
        return [
            {
            "type": "function",
            "function": {
                "name": "get_location",
                "description": "Returns the users approximate location.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "request": {
                                "type": "string",
                                "description": "Reason for requesting location information."
                            }
                        },
                    "required": []
                }
            }
        }
        ]

    def get_tools(self):
        return {
            "get_location": self.get_location
        }

    def preload(self):
        return {"location": self.get_location()}