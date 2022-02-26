from flask import Flask, render_template, url_for, send_from_directory, request, session, redirect
from oauth import Oauth
from flaskext.mysql import MySQL
import hashlib
import json
import os

with open("secret.json", "r") as json_file:
    file_json = json.load(json_file)


app = Flask(__name__)
app.config['MYSQL_DATABASE_HOST'] = file_json['mysql']['host']
app.config['MYSQL_DATABASE_USER'] = file_json['mysql']['user']
app.config['MYSQL_DATABASE_PASSWORD'] = file_json['mysql']['password']
app.config['MYSQL_DATABASE_DB'] = file_json['mysql']['database']
app.config['MYSQL_CONNECT_TIMEOUT'] = file_json['mysql']['timeout']
app.secret_key = file_json['key']
mysql = MySQL(app)


@app.route('/', methods=["GET"])
def index():
    return render_template('index.html')


@app.route('/ecnh', methods=["GET"])
def index():
    return render_template('enchant.html')



@app.route('/reg', methods=["GET","POST"])
def reg():
    if request.method == 'GET':
        return render_template('registr.html', text='')
    else:
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        h = str(hashlib.md5(password.strip().encode('utf-8')).hexdigest())
        cur = mysql.connection.cursor()
        if cur.execute(f'SELECT id FROM users WHERE id = {name}') is None:
            cur.execute('INSERT INTO user (name, email,password, h1) VALUES (%s, %s,%s, %s)')
            mysql.connection.commit()
            session['name'] = name
            session['email'] = email
            return render_template('registr.html', text='Вы успешно зарегистрировались')
        else:
            return render_template('registr.html', text='Такой ник уже есть')


@app.route('/oauth', methods=["GET"])
def oauth():
    code = request.args.get("code")
    at = Oauth.get_acces_token(code)

    user_json = Oauth.get_user_json(at)
    username1, usertag = user_json.get("username"), user_json.get("discriminator")
    id = user_json("id")
    username = f"{username1}#{usertag}"

@app.route('/oa', methods=["GET"])
def oa():
    return redirect(Oauth.discord_login_url)

if __name__ == "__main__":
    app.run(debug=file_json['debug'])
