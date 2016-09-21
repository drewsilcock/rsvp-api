#!/usr/bin/env python

import json
import os

from os.path import isfile
from flask import Flask, make_response, request
from flask_pymongo import PyMongo
from flask_httpauth import HTTPBasicAuth
from bson import json_util
from passlib.apps import custom_app_context as pass_context


def log_debug(msg):
    print("[DBG] " + str(msg))


def log_info(msg):
    print("[INF] " + str(msg))


def log_warning(msg):
    print("[WRN] " + str(msg))


def log_error(msg):
    print("[ERR] " + str(msg))


rsvp_api = {
    "required_properties": [
        "name",
        "can_attend",
    ],
}

app = Flask(__name__)
app.config["MONGO_DBNAME"] = "rsvp"

db_url = os.environ.get("OPENSHIFT_MONGODB_DB_URL")
if db_url is not None:
    app.config["MONGO_URL"] = db_url

mongo = PyMongo(app)


def seed_users(users):
    for user in users:
        username = user["username"]
        raw_password = user["password"]

        with app.app_context():
            users = mongo.db.users.find({"username": username})
            if users.count() == 0:
                mongo.db.users.insert_one(create_user(username, raw_password))
                log_info("Added user" + username)


def create_user(username, raw_password):
    hashed_password = pass_context.encrypt(raw_password)
    return {"username": username, "password": hashed_password}


def read_secrets():
    secrets_fname = ".secrets.json"

    if not isfile(secrets_fname):
        raise IOError("Secrets file not found.")

    with open(secrets_fname, "r") as secrets_file:
        return json.loads(secrets_file.read())


secrets = read_secrets()
app.config["SECRET_KEY"] = secrets["key"]
auth = HTTPBasicAuth()
rsvp_api["users"] = secrets["users"]
seed_users(secrets["users"])


@auth.verify_password
def verify_passwd(username, password):
    user = mongo.db.users.find_one({"username": username})

    if user is not None:
        storedPassword = user["password"]
        return pass_context.verify(password, storedPassword)

    return False


@app.route("/")
@auth.login_required
def get_all_replies():
    replies = mongo.db.replies.find()
    return make_json_response(replies)


@app.route("/users/")
@auth.login_required
def get_users():
    users = mongo.db.users.find()
    return make_json_response(users)


@app.route("/name/<name>")
@auth.login_required
def get_name_replies(name):
    replies = mongo.db.replies.find_one_or_404({"name": name})
    return make_json_response(replies)


# Anonymous method
@app.route("/", methods=["POST"])
def add_reply():
    post_content = request.get_json()
    new_rsvp = get_rsvp(post_content)

    if new_rsvp is None:
        return make_api_response(400, "Bad Request", "RSVP is not valid.")

    mongo.db.replies.insert_one(new_rsvp)
    return make_api_response(200, "Ok", "Successfully added RSVP.")


@app.route("/name/<name>", methods=["DELETE"])
@auth.login_required
def delete_reply(name):
    mongo.db.replies.delete_one({"name": name})
    return make_api_response(200, "Ok", "Successfully deleted RSVP.")


@auth.error_handler
def basic_unauthenticated():
    return make_api_response(401, "Unauthorised", "Not authorised.")


@app.errorhandler(401)
def unauthenticated(error):
    return basic_unauthenticated()


@app.errorhandler(404)
def not_found(error):
    return make_api_response(404, "Not Found", "RSVP not found.")


@app.errorhandler(405)
def method_not_allowed(error):
    return make_api_response(
        405, "Method Not Allowed",
        "That method isn't allowed for that URL.")


def rsvp_is_valid(rsvp):
    """ Test whether an RSVP dictionary has all the required properties. """
    return all(prop in rsvp for prop in rsvp_api["required_properties"])


def get_rsvp(in_dict):
    if not rsvp_is_valid(in_dict):
        return None

    return ({
        "name": in_dict["name"],
        "can_attend": in_dict["can_attend"],
    })


def make_api_response(code, status, message):
    return make_json_response({
        "code": code,
        "status": status,
        "message": message
    }), code


def make_json_response(cursor):
    """
    Take a MongoDB cursor and produce a Flask Response with JSON serialisation
    of this, ignoring the ObjectId properties.
    """

    json_string = json_util.dumps(cursor)

    response = make_response(json_string)
    response.mimetype = "application/json"

    return response


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0")
