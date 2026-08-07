import json
import requests

from tools.time import TimeTool
from tools.geo import GeoTool
from tools.user_data import UserDataTool
from tools.search_tool import SearchTool

class AICall:
    def __init__(self, enabled_tools, preloaded_info, system_prompt: str, reasoning: bool, model: str, query: str):
        self.system_prompt = system_prompt
        self.reasoning = reasoning
        self.model = model
        self.query = query

        self.tools = []
        self.tool_functions = {}
        for tool in enabled_tools:
            self.tools.extend(tool.return_tool_schema())
            self.tool_functions.update(tool.get_tools())

        self.preloaded_context = {}
        for info in preloaded_info:
            self.preloaded_context.update(info.preload())

    def request(self, payload):
        res = requests.post(
            "http://localhost:11434/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json=payload
        )

        if res.status_code != 200:
            print(res.text)
            raise RuntimeError(res.status_code)
        return res.json()

    def user_message(self):
        return  {
                    "user_info": self.preloaded_context,
                    "user_msg": self.query
                }

    def messages(self, user_message):
        return [
            {
                "role": "system",
                "content": self.system_prompt
            },
            {
                "role": "user",
                "content": json.dumps(user_message, indent=2)
            }
        ]

    def payload(self, messages):
        return {
            "model": self.model,
            "messages": messages,
            "temperature": 0,
            "tools": self.tools,
            "tool_choice": "auto",
            "reasoning_effort": "medium" if self.reasoning else "none",
        }

    def ai_call(self):
        user_message = self.user_message()
        messages = self.messages(user_message)
        payload = self.payload(messages)

        while True:
            response = self.request(payload)
            message = response["choices"][0]["message"] #response["message"] 

            print(message)

            if "tool_calls" not in message:
                print(message["content"])
                break

            messages.append(message)
                
            for call in message["tool_calls"]:
                name = call["function"]["name"]
                args = json.loads(call["function"]["arguments"])

                if name in self.tool_functions:
                    result = self.tool_functions[name](**args)
                else:
                    result = {
                        "error": f"Unknown tool: {name}"
                    }

                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result)
                })
            # Ask model to produce final answer
            payload["messages"] = messages


#ai_call_1 = AICall(
#    [TimeTool(), GeoTool()],
#    [], 
#    "",
#    False,
#    "qwen3.5:0.8b",
#    "Please tell me my approximate location."
#)
#
#ai_call_1.ai_call()
#
#
#ai_call_2 = AICall(
#    [UserDataTool()],
#    [],
#    "",
#    False,
#    "qwen3.5:0.8b",
#    "Please tell me my approximate location."
#)
#
#ai_call_2.ai_call()

ai_call_3 = AICall(
    [TimeTool(), SearchTool()],
    [],
    "",
    False,
    "qwen3.5:9b",
    "Current generation of NVIDIA consumer GPU's. Check the date first. Afterwards search the web. Return 1 GPU name."
)

ai_call_3.ai_call()