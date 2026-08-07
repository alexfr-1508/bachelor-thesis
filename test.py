import requests
import certifi

r = requests.get(
    "https://ipapi.co/json/",
    verify=certifi.where()
)

print(r.json())