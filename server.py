##:: Author: Tomas Andriekus
##:: 2020-03-16 - 2020-03-22
##:: Description: This is a REST API prototype for Adeptio cryptocurrency & L2J Server Adena exchange.
##:: All work is done in a sprint mode without any good practices.

import pymysql, re
from flask import Flask, request, jsonify, json
from flask_limiter import Limiter
from werkzeug.contrib.fixers import ProxyFix
from flask_restful import Resource, Api
from gevent.pywsgi import WSGIServer
from auth import credentials
from pymysql.cursors import DictCursor
import hashlib, base64
import subprocess
import urllib.request
from flask_cors import CORS

notFound = json.loads('{"ERROR" : "No data found"}')
adeptio_rate = 10000 # Set 10000 Adena = 1 ADE
adeptio_BuyRate = 6000 # Set 1 Adeptio(ADE) = 6000 ADE

con = pymysql.connect(credentials['ip'],credentials['user'],credentials['passw'],credentials['db'], autocommit=True)
con2 = pymysql.connect(credentials['ip'],credentials['user'],credentials['passw'],credentials['db2'], autocommit=True)

def get_real_ip():
    print (str(request.remote_addr) + ' Client initiated request ->')
    return (request.remote_addr)

def createCursor(): # Game db
    con.ping(reconnect=True)
    cursor = con.cursor(DictCursor)
    return cursor

def createCursorLG(): # Login db
    con2.ping(reconnect=True)
    cursor = con2.cursor(DictCursor)
    return cursor

# Flask rules
app = Flask(__name__)
CORS(app)
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

def checkMail(value):
    regex = re.compile('@')
    if (regex.search(value) == None):
        return 'FAIL'
    else:
        return 'OK'

# http://127.0.0.1:9005/apiv1/getInfo
class getInfo(Resource):
    def get(self):
        cursor = createCursor()
        cursor.execute("SELECT characters.char_name, characters.account_name, characters.onlinetime, characters.pvpkills, "
                       "characters.charId, characters.level, characters.classid, clan_data.clan_name FROM characters "
                       "LEFT JOIN clan_data ON characters.clanid=clan_data.clan_id")
        cursor.close()
        return jsonify(data=cursor.fetchall())

# http://127.0.0.1:9005/apiv1/getWealth
class getWealth(Resource):
    def get(self):
        cursor = createCursor()
        cursor.execute("SELECT characters.char_name, characters.level, characters.classid, characters.clanid, items.count "
                       "FROM characters INNER JOIN items ON characters.charId=items.owner_id WHERE item_id=57 AND loc='INVENTORY' "
                       "GROUP BY count ORDER BY count DESC;")
        cursor.close()
        return jsonify(data=cursor.fetchall())

### Without REFERAL link;
'''
# http://127.0.0.1:9005/apiv1/register?user=test&passw=test&email=info@ababas.lt
class register(Resource):

    def get(self):
        cursorLG = createCursorLG()
        already = json.loads('{"ERROR" : "User already exists?"}')
        alreadyMail = json.loads('{"ERROR" : "Email already exists?"}')
        fail = json.loads('{"ERROR" : "Invalid username/password or email. Please check your data"}')
        success = json.loads('{"SUCCESS" : "Registration successful. Now you can start a game. Collect some adena first and login to your control panel"}')
        user = str(request.args.get('user'))
        passw = str(request.args.get('passw'))
        mail = str(request.args.get('email'))
        regex = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'
        hashBase64 = base64.b64encode(hashlib.sha1(passw.encode('utf8')).digest())

        # Check if mail exists?
        cursorLG.execute("SELECT email FROM accounts WHERE email=%s;", mail)
        checkMail = cursorLG.fetchall()

        try:
            if str(checkMail[0]['email']) == mail:
                return jsonify(data=alreadyMail)
        except:
            pass

        # Query start
        if user != '' and passw != '':
            if (re.search(regex, mail)):
                try:
                    cursorLG.execute("insert into accounts (login, password, email) values (%s, %s, %s);", (user, hashBase64, mail))
                    cursorLG.close()
                    return jsonify(data=success)
                except:
                    cursorLG.close()
                    return jsonify(data=already)
            else:
                print("Failed mail check")
                print('email: ', mail)
                cursorLG.close()
                return jsonify(data=fail)
        else:
            print("Failed username/password check")
            print('user/passw: ', user, passw)
            cursorLG.close()
            return jsonify(data=fail)
'''
### To create REF -> openssl rand -base64 3
# http://127.0.0.1:9005/apiv1/register?user=test&passw=test&email=info@ababas.lt&ref=aBc1
class register(Resource):

    def get(self):
        cursorLG = createCursorLG()
        already = json.loads('{"ERROR" : "User already exists?"}')
        alreadyMail = json.loads('{"ERROR" : "Email already exists?"}')
        alreadyRef = json.loads('{"ERROR" : "Referral code does not exist?"}')
        fail = json.loads('{"ERROR" : "Invalid username/password or email. Please check your data"}')
        success = json.loads('{"SUCCESS" : "Registration successful. Now you can start a game. Collect some adena first and login to your control panel"}')
        user = str(request.args.get('user'))
        passw = str(request.args.get('passw'))
        mail = str(request.args.get('email'))
        referral = str(request.args.get('ref'))
        regex = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'
        hashBase64 = base64.b64encode(hashlib.sha1(passw.encode('utf8')).digest())

        # Check if ref exists?
        cursorLG.execute("SELECT code FROM referral_code WHERE code=%s;", referral)
        checkRef = cursorLG.fetchall()

        try:
            if str(checkRef[0]['code']) == referral:
                pass
        except:
            return jsonify(data=alreadyRef)

        # Check if mail exists?
        cursorLG.execute("SELECT email FROM accounts WHERE email=%s;", mail)
        checkMail = cursorLG.fetchall()

        try:
            if str(checkMail[0]['email']) == mail:
                return jsonify(data=alreadyMail)
        except:
            pass

        # Query start
        if user != '' and passw != '':
            if (re.search(regex, mail)):
                try:
                    cursorLG.execute("insert into accounts (login, password, email) values (%s, %s, %s);", (user, hashBase64, mail))
                    cursorLG.close()

                    cursorLG.execute("DELETE FROM referral_code WHERE code=%s;", (referral))
                    cursorLG.close()

                    return jsonify(data=success)
                except:
                    cursorLG.close()
                    return jsonify(data=already)
            else:
                print("Failed mail check")
                print('email: ', mail)
                cursorLG.close()
                return jsonify(data=fail)
        else:
            print("Failed username/password check")
            print('user/passw: ', user, passw)
            cursorLG.close()
            return jsonify(data=fail)


# http://127.0.0.1:9005/apiv1/preregister?&email=info@ababas.lt
class preregister(Resource):

    def get(self):
        cursorLG = createCursorLG()

        ip = (str(request.remote_addr))
        fail = json.loads('{"ERROR" : "Invalid email. Please check your data"}')
        alreadyMail = json.loads('{"ERROR" : "Email already exists?"}')
        success = json.loads('{"SUCCESS" : "Notify successful."}')
        mail = str(request.args.get('email'))
        regex = '^\w+([\.-]?\w+)*@\w+([\.-]?\w+)*(\.\w{2,3})+$'

        # Check if mail exists?
        cursorLG.execute("SELECT email FROM pre_registration WHERE email=%s;", mail)
        checkMail = cursorLG.fetchall()

        try:
            if str(checkMail[0]['email']) == mail:
                return jsonify(data=alreadyMail)
        except:
            pass

        # Query start
        if (re.search(regex, mail)):
            try:
                cursorLG.execute("insert into pre_registration (email, lastIP) values (%s, %s);", (mail, ip))
                cursorLG.close()
                return jsonify(data=success)
            except:
                cursorLG.close()
                return jsonify(data=already)
        else:
            print("Failed mail check")
            print('email: ', mail)
            cursorLG.close()
            return jsonify(data=fail)


# http://127.0.0.1:9005/apiv1/getClans?
class getClans(Resource):
    def get(self):
        cursor = createCursor()
        cursor.execute("SELECT clan_name,reputation_score,hasCastle,ally_name,leader_id FROM clan_data;")
        cursor.close()
        return jsonify(data=cursor.fetchall())

# http://127.0.0.1:9005/apiv1/getUserClan?clanId=268518907
class getUserClan(Resource):
    def get(self):
        clanNum = request.args.get('clanId')
        cursor = createCursor()
        cursor.execute("SELECT clan_name,reputation_score,hasCastle,ally_name FROM clan_data WHERE clan_id=%s", clanNum)
        cursor.close()
        return jsonify(data=cursor.fetchall())

# http://127.0.0.1:9005/apiv1/getInfo?account=adeptio
class getUserInfo(Resource):
    def get(self):
        accountNotExist = json.loads('{"ERROR" : "Account don\'t exists"}')
        accountExists = json.loads('{"WARN" : "Account exists, but player don\'t have any characters. Probably not played yet?"}')
        cursor = createCursor()
        cursorLG = createCursorLG()
        userAcc = request.args.get('account')

        cursorLG.execute("select email from accounts where login=%s", (userAcc))
        cursorLG.close()
        result = cursorLG.fetchall()
        try:
            mailRes = checkMail(result[0]['email'])
            print('Checking if userAccount has a valid email. Mail: ', mailRes)
        except:
            return accountNotExist

        cursor.execute("SELECT char_name,account_name,onlinetime,pvpkills,charId,`level`,classid,clanid FROM characters WHERE "
                       "account_name=%s", userAcc)
        cursor.close()
        charData = cursor.fetchall()

        if str(charData) == '()':
            return accountExists
        else:
            return jsonify(data=charData)

# http://127.0.0.1:9005/apiv1/getAdeptioUserInfo?account=adeptio
class getAdeptioUserInfo(Resource):
    def get(self):
        cursorLG = createCursorLG()
        userAcc = request.args.get('account')
        cursorLG.execute("select balance from adeptio_balances WHERE login=%s;", userAcc)
        cursorLG.close()
        return jsonify(data=cursorLG.fetchall())

# http://127.0.0.1:9005/apiv1/getUserSellActivity?
class getUserSellActivity(Resource):
    def get(self):
        cursorLG = createCursorLG()
        cursorLG.execute("SELECT adena_count, created_time, country, adeptio_amount FROM adeptio_sold "
                        "GROUP BY created_time ORDER BY created_time DESC LIMIT 15;")
        cursorLG.close()
        return jsonify(data=cursorLG.fetchall())

# http://127.0.0.1:9005/apiv1/getUserBuyActivity?
class getUserBuyActivity(Resource):
    def get(self):
        cursorLG = createCursorLG()
        cursorLG.execute("SELECT adena_count, created_time, country, adeptio_amount FROM adeptio_bought "
                        "GROUP BY created_time ORDER BY created_time DESC LIMIT 15;")
        cursorLG.close()
        return jsonify(data=cursorLG.fetchall())

# http://127.0.0.1:9005/apiv1/getMoneyCount?charId=268481220
class getMoneyCount(Resource):
    def get(self):
        cursor = createCursor()
        userCharId = int(request.args.get('charId'))
        cursor.execute("SELECT count FROM items WHERE item_id=57 AND owner_id=%s;", userCharId)
        cursor.close()
        return jsonify(data=cursor.fetchall())

# http://127.0.0.1:9005/apiv1/getMoneyCount?account=adeptio
class getUserMoneyCount(Resource):
    def get(self):
        cursor = createCursor()
        theSum = 0
        account = str(request.args.get('account'))
        cursor.execute("select charId from characters WHERE account_name=%s;", account)
        allCharsIds = cursor.fetchall()
        for value in allCharsIds:
            cursor.execute("select count from items WHERE item_id=57 and owner_id=%s;", value['charId'])
            count = cursor.fetchall()
            try:
                theSum += int(count[0]['count'])
            except:
                theSum += 0

        cursor.close()
        return jsonify(data=theSum)

# http://127.0.0.1:9005/apiv1/buyAdena?owner=268481220&count=1234&token=540215452&account=adeptio
class buyAdena(Resource):
    def get(self):
        cursor = createCursor()
        cursorLG = createCursorLG()
        ip = (str(request.remote_addr))
        cf_header = dict(request.headers)
        country = ''
        success = json.loads('{"SUCCESS" : "Operation was successful. Your balance was updated."}')
        auth = json.loads('{"ERROR" : "User authentication failed!"}')
        charAdena = json.loads('{"ERROR" : "A provided character has to have at least 1 Adena in-game items list!"}')
        loggedin = json.loads('{"ERROR" : "User logged in game. Please logout from L2-Corona server first"}')
        adeptioFail = json.loads('{"ERROR" : "User don\'t have enough Adeptio(ADE) to perform this operation"}')
        adeptioFail2 = json.loads('{"ERROR" : "User don\'t have enough Adeptio(ADE) to perform this operation. At least 1 required"}')
        adeptioFail3 = json.loads('{"ERROR" : "At least 6000 Adena required to perform this operation."}')
        adeptioFail4 = json.loads('{"ERROR" : "Incorrect amount. At least 1 Adeptio (ADE) required"}')
        account = str(request.args.get('account'))
        owner_id = str(request.args.get('owner'))
        cursor.execute("SELECT char_name FROM characters WHERE charId=%s;", owner_id)
        characterName = cursor.fetchall()

        try:
            country = cf_header ['Cf-Ipcountry']
        except KeyError:
            country = 'unknown'

        try:
            print(int(request.args.get('count')))
        except:
            return jsonify(data=adeptioFail4)

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
            cursor.close()
            return jsonify(data=loggedin)
        elif int(adeptioCountStatus[0]['balance']) <= 0: # Check if user have enough Adeptio(ADE) to sell
            cursor.close()
            return jsonify(data=adeptioFail2)
        elif int(count) < 6000:
            cursor.close()
            return jsonify(data=adeptioFail3)
        elif int(adeptioCountStatus[0]['balance']) < int((count) / adeptio_BuyRate): # Check if user have enough Adeptio(ADE) to sell
            cursor.close()
            return jsonify(data=adeptioFail)
        elif account == '':
            cursor.close()
            return jsonify(data=auth)
        else:
            # Start checking user passw
            cursorLG.execute("select password from accounts WHERE login=%s;", account)
            userCheck = cursorLG.fetchall()

            if userCheck[0]['password'] == token:
                if count and int(count) > 0:
                    cursor.execute("select count from items WHERE item_id=57 and owner_id=%s;", owner_id)
                    checkCurrentAdena = cursor.fetchall()

                    try:
                        print(int(checkCurrentAdena[0]['count']))
                    except:
                        cursor.close()
                        return jsonify(data=charAdena)

                    setAdenaFinal = (int(checkCurrentAdena[0]['count']) + count)
                    adeptioToSet = int(int(count) / int(adeptio_BuyRate))
                    cursor.execute("update items set count=%s WHERE item_id=57 and owner_id=%s;", (setAdenaFinal, owner_id))
                    cursorLG.execute("select balance from adeptio_balances WHERE login=%s", account)
                    checkBalance = cursorLG.fetchall()
                    setAdeptioFinal = int((float(checkBalance[0]['balance']) - int(adeptioToSet)))
                    cursorLG.execute("replace into adeptio_balances (login, balance) values (%s, %s) ", (account, setAdeptioFinal))

                    cursorLG.execute(
                        "INSERT INTO adeptio_bought (account, adena_count, adeptio_amount, owner, password, ip, country) values (%s, %s, %s, %s, %s, %s, %s) ",
                        (account, count, int(adeptioToSet), str(characterName[0]['char_name']), token, ip, country))
                    cursorLG.close()

                    return jsonify(data=success)
            else:
                print('Failed adena change! Actual passw / user sent: ', userCheck[0]['password'], token)
                cursor.close()
                return jsonify(data=auth)




# http://127.0.0.1:9005/apiv1/sellAdena?owner=268481220&count=1234&token=540215452&account=adeptio
class sellAdena(Resource):
    def get(self):
        cursor = createCursor()
        cursorLG = createCursorLG()
        ip = (str(request.remote_addr))
        cf_header = dict(request.headers)
        country = ''
        success = json.loads('{"SUCCESS" : "Operation was successful. Your balance was updated."}')
        auth = json.loads('{"ERROR" : "User authentication failed!"}')
        charAdena = json.loads('{"ERROR" : "A provided character has to have at least 1 Adena in-game items list!"}')
        loggedin = json.loads('{"ERROR" : "User logged in game. Please logout from L2-Corona server first"}')
        adenaFail = json.loads('{"ERROR" : "User don\'t have enough adena to perform this operation"}')
        adenaFail2 = json.loads('{"ERROR" : "User don\'t have enough adena to perform this operation. At least 10 000 required"}')
        account = str(request.args.get('account'))
        owner_id = str(request.args.get('owner'))
        count = int(request.args.get('count'))
        token = str(request.args.get('token'))
        cursor.execute("SELECT online FROM characters WHERE charId=%s;", owner_id)
        onlineStatus = cursor.fetchall()
        cursor.execute("SELECT count FROM items WHERE item_id=57 and owner_id=%s;", owner_id)
        adenaCountStatus = cursor.fetchall()
        cursor.execute("SELECT char_name FROM characters WHERE charId=%s;", owner_id)
        characterName = cursor.fetchall()

        try:
            country = cf_header ['Cf-Ipcountry']
        except KeyError:
            country = 'unknown'

        try:
            print(int(adenaCountStatus[0]['count']))
        except:
            cursor.close()
            return jsonify(data=charAdena)

        if onlineStatus[0]['online'] != 0:
            cursor.close()
            return jsonify(data=loggedin)
        elif int(adenaCountStatus[0]['count']) <= 10000: # Check if user have enough adena to sell
            cursor.close()
            return jsonify(data=adenaFail2)
        elif int(count) < 10000:
            cursor.close()
            return jsonify(data=adenaFail2)
        elif int(adenaCountStatus[0]['count']) < int(count): # Check if user have enough adena to sell
            cursor.close()
            return jsonify(data=adenaFail)
        elif account == '':
            cursor.close()
            return jsonify(data=auth)
        else:
            # Start checking user passw
            cursorLG.execute("select password from accounts WHERE login=%s;", account)
            userCheck = cursorLG.fetchall()

            if userCheck[0]['password'] == token:
                if count and int(count) > 0:
                    setAdenaFinal = (int(adenaCountStatus[0]['count']) - count)
                    adeptioTopay = int(count / adeptio_rate)
                    cursor.execute("update items set count=%s WHERE item_id=57 and owner_id=%s;", (setAdenaFinal, owner_id))
                    cursorLG.execute("select balance from adeptio_balances WHERE login=%s", account)
                    checkBalance = cursorLG.fetchall()

                    try:
                        print(checkBalance[0]['balance'])
                    except:
                        cursorLG.execute("replace into adeptio_balances (login, balance) values (%s, %s) ", (account, 0))
                        print("WARNING! User balance initiated to - 0 (ADE)")

                    cursorLG.execute("select balance from adeptio_balances WHERE login=%s", account)
                    checkBalance = cursorLG.fetchall()

                    setAdeptioFinal = int((int(checkBalance[0]['balance']) + int(adeptioTopay)))
                    cursorLG.execute("replace into adeptio_balances (login, balance) values (%s, %s) ", (account, setAdeptioFinal))

                    cursorLG.execute(
                        "INSERT INTO adeptio_sold (account, adena_count, adeptio_amount, owner, password, ip, country) values (%s, %s, %s, %s, %s, %s, %s) ",
                        (account, count, int(adeptioTopay), str(characterName[0]['char_name']), token, ip, country))
                    cursorLG.close()

                    return jsonify(data=success)
            else:
                print('Failed adena change! Actual passw / user sent: ', userCheck[0]['password'], token)
                cursor.close()
                return jsonify(data=auth)


class getOnline(Resource):
    def get(self):
        cursor = createCursor()
        cursor.execute("select char_name from characters WHERE online=1 or online=2;")
        cursor.close()
        return jsonify(data=cursor.fetchall())

# http://127.0.0.1:9005/apiv1/depositAdeptio?token=540215452&account=adeptio
class depositAdeptio(Resource):
    def get(self):
        cursorLG = createCursorLG()
        auth = json.loads('{"ERROR" : "User authentication failed!"}')
        account = str(request.args.get('account'))
        token = str(request.args.get('token'))
        cursorLG.execute("select password from accounts WHERE login=%s;", account)
        userCheck = cursorLG.fetchall()

        if userCheck[0]['password'] == token:
            host = credentials['rpc']
            user = credentials['rpcuser']
            passwd= credentials['rpcpassword']
            timeout = credentials['rpcclienttimeout']
            command = 'adeptio-cli -rpcconnect=' + host + ' -rpcuser=' + user + ' -rpcpassword=' + passwd  + ' -rpcclienttimeout=' + timeout + ' getnewaddress'
            result = subprocess.check_output(command,shell=True).strip()
            onlyWlt = result.decode("utf-8")
            cursorLG.execute("update adeptio_balances set lastdepositwlt=%s WHERE login=%s;", (onlyWlt, account))
            cursorLG.close()
            return jsonify(data=result.decode("utf-8"))
        else:
            print('Failed Adeptio deposit! Actual passw / user sent: ', userCheck[0]['password'], token)
            cursorLG.close()
            return jsonify(data=auth)

# http://127.0.0.1:9005/apiv1/depositAdeptioApproval?token=540215452&account=adeptio&wlt=AGKpzTYSQrVTBshqXLyhja9hhBtDEv3rNn&count=123
class depositAdeptioApproval(Resource):
    def get(self):
        cursorLG = createCursorLG()
        ip = (str(request.remote_addr))
        cf_header = dict(request.headers)
        country = ''
        success = json.loads('{"SUCCESS" : "Operation was successful. Your balance was updated."}')
        failedwlt = json.loads('{"ERROR" : "This is not correct wallet to update the adeptio coins"}')
        failedCount = json.loads('{"ERROR" : "Unknown amount?"}')
        failedExplorer = json.loads('{"ERROR" : "Unknown amount from explorer. Do you really sent the coins to deposit address? If yes, please wait at least up-to 15 minutes."}')
        failedAmount = json.loads('{"ERROR" : "Amount not match? Looks like you sent the coins but amount you provided don\'t match with actually sent coins"}')
        auth = json.loads('{"ERROR" : "User authentication failed!"}')
        header = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) l2corona.adeptio.cc'}
        provider = 'https://explorer.adeptio.cc/ext/getbalance/'
        wallet = str(request.args.get('wlt'))
        url = (provider + wallet)
        account = str(request.args.get('account'))
        token = str(request.args.get('token'))
        count = int(request.args.get('count'))

        try:
            country = cf_header ['Cf-Ipcountry']
        except KeyError:
            country = 'unknown'

        # Read count from explorer
        req = urllib.request.Request(url, headers=header)
        response = urllib.request.urlopen(req)

        try:
            restmp = int(response.read())
            print(int(restmp))
        except:
            cursorLG.close()
            return jsonify(data=failedExplorer)

        cursorLG.execute("select password from accounts WHERE login=%s;", account)
        userCheck = cursorLG.fetchall()

        if userCheck[0]['password'] == token:
            cursorLG.execute("select lastdepositwlt from adeptio_balances WHERE login=%s;", account)
            walletCheck = cursorLG.fetchall()

            if walletCheck[0]['lastdepositwlt'] == wallet and walletCheck[0]['lastdepositwlt'] != None:

                if (restmp == int(count)):
                    cursorLG.execute("select balance from adeptio_balances WHERE login=%s", account)
                    currentAdeptioBalance = cursorLG.fetchall()

                    try:
                        print(currentAdeptioBalance[0]['balance'])
                    except:
                        cursorLG.execute("replace into adeptio_balances (login, balance) values (%s, %s) ", (account, 0))
                        print("WARNING! User balance initiated to - 0 (ADE)")

                    cursorLG.execute("select balance from adeptio_balances WHERE login=%s", account)
                    currentAdeptioBalance = cursorLG.fetchall()

                    setNewAdeptioBalance = int(int(currentAdeptioBalance[0]['balance']) + int(count))

                    if count and count > 0:
                        cursorLG.execute("replace into adeptio_balances set login=%s, balance=%s, lastdepositwlt=%s;", (account, setNewAdeptioBalance, None))

                        cursorLG.execute(
                            "INSERT INTO adeptio_deposits (account, balance_before, ade_count, wallet, password, ip, country) values (%s, %s, %s, %s, %s, %s, %s) ",
                            (account, int(currentAdeptioBalance[0]['balance']), count, wallet, token, ip, country))
                        cursorLG.close()

                        return jsonify(data=success)
                    else:
                        cursorLG.close()
                        return jsonify(data=failedCount)
                else:
                    cursorLG.close()
                    return jsonify(data=failedAmount)
            else:
                cursorLG.close()
                return jsonify(data=failedwlt)
        else:
            print('Failed Adeptio deposit! Actual passw / user sent: ', userCheck[0]['password'], token)
            cursorLG.close()
            return jsonify(data=auth)


# http://127.0.0.1:9005/apiv1/getCryptoPrices?
class getCryptoPrices(Resource):
    def get(self):
        fail = json.loads('{"ERROR" : "Failed to find crypto prices"}')
        header = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) l2corona.adeptio.cc'}
        provider = 'https://api.crex24.com/v2/public/tickers?instrument=ADE-BTC,BTC-USDPM'
        req = urllib.request.Request(provider, headers=header)
        response = urllib.request.urlopen(req)

        try:
            restmp = response.read()
            cont = json.loads(restmp.decode('utf-8'))
            adePrice = float(cont[0]['last'])
            btcPrice = float(cont [1] ['last'])
            return jsonify(data=(adePrice,btcPrice))
        except:
            return jsonify(data=fail)


# http://127.0.0.1:9005/apiv1/withdrawAdeptio?token=540215452&account=adeptio&wlt=AGKpzTYSQrVTBshqXLyhja9hhBtDEv3rNn&count=123
class withdrawAdeptio(Resource):
    def get(self):
        cursorLG = createCursorLG()
        ip = (str(request.remote_addr))
        cf_header = dict(request.headers)
        country = ''
        auth = json.loads('{"ERROR" : "User authentication failed!"}')
        wrongAmount = json.loads('{"ERROR" : "Wrong amount"}')
        wrongWlt = json.loads('{"ERROR" : "Invalid wallet provided. Please check the wallet addr!"}')
        notEnoughAdeptio = json.loads('{"ERROR" : "You don\'t have enough Adeptio to withdraw this amount"}')
        adeptioFail4 = json.loads('{"ERROR" : "Incorrect amount. At least 1 Adeptio (ADE) required"}')
        account = str(request.args.get('account'))
        token = str(request.args.get('token'))
        wallet = str(request.args.get('wlt'))

        try:
            country = cf_header ['Cf-Ipcountry']
        except KeyError:
            country = 'unknown'

        try:
            print(int(request.args.get('count')))
        except:
            return jsonify(data=adeptioFail4)

        count = int(request.args.get('count'))

        if len(wallet) != 34:
            cursorLG.close()
            return jsonify(data=wrongWlt)

        if wallet[0] != 'A':
            cursorLG.close()
            return jsonify(data=wrongWlt)

        cursorLG.execute("select balance from adeptio_balances WHERE login=%s;", account)
        checkBalance = cursorLG.fetchall()

        try:
            print(checkBalance[0]['balance'])
        except:
            return jsonify(data=notEnoughAdeptio)

        if checkBalance[0]['balance'] < int(count):
            cursorLG.close()
            return jsonify(data=notEnoughAdeptio)

        cursorLG.execute("select password from accounts WHERE login=%s;", account)
        userCheck = cursorLG.fetchall()

        if userCheck[0]['password'] == token:
            if count and int(count) > 0:
                host = credentials['rpc']
                user = credentials['rpcuser']
                passwd= credentials['rpcpassword']
                timeout = credentials['rpcclienttimeout']
                command = '/usr/bin/adeptio-cli -rpcconnect=' + host + ' -rpcuser=' + user + ' -rpcpassword=' + passwd  + ' -rpcclienttimeout=' + timeout + ' sendtoaddress ' + wallet + ' ' + str(count)
                result = subprocess.check_output(command,shell=True).strip()
                print("Making a transaction: ", command)
                print("Tx result: ", result)

                cursorLG.execute("select balance from adeptio_balances WHERE login=%s", account)
                currentAdeptioBalance = cursorLG.fetchall()

                setNewAdeptioBalance = int(int(currentAdeptioBalance[0]['balance']) - int(count))

                cursorLG.execute("REPLACE INTO adeptio_balances (login, balance, lastwithdrawalwlt) values (%s, %s, "
                                 "%s) ", (account, setNewAdeptioBalance, wallet))

                cursorLG.execute(
                    "INSERT INTO adeptio_withdraws (account, balance_before, ade_count, wallet, password, ip, "
                    "country, txid) values (%s, %s, %s, %s, %s, %s, %s, %s) ",
                    (account, int(currentAdeptioBalance[0]['balance']), count, wallet, token, ip, country, str(result)))
                cursorLG.close()

                return jsonify(data=result.decode("utf-8"))
            else:
                cursorLG.close()
                return jsonify(data=wrongAmount)
        else:
            print('Failed Adeptio withdrawal! Actual passw / user sent: ', userCheck[0]['password'], token)
            cursorLG.close()
            return jsonify(data=auth)

# Routes
api.add_resource(getInfo, '/getInfo')
api.add_resource(getOnline, '/getOnline')
api.add_resource(getClans, '/getClans')
api.add_resource(getUserSellActivity, '/getUserSellActivity')
api.add_resource(getUserBuyActivity, '/getUserBuyActivity')
api.add_resource(getWealth, '/getWealth')
api.add_resource(getUserClan, '/getUserClan')
api.add_resource(getUserInfo, '/getUserInfo')
api.add_resource(getCryptoPrices, '/getCryptoPrices')
api.add_resource(getAdeptioUserInfo, '/getAdeptioUserInfo')
api.add_resource(getMoneyCount, '/getMoneyCount')
api.add_resource(getUserMoneyCount, '/getUserMoneyCount')
api.add_resource(register, '/register')
api.add_resource(preregister, '/preregister')
api.add_resource(sellAdena, '/sellAdena')
api.add_resource(buyAdena, '/buyAdena')
api.add_resource(depositAdeptio, '/depositAdeptio')
api.add_resource(withdrawAdeptio, '/withdrawAdeptio')
api.add_resource(depositAdeptioApproval, '/depositAdeptioApproval')

# Serve the high performance http server
if __name__ == '__main__':
    http_server = WSGIServer(('', 9005), app)
    http_server.serve_forever()