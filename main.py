import json
import requests
import time

from tools.time import TimeTool
from tools.geo import GeoTool
from tools.user_data import UserDataTool
from tools.search import SearchTool
from tools.rag import RAGTool
from db import ResultsDB

class AICall:
    def __init__(self, enabled_tools, preloaded_info, system_prompt: str, reasoning: bool, model: str, query: str, db: ResultsDB = None):
        self.system_prompt = system_prompt
        self.reasoning = reasoning
        self.model = model
        self.query = query
        self.db = db

        self.tools = []
        self.tool_functions = {}
        for tool in enabled_tools:
            self.tools.extend(tool.return_tool_schema())
            self.tool_functions.update(tool.get_tools())

        self.preloaded_context = {}
        for info in preloaded_info:
            self.preloaded_context.update(info.preload())

        self._tool_names = [t["function"]["name"] for t in self.tools]
        self._preloaded_info = list(self.preloaded_context.keys())

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
            msg = {"user_msg": self.query}
            msg.update(self.preloaded_context)  # e.g. adds "location": ..., "timestamp": ...
            return msg

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

        run_id = None
        if self.db:
            run_id = self.db.start_run(
                model=self.model,
                reasoning=self.reasoning,
                system_prompt=self.system_prompt,
                query=self.query,
                preloaded_info=self._preloaded_info,
                enabled_tools=self._tool_names,
            )

        start_time = time.time()
        tool_call_count = 0
        final_response = None

        while True:
            response = self.request(payload)
            message = response["choices"][0]["message"] #response["message"] 

            #print(message)

            if "tool_calls" not in message or not message["tool_calls"]:
                final_response = message.get("content", "")
                break

            messages.append(message)
                
            for call in message["tool_calls"]:
                name = call["function"]["name"]
                args = json.loads(call["function"]["arguments"])
                tool_call_count += 1

                if name in self.tool_functions:
                    result = self.tool_functions[name](**args)
                else:
                    result = {"error": f"Unknown tool: {name}"}

                messages.append({
                    "role": "tool",
                    "tool_call_id": call["id"],
                    "content": json.dumps(result)
                })
            # Ask model to produce final answer
            payload["messages"] = messages

        duration_ms = int((time.time() - start_time) * 1000)

        if self.db and run_id:
            self.db.finish_run(run_id, final_response, tool_call_count, duration_ms)
        
        return final_response