import pymysql
from flask import Flask, request, jsonify, json
from flask_limiter import Limiter
from werkzeug.contrib.fixers import ProxyFix
from flask_restful import Resource, Api
from gevent.pywsgi import WSGIServer
from time import gmtime, strftime
import urllib.request
import re
from auth import credentials
from pymysql.cursors import DictCursor

notFound = json.loads('{"ERROR" : "No data found"}')

con = pymysql.connect(credentials[ip],credentials[user],credentials[passw],credentials[db] )
cursor = con.cursor(DictCursor)

def get_real_ip():
    print (str(request.remote_addr) + ' Client initiated request ->')
    return (request.remote_addr)

# Flask rules
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, num_proxies=1)
limiter = Limiter(app, key_func=get_real_ip, default_limits=["60/minute"])
app.url_map.strict_slashes = False
api = Api(app, prefix="/apiv1/")

def checkInvalidChars(value):
    regex = re.compile('[@_!#$%^&*()<>?/\|}{~:,.}{+]')
    if (regex.search(value) == None):
        return 'OK'
    else:
        return 'FAIL'

# http://127.0.0.1:9005/apiv1/getInfo
class getInfo(Resource):
    def get(self):
        cursor.execute("select char_name,account_name,charId,`level` from characters;")
        return jsonify(data=cursor.fetchall())

# Routes
api.add_resource(getInfo, '/getInfo')

# Serve the high performance http server
if __name__ == '__main__':
    http_server = WSGIServer(('', 9005), app)
    http_server.serve_forever()
