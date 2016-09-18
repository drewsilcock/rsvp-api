#!/usr/bin/env python

from flask import Flask, make_response, request
from flask_pymongo import PyMongo
from bson import json_util


app = Flask(__name__)
app.config["MONGO_DBNAME"] = "rsvp"
mongo = PyMongo(app)

rsvp_api = {
    "required_properties": [
        "name",
        "can_attend",
    ],
}


@app.route("/")
def get_all_replies():
    replies = mongo.db.replies.find()
    return make_json_response(replies)


@app.route("/name/<name>")
def get_name_replies(name):
    replies = mongo.db.replies.find_one_or_404({"name": name})
    return make_json_response(replies)


@app.route("/", methods=["POST"])
def add_reply():
    new_reply = request.get_json()

    if not rsvp_is_valid(new_reply):
        return make_api_response(400, "Bad Request", "RSVP is not valid.")

    mongo.db.replies.insert_one(new_reply)
    return make_api_response(200, "Ok", "Successfully added RSVP.")


@app.errorhandler(404)
def page_not_found(error):
    return make_api_response(404, "Not Found", "RSVP not found.")


def rsvp_is_valid(rsvp):
    """ Test whether an RSVP dictionary has all the required properties. """
    return all(prop in rsvp for prop in rsvp_api["required_properties"])


def make_api_response(code, status, message):
    return make_json_response(
        {"status": status,
         "message": message}), code


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
    app.run(debug=True)
