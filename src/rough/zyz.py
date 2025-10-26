import requests

url = "http://localhost:8000/auth/api-key/list?target_user_id=68e5f637d93156413d55b152&target_service_id"

payload = ""
headers = {
  'x-auth-source': 'AUTH_TOKEN',
  'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInRvayI6InJlZnJlc2giLCJ0eXAiOiJKV1QifQ.eyJzdWIiOiI2OGU1ZjYzN2Q5MzE1NjQxM2Q1NWIxNTIiLCJuYW1lIjoiVGVzdHVzZXJfcG9zdG1hbl8xIiwiZXhwIjoxNzkxNDQxNjk1LjIwNzgxNzgsImlhdCI6MTc1OTkwNTY5NS4yMDc4MTkyLCJzZXNzX2lkIjoiNjhlNjA3OWZkOTMxNTY0MTNkNTViMTYyIn0.9o_mxOB0IlHvpST3_8CIt4TX6gFwVPmAvOpCRRdCUMQ'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text)