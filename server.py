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

con = pymysql.connect(credentials['ip'],credentials['user'],credentials['passw'],credentials['db'], autocommit=True)
con2 = pymysql.connect(credentials['ip'],credentials['user'],credentials['passw'],credentials['db2'], autocommit=True)
cursor = con.cursor(DictCursor)
cursorLG = con2.cursor(DictCursor)

def get_real_ip():
    print (str(request.remote_addr) + ' Client initiated request ->')
    return (request.remote_addr)

# Flask rules
app = Flask(__name__)
app.wsgi_app = ProxyFix(app.wsgi_app, num_proxies=1)
limiter = Limiter(app, key_func=get_real_ip, default_limits=["60/minute"])
app.url_map.strict_slashes = False
api = Api(app, prefix="/apiv1")

def checkInvalidChars(value):
    regex = re.compile('[@_!#$%^&*()<>?/\|}{~:,.}{+]')
    if (regex.search(value) == None):
        return 'OK'
    else:
        return 'FAIL'

# http://127.0.0.1:9005/apiv1/getInfo
class getInfo(Resource):
    def get(self):
        cursor.execute("select char_name,account_name,onlinetime,pvpkills,charId,`level` from characters")
        return jsonify(data=cursor.fetchall())

# http://127.0.0.1:9005/apiv1/getInfo?account=adeptio
class getUserInfo(Resource):
    def get(self):
        userAcc = request.args.get('account')
        cursor.execute("select char_name,account_name,onlinetime,pvpkills,charId,`level` from characters WHERE account_name=%s;", userAcc)
        return jsonify(data=cursor.fetchall())

# http://127.0.0.1:9005/apiv1/getMoneyCount?charId=268481220
class getMoneyCount(Resource):
    def get(self):
        userCharId = int(request.args.get('charId'))
        cursor.execute("select count from items WHERE item_id=57 and owner_id=%s;", userCharId)
        return jsonify(data=cursor.fetchall())

# http://127.0.0.1:9005/apiv1/sellAdena?owner=268481220&count=1234&token=t540215452
class sellAdena(Resource):
    def get(self):
        owner_id = str(request.args.get('owner'))
        count = int(request.args.get('count'))
        token = int(request.args.get('token'))
        if token != None:
            cursor.execute("update items set count=%s WHERE item_id=57 and owner_id=%s;", (count, owner_id))

        return jsonify(data=cursor.fetchall())


# http://127.0.0.1:9005/apiv1/register?user=test&passw=test
class register(Resource):
    def get(self):
        user = str(request.args.get('user'))
        passw = str(request.args.get('passw'))
        cursorLG.execute("insert into accounts (login, password) values (%s, %s);", (user, passw))
        return jsonify(data=cursorLG.fetchall())

# Routes
api.add_resource(getInfo, '/getInfo')
api.add_resource(getUserInfo, '/getUserInfo')
api.add_resource(getMoneyCount, '/getMoneyCount')
api.add_resource(register, '/register')
api.add_resource(sellAdena, '/sellAdena')

# Serve the high performance http server
if __name__ == '__main__':
    http_server = WSGIServer(('', 9005), app)
    http_server.serve_forever()