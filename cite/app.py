from flask import Flask, render_template
import json


with open("secret.json", "r") as json_file:
    file_json = json.load(json_file)


app = Flask(__name__)


@app.route('/', methods=["GET"])
def index():
    return render_template('index.html')


if __name__ == "__main__":
    app.run(debug=file_json['debug'])
