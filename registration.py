import pymysql, re
from flask import Flask, request, jsonify, json
from flask_limiter import Limiter
from werkzeug.contrib.fixers import ProxyFix
from flask_restful import Resource, Api
from auth import credentials
from pymysql.cursors import DictCursor
import hashlib, base64
from flask_cors import CORS

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