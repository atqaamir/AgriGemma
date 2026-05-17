import urllib.request, json, sys
url='http://127.0.0.1:5000/notifications/test/create'
data=json.dumps({'user_id':1,'title':'Trigger Test','message':'testing change summary','notification_type':'change'}).encode()
req=urllib.request.Request(url,data,headers={'Content-Type':'application/json'})
try:
    resp=urllib.request.urlopen(req,timeout=5)
    print('status',resp.status)
    print(resp.read().decode())
except Exception as e:
    print('error',e)
    sys.exit(1)
