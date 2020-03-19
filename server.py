import pymysql, re
from flask import Flask, request, jsonify, json
from flask_limiter import Limiter
from werkzeug.contrib.fixers import ProxyFix
from flask_restful import Resource, Api
from gevent.pywsgi import WSGIServer
from auth import credentials
from pymysql.cursors import DictCursor
import hashlib, base64

notFound = json.loads('{"ERROR" : "No data found"}')
adeptio_rate = 1000 # Set 1000 Adena = 1 ADE
adeptio_BuyRate = 600 # Set 1 Adeptio(ADE) = 600 ADE

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
limiter = Limiter(app, key_func=get_real_ip, default_limits=["20/minute"])
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

# http://127.0.0.1:9005/apiv1/getAdeptioUserInfo?account=adeptio
class getAdeptioUserInfo(Resource):
    def get(self):
        userAcc = request.args.get('account')
        cursorLG.execute("select balance from adeptio_balances WHERE login=%s;", userAcc)
        return jsonify(data=cursorLG.fetchall())

# http://127.0.0.1:9005/apiv1/getMoneyCount?charId=268481220
class getMoneyCount(Resource):
    def get(self):
        userCharId = int(request.args.get('charId'))
        cursor.execute("select count from items WHERE item_id=57 and owner_id=%s;", userCharId)
        return jsonify(data=cursor.fetchall())


# http://127.0.0.1:9005/apiv1/buyAdena?owner=268481220&count=1234&token=540215452&account=adeptio
class buyAdena(Resource):
    def get(self):
        success = json.loads('{"SUCCESS" : "Operation was successful"}')
        auth = json.loads('{"ERROR" : "User authentication failed!"}')
        loggedin = json.loads('{"ERROR" : "User logged in game. Please logout from L2-Corona server first"}')
        adeptioFail = json.loads('{"ERROR" : "User don\'t have enough Adeptio(ADE) to perform this operation"}')
        adeptioFail2 = json.loads('{"ERROR" : "User don\'t have enough Adeptio(ADE) to perform this operation. At least 1 required"}')
        adeptioFail3 = json.loads('{"ERROR" : "At least 1000 Adena required to perform this operation."}')
        account = str(request.args.get('account'))
        owner_id = str(request.args.get('owner'))
        count = int(request.args.get('count'))
        token = str(request.args.get('token'))
        cursor.execute("select online from characters WHERE charId=%s;", owner_id)
        onlineStatus = cursor.fetchall()
        cursorLG.execute("select balance from adeptio_balances WHERE login=%s", account)
        adeptioCountStatus = cursorLG.fetchall()

        try:
            print(adeptioCountStatus[0]['balance'])
        except:
            cursorLG.execute("replace into adeptio_balances (login, balance) values (%s, %s) ", (account, 0))
            print("WARNING! User balance initiated to - 0 (ADE)")

        cursorLG.execute("select balance from adeptio_balances WHERE login=%s", account)
        adeptioCountStatus = cursorLG.fetchall()

        if onlineStatus[0]['online'] != 0:
            return jsonify(data=loggedin)
        elif int(adeptioCountStatus[0]['balance']) <= 0: # Check if user have enough Adeptio(ADE) to sell
            return jsonify(data=adeptioFail2)
        elif int(count) >= 1000:
            return jsonify(data=adeptioFail3)
        elif int(adeptioCountStatus[0]['balance']) < int((count) / adeptio_BuyRate): # Check if user have enough Adeptio(ADE) to sell
            return jsonify(data=adeptioFail)
        elif account == '':
            return jsonify(data=auth)
        else:
            # Start checking user passw
            cursorLG.execute("select password from accounts WHERE login=%s;", account)
            userCheck = cursorLG.fetchall()

            if userCheck[0]['password'] == token:
                if count and count.isdigit():
                    cursor.execute("select count from items WHERE item_id=57 and owner_id=%s;", owner_id)
                    checkCurrentAdena = cursor.fetchall()
                    setAdenaFinal = (int(checkCurrentAdena[0]['count']) + count)
                    adeptioToSet = float(float(count) / float(adeptio_BuyRate))
                    cursor.execute("update items set count=%s WHERE item_id=57 and owner_id=%s;", (setAdenaFinal, owner_id))
                    cursorLG.execute("select balance from adeptio_balances WHERE login=%s", account)
                    checkBalance = cursorLG.fetchall()
                    setAdeptioFinal = float((float(checkBalance[0]['balance']) - float(adeptioToSet)))
                    cursorLG.execute("replace into adeptio_balances (login, balance) values (%s, %s) ", (account, setAdeptioFinal))
                    return jsonify(data=success)
            else:
                print('Failed adena change! Actual passw / user sent: ', userCheck[0]['password'], token)
                return jsonify(data=auth)




# http://127.0.0.1:9005/apiv1/sellAdena?owner=268481220&count=1234&token=540215452&account=adeptio
class sellAdena(Resource):
    def get(self):
        success = json.loads('{"SUCCESS" : "Operation was successful"}')
        auth = json.loads('{"ERROR" : "User authentication failed!"}')
        loggedin = json.loads('{"ERROR" : "User logged in game. Please logout from L2-Corona server first"}')
        adenaFail = json.loads('{"ERROR" : "User don\'t have enough adena to perform this operation"}')
        adenaFail2 = json.loads('{"ERROR" : "User don\'t have enough adena to perform this operation. At least 1000 required"}')
        account = str(request.args.get('account'))
        owner_id = str(request.args.get('owner'))
        count = int(request.args.get('count'))
        token = str(request.args.get('token'))
        cursor.execute("select online from characters WHERE charId=%s;", owner_id)
        onlineStatus = cursor.fetchall()
        cursor.execute("select count from items WHERE item_id=57 and owner_id=%s;", owner_id)
        adenaCountStatus = cursor.fetchall()

        if onlineStatus[0]['online'] != 0:
            return jsonify(data=loggedin)
        elif int(adenaCountStatus[0]['count']) <= 1000: # Check if user have enough adena to sell
            print(1)
            return jsonify(data=adenaFail2)
        elif int(count) >= 1000:
            print(2)
            return jsonify(data=adenaFail2)
        elif int(adenaCountStatus[0]['count']) < int(count): # Check if user have enough adena to sell
            return jsonify(data=adenaFail)
        elif account == '':
            return jsonify(data=auth)
        else:
            # Start checking user passw
            cursorLG.execute("select password from accounts WHERE login=%s;", account)
            userCheck = cursorLG.fetchall()

            if userCheck[0]['password'] == token:
                if count and count.isdigit():
                    setAdenaFinal = (int(adenaCountStatus[0]['count']) - count)
                    adeptioTopay = float(count / adeptio_rate)
                    cursor.execute("update items set count=%s WHERE item_id=57 and owner_id=%s;", (setAdenaFinal, owner_id))
                    cursorLG.execute("select balance from adeptio_balances WHERE login=%s", account)
                    checkBalance = cursorLG.fetchall()
                    setAdeptioFinal = float((int(checkBalance[0]['balance']) + float(adeptioTopay)))
                    cursorLG.execute("replace into adeptio_balances (login, balance) values (%s, %s) ", (account, setAdeptioFinal))
                    return jsonify(data=success)
            else:
                print('Failed adena change! Actual passw / user sent: ', userCheck[0]['password'], token)
                return jsonify(data=auth)

# http://127.0.0.1:9005/apiv1/register?user=test&passw=test&email=info@ababas.lt
class register(Resource):

    def get(self):
        already = json.loads('{"ERROR" : "User already exists?"}')
        fail = json.loads('{"ERROR" : "Invalid username/password or email. Please check your data"}')
        success = json.loads('{"SUCCESS" : "Registration successful"}')
        user = str(request.args.get('user'))
        passw = str(request.args.get('passw'))
        mail = str(request.args.get('email'))
        regex = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'
        hashBase64 = base64.b64encode(hashlib.sha1(passw.encode('utf8')).digest())

        # Query start
        if user != '' and passw != '':
            if (re.search(regex, mail)):
                try:
                    cursorLG.execute("insert into accounts (login, password, email) values (%s, %s, %s);", (user, hashBase64, mail))
                    return jsonify(data=success)
                except:
                    return jsonify(data=already)
            else:
                print("Failed mail check")
                print('email: ', mail)
                return jsonify(data=fail)
        else:
            print("Failed username/password check")
            print('user/passw: ', user, passw)
            return jsonify(data=fail)

# Routes
api.add_resource(getInfo, '/getInfo')
api.add_resource(getUserInfo, '/getUserInfo')
api.add_resource(getAdeptioUserInfo, '/getAdeptioUserInfo')
api.add_resource(getMoneyCount, '/getMoneyCount')
api.add_resource(register, '/register')
api.add_resource(sellAdena, '/sellAdena')
api.add_resource(buyAdena, '/buyAdena')

# Serve the high performance http server
if __name__ == '__main__':
    http_server = WSGIServer(('', 9005), app)
    http_server.serve_forever()