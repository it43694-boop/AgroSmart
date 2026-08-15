import urllib.request, urllib.parse
url='http://127.0.0.1:8001/token'
data={'admin_code':'Ibrahim200119!','username':'admin@test.com'}
data_bytes=urllib.parse.urlencode(data).encode()
req=urllib.request.Request(url, data=data_bytes, method='POST')
req.add_header('Content-Type','application/x-www-form-urlencoded')
try:
    with urllib.request.urlopen(req, timeout=10) as r:
        print('STATUS', r.status)
        print(r.read().decode())
except Exception as e:
    import traceback
    traceback.print_exc()
