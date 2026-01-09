from backend.app import app
c = app.test_client()
r = c.get('/api/health')
print(r.status_code, r.get_json())
