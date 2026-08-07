from datetime import datetime

class TimeTool:
    def get_time(self, request: str = ""):
        return {
            "timestamp": datetime.now().isoformat()
        }

    def return_tool_schema(self):
        return [
            {
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "Returns the current timestamp.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "request": {
                            "type": "string",
                            "description": "Reason for requesting time information."
                        }
                    },
                    "required": []
                }
            }
        }
        ]

    def get_tools(self):
        return {
            "get_time": self.get_time
        }

    def preload(self):
        return {"time": self.get_time()}