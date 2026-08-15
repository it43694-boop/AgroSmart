import json, urllib.request, urllib.parse
# create admin user via API
url='http://127.0.0.1:8002/api/users/'
user_data={
    'full_name':'Admin Test',
    'email':'admin@test.com',
    'username':'admin',
    'password':'AdminPass123!',
    'account_type':'admin'
}
req=urllib.request.Request(url, data=json.dumps(user_data).encode(), headers={'Content-Type':'application/json'})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print('create status', r.status)
        print(r.read().decode())
except urllib.error.HTTPError as e:
    print('create HTTP', e.code)
    print(e.read().decode())
except Exception as e:
    import traceback; traceback.print_exc()

# login to obtain token
url='http://127.0.0.1:8002/token'
form={'username':'admin@test.com','password':'AdminPass123!'}
req=urllib.request.Request(url, data=urllib.parse.urlencode(form).encode(), headers={'Content-Type':'application/x-www-form-urlencoded'})
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print('login status', r.status)
        print(r.read().decode())
except urllib.error.HTTPError as e:
    print('login HTTP', e.code)
    print(e.read().decode())
except Exception:
    import traceback; traceback.print_exc()
