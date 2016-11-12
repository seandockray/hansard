# -*- coding: utf-8 -*-
"""
Some initial ideas for noun phrase queries (which is parsed from Hansard data in app.py)
"""
import os, sys
import getopt
import re

from pymongo import MongoClient
import sqlite3

client = MongoClient('localhost', 27017)
db = client.hansard
conn = sqlite3.connect('db.sql')


def get_speaker_phrase_counts(speakername, how_many=25, from_date=None, to_date=None):
    ''' A list of phrases by number of occurrences '''  
    match = {"$match": {"speakername":speakername}}
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


def get_phrase_speaker_counts(phrase, how_many=25, from_date=None, to_date=None):
    ''' A list of phrases by number of occurrences '''  
    match = {"$match": {"phrase":phrase}}
    if from_date and to_date:
        match["$match"]["date"] = {"$gte": from_date, "$lte": to_date}
    results = db.phrases.aggregate([
        match, 
        {"$group" : {"_id":"$speakername", "count" : {"$sum" : 1}}}, 
        {"$sort": {"count": -1}},
        {"$limit" : how_many}
    ])
    for r in results:
        pass
        print r


def get_phrase_usage(phrase, speakername=None):
    ''' A list of phrases by number of occurrences '''  
    match = {"$match": {"phrase":phrase}}
    if speakername:
        match["$match"]["speakername"] = speakername
    results = db.phrases.aggregate([
        match, 
        {"$group" : {"_id": { "$substr": ["$date",0,7] }, "count" : {"$sum" : 1}}}, 
        {"$sort": {"date": 1}}
    ])
    for r in results:
        pass
        print r


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
    get_speaker_phrase_counts("Christine Anne Milne")
    get_speaker_phrase_counts("Christine Anne Milne", from_date="2006-02-07", to_date="2007-02-07")
    get_phrase_speaker_counts("the government")
    get_phrase_usage("the government", speakername="Christine Anne Milne")
    get_phrases_containing("energy")
    get_phrases_containing("energy", speakername="Christine Anne Milne")