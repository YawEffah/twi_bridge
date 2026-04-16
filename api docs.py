########### Python 3.2 #############
import urllib.request, json

try:
    url = "https://translation-api.ghananlp.org/v1/translate"

    hdr ={
    # Request headers
    'Content-Type': 'application/json',
    'Cache-Control': 'no-cache',
    'Ocp-Apim-Subscription-Key': '433480ed30184cc4a53b67cde36b6f63',
    }

    # Request body
    data =  {
        "in": "Translation text",
        "lang": "en-tw"
    }
    
    data = json.dumps(data)
    req = urllib.request.Request(url, headers=hdr, data = bytes(data.encode("utf-8")))

    req.get_method = lambda: 'POST'
    response = urllib.request.urlopen(req)
    print(response.getcode())
    print(response.read())
except Exception as e:
    print(e)
####################################