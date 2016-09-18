#!/usr/bin/env python

from flask import Flask, make_response, jsonify, request
from flask_pymongo import PyMongo
from bson import json_util


app = Flask(__name__)
app.config["MONGO_DBNAME"] = "rsvp"
mongo = PyMongo(app)


@app.route("/")
def hello_all():
    replies = mongo.db.replies.find()
    return make_json_response(replies)


@app.route("/name/<name>")
def get_name_replies(name):
    replies = mongo.db.replies.find_one_or_404({"name": name});
    return make_json_response(replies);


@app.route("/", methods=["POST"])
def add_person():
    body = request.get_json()
    mongo.db.replies.insert_one(body);
    return make_json_response({"response": "OK", "message": "Successfully added RSVP."})


@app.errorhandler(404)
def page_not_found(error):
    response = { "response": 404, "message": "RSVP not found." }
    return make_json_response(response)


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
