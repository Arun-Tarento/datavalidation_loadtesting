import requests


r = requests.post("http://localhost:8000/auth/refresh", json={
  "token" : "eyJhbGciOiJIUzI1NiIsInRvayI6InJlZnJlc2giLCJ0eXAiOiJKV1QifQ.eyJzdWIiOiJlMmQ0ZTE2Zi03NDBiLTRmZmMtOGIzZS1lY2M0ZGUxZjNiZTYiLCJuYW1lIjoidGVzdGNvbnN1bWVyIiwiZXhwIjoxNzkyNTgxMjExLjA4NTQ1OTcsImlhdCI6MTc2MTA0NTIxMS4wODU0NjExLCJzZXNzX2lkIjoiYTVlMmVkOGYtOTE3ZC00YWQ5LWE4ZDAtMjk4YjRhZDZlZWM0In0.mabezjXRXE3nl_VWDpYHMpMCtJBF87XT5K2IO0Qw_Bk"
})
data = r.json()


print(data)

refresh_resp = requests.post(
        f"http://localhost:8000/auth/refresh",
        json={"token": token_after_signin},
        timeout=5,
    )