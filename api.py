# -*- coding: utf-8 -*-
"""
Some initial ideas for noun phrase queries (which is parsed from Hansard data in app.py)
"""
import os, sys
import getopt
import re
from bson.code import Code

from flask import Flask, request, jsonify, url_for
from flaskrun import flaskrun

from mako.template import Template
from pymongo import MongoClient

client = MongoClient('localhost', 27017)
db = client.hansard


def get_speaker_phrase_counts(speakername, how_many=25, from_date=None, to_date=None):
    ''' A list of phrases by number of occurrences '''  
    query = {"speakername": speakername}
    if from_date and to_date:
        query["date"] = {"$gte": from_date, "$lte": to_date}
    print query
    map = Code("function () {"
                "   emit(this.phrase,1);"
                "}")
    reduce = Code("function (key, values) {"
                "   return Array.sum(values)"
                "}")
    results = db.phrases.map_reduce(map, reduce, "results", query=query)
    for doc in results.find().sort("value", -1).limit(how_many):
        yield doc


def get_phrase_speaker_counts(phrase, how_many=25, from_date=None, to_date=None):
    ''' A list of speakers by number of occurrences for a phrase '''  
    query = {"phrase": phrase}
    if from_date and to_date:
        query["date"] = {"$gte": from_date, "$lte": to_date}
    map = Code("function () {"
                "   emit(this.speakername,1);"
                "}")
    reduce = Code("function (key, values) {"
                "   return Array.sum(values)"
                "}")
    results = db.phrases.map_reduce(map, reduce, "results", query=query)
    for doc in results.find().sort("value", -1).limit(how_many):
        yield doc

def get_phrase_speaker_heading_counts(phrase, speakername):
    ''' A list of speakers by number of occurrences for a phrase '''  
    query = {"phrase": phrase, "speakername": speakername}
    map = Code("function () {"
                "   emit(this.headingtitle + ' ('+ this.date + ')',1);"
                "}")
    reduce = Code("function (key, values) {"
                "   return Array.sum(values)"
                "}")
    results = db.phrases.map_reduce(map, reduce, "results", query=query)
    for doc in results.find().sort("value", -1):
        yield doc

def get_heading_phrase_counts(headingtitle, how_many=25):
    ''' A list of headings by number of occurrences for a phrase '''
    if headingtitle[-1]==')' and headingtitle[-4]=='-' and headingtitle[-12]=='(':
        date = headingtitle[-12:]
        headingtitle = headingtitle[:-12].strip()  
    query = {"headingtitle": headingtitle}
    map = Code("function () {"
                "   emit(this.phrase,1);"
                "}")
    reduce = Code("function (key, values) {"
                "   return Array.sum(values)"
                "}")
    results = db.phrases.map_reduce(map, reduce, "results", query=query)
    for doc in results.find().sort("value", -1).limit(how_many):
        yield doc

def get_phrase_heading_counts(phrase, speakername=None, how_many=25, from_date=None, to_date=None):
    ''' A list of headings by number of occurrences for a phrase '''  
    query = {"phrase": phrase}
    if from_date and to_date:
        query["date"] = {"$gte": from_date, "$lte": to_date}
    if speakername:
        query["speakername"] = speakername
    map = Code("function () {"
                "   emit(this.headingtitle + ' ('+ this.date + ')',1);"
                "}")
    reduce = Code("function (key, values) {"
                "   return Array.sum(values)"
                "}")
    results = db.phrases.map_reduce(map, reduce, "results", query=query)
    for doc in results.find().sort("value", -1).limit(how_many):
        yield doc


def get_phrase_usage(phrase, speakername=None):
    ''' A list of phrases by number of occurrences '''
    query = {"phrase": phrase}
    if speakername:
        query["speakername"] = speakername
    map = Code("function () {"
                "   emit(this.date.substring(0,7),1);"
                "}")
    reduce = Code("function (key, values) {"
                "   return Array.sum(values)"
                "}")
    results = db.phrases.map_reduce(map, reduce, "results", query=query)
    for doc in results.find().sort("_id", 1):
        yield doc


def get_phrases_containing(fragment, how_many=25, from_date=None, to_date=None, speakername=None):
    ''' A list of phrases containing some text '''  
    match = {"$match": {"phrase":re.compile(".*"+fragment+".*", re.IGNORECASE)}}
    if speakername:
        match["$match"]["speakername"] = speakername
    if from_date and to_date:
        match["$match"]["date"] = {"$gte": from_date, "$lte": to_date}
    results = db.phrases.aggregate([
        match, 
        {"$group" : {"_id":"$phrase", "count" : {"$sum" : 1}}}, 
        {"$sort": {"count": -1}},
        {"$limit" : how_many}
    ])
    for r in results:
        pass
        print r


app = Flask(__name__)
@app.route("/speaker/<speakername>")
def speaker_phrases(speakername):
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    if from_date and to_date:
        data_url = url_for('api_speaker_phrases', speakername=speakername, from_date=from_date, to_date=to_date)
    else:
        data_url = url_for('api_speaker_phrases', speakername=speakername)
    t = Template(filename='templates/rhetoric/bar-chart.html')
    return t.render(data_url=data_url)

@app.route("/api/v1.0/speaker/<speakername>")
def api_speaker_phrases(speakername):
    ret = {"items":[]}
    results = get_speaker_phrase_counts(speakername, how_many=50)
    for r in results:
        ret["items"].append({
            "label": str(r["_id"]), 
            "num": int(r["value"]),
            "url": url_for('phrase_speakers', phrase=str(r["_id"]))
            })
    return jsonify(**ret)

@app.route("/phrase/<phrase>")
@app.route("/phrase/<phrase>/speakers")
def phrase_speakers(phrase):
    title = "People who said '%s'" % phrase
    linked_title = "People who said '<a href='%s'>%s</a>'" % (url_for('phrase_usage',phrase=phrase), phrase)
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    if from_date and to_date:
        data_url = url_for('api_phrase_speakers', phrase=phrase, from_date=from_date, to_date=to_date)
        title += " between %s and %s" % (from_date, to_date)
    else:
        data_url = url_for('api_phrase_speakers', phrase=phrase)
    t = Template(filename='templates/rhetoric/bubble-chart.html')
    return t.render(
        data_url=data_url,
        title = title,
        linked_title=linked_title
    )

@app.route("/api/v1.0/phrase/<phrase>/speakers")
def api_phrase_speakers(phrase):
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    if from_date and to_date:
        results = get_phrase_speaker_counts(phrase, how_many=50, from_date=from_date, to_date=to_date)
    else:
        results = get_phrase_speaker_counts(phrase, how_many=50)
    ret = {"items":[]}
    for r in results:
        ret["items"].append({
            "label": str(r["_id"]), 
            "num": int(r["value"]),
            "url": url_for('phrase_speaker_headings', phrase=phrase, speakername=str(r["_id"]))
            })
    return jsonify(**ret)

@app.route("/phrase/<phrase>/speaker/<speakername>")
def phrase_speaker_headings(phrase, speakername):
    title = "where %s said '%s'" % (speakername, phrase)
    linked_title = "where <a href='%s'>%s</a> said '<a href='%s'>%s</a>'" % (
        url_for('speaker_phrases', speakername=speakername), speakername, 
        url_for('phrase_usage', phrase=phrase), phrase)
    data_url = url_for('api_phrase_speaker_headings', phrase=phrase, speakername=speakername)
    t = Template(filename='templates/rhetoric/bubble-chart.html')
    return t.render(
        data_url=data_url,
        title = title,
        linked_title=linked_title
    )

@app.route("/api/v1.0/phrase/<phrase>/speaker/<speakername>")
def api_phrase_speaker_headings(phrase, speakername):
    results = get_phrase_speaker_heading_counts(phrase, speakername)
    ret = {"items":[]}
    for r in results:
        ret["items"].append({
            "label": str(r["_id"]), 
            "num": int(r["value"]),
            "url": url_for('heading_phrases', headingtitle=str(r["_id"]))
            })
    return jsonify(**ret)

@app.route("/phrase/<phrase>/headings")
def phrase_headings(phrase):
    title = "where '%s' was said" % phrase
    linked_title = "where '<a href='%s'>%s</a>' was said" % (url_for('phrase_usage', phrase=phrase), phrase)
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    if from_date and to_date:
        data_url = url_for('api_phrase_headings', phrase=phrase, from_date=from_date, to_date=to_date)
        title += " between %s and %s" % (from_date, to_date)
    else:
        data_url = url_for('api_phrase_headings', phrase=phrase)
    t = Template(filename='templates/rhetoric/bubble-chart.html')
    return t.render(
        title = title,
        linked_title = linked_title,
        data_url=data_url
    )

@app.route("/api/v1.0/phrase/<phrase>/headings")
def api_phrase_headings(phrase):
    from_date = request.args.get('from_date')
    to_date = request.args.get('to_date')
    if from_date and to_date:
        results = get_phrase_heading_counts(phrase, how_many=50, from_date=from_date, to_date=to_date)
    else:
        results = get_phrase_heading_counts(phrase, how_many=50)
    ret = {"items":[]}
    for r in results:
        ret["items"].append({
            "label": str(r["_id"]), 
            "num": int(r["value"]),
            "url": url_for('heading_phrases', headingtitle=str(r["_id"]))
            })
    return jsonify(**ret)

@app.route("/heading/<headingtitle>/phrases")
def heading_phrases(headingtitle):
    title = "phrases used during '%s'" % headingtitle
    data_url = url_for('api_heading_phrases', headingtitle=headingtitle)
    t = Template(filename='templates/rhetoric/bar-chart.html')
    return t.render(
        data_url=data_url,
        title = title
    )

@app.route("/api/v1.0/heading/<headingtitle>/phrases")
def api_heading_phrases(headingtitle):
    results = get_heading_phrase_counts(headingtitle, how_many=50)
    ret = {"items":[]}
    for r in results:
        ret["items"].append({
            "label": str(r["_id"]), 
            "num": int(r["value"]),
            "url": url_for('phrase_speakers', phrase=str(r["_id"]))
            })
    return jsonify(**ret)

@app.route("/phrase/<phrase>/usage")
def phrase_usage(phrase):
    title = "when and how often '%s' was said" % phrase
    t = Template(filename='templates/rhetoric/line-chart.html')
    return t.render(
        data_url=url_for('api_phrase_usage', phrase=phrase),
        title = title
    )

@app.route("/api/v1.0/phrase/<phrase>/usage")
def api_phrase_usage(phrase):
    ret = {"filter_url": url_for('phrase_headings', phrase=phrase, from_date="FROM_DATE", to_date="TO_DATE"), "items":[]}
    results = get_phrase_usage(phrase)
    for r in results:
        ret["items"].append({
            "Date": str(r["_id"]), 
            "Usage": int(r["value"])
        })
    return jsonify(**ret)

if __name__=="__main__":
    flaskrun(app)

    """
    print 'get_speaker_phrase_counts("Christine Anne Milne")'
    get_speaker_phrase_counts("Christine Anne Milne")
    print 'get_speaker_phrase_counts("Christine Anne Milne", from_date="2006-02-08", to_date="2007-02-08")'
    get_speaker_phrase_counts("Christine Anne Milne", from_date="2006-02-08", to_date="2007-02-08")
    print 'get_phrase_speaker_counts("the government")'
    get_phrase_speaker_counts("the government")
    print 'get_phrase_usage("the government")'
    get_phrase_usage("the government")
    print 'get_phrase_usage("the government", speakername="Christine Anne Milne")'
    get_phrase_usage("the government", speakername="Christine Anne Milne")
    print 'get_phrases_containing("energy")'
    get_phrases_containing("energy")
    print 'get_phrases_containing("energy", speakername="Christine Anne Milne")'
    get_phrases_containing("energy", speakername="Christine Anne Milne")
    """