class UserDataTool:
    def save_user_data(self, content: str, request: str = ""):
        with open("userdata.txt", "w", encoding="utf-8") as file:
            file.write(content)

        return {
            "message": "Userdata has been saved."
        }

    def read_user_data(self, request: str = ""):
        try:
            with open("userdata.txt", "r", encoding="utf-8") as file:
                content = file.read()
        except FileNotFoundError:
            content = ""
    
        return {
            "user_data": content
        }

    def return_tool_schema(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "save_user_data",
                    "description": "Saves user data. Overwrites old data.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {
                                "type": "string",
                                "description": "User data to save."
                            },
                            "request": {
                                "type": "string",
                                "description": "Reason for saving user data."
                            }
                                                    
                        },
                        "required": ["content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "read_user_data",
                    "description": "Reads saved user data.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "request": {
                                "type": "string",
                                "description": "Reason for requesting user data."
                            }
                        },
                        "required": []
                    }
                }
            }
        ]

    def get_tools(self):
            return {
                "save_user_data": self.save_user_data,
                "read_user_data": self.read_user_data
            }

    def preload(self):
        return self.read_user_data()
