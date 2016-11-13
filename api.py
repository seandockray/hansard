# -*- coding: utf-8 -*-
"""
Some initial ideas for noun phrase queries (which is parsed from Hansard data in app.py)
"""
import os, sys
import getopt
import re
from bson.code import Code

from pymongo import MongoClient
import sqlite3

client = MongoClient('localhost', 27017)
db = client.hansard
conn = sqlite3.connect('db.sql')


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
        print doc


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
        print doc


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
        print doc


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


if __name__=="__main__":
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