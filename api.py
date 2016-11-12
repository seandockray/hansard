# -*- coding: utf-8 -*-
"""
Some initial ideas for noun phrase queries (which is parsed from Hansard data in app.py)
"""
import os, sys
import getopt

import sqlite3

conn = sqlite3.connect('db.sql')

def get_noun_phrases_for_speaker(speakername, how_many=25, from_date=None, to_date=None):
    c = conn.cursor()
    if from_date and to_date:
        values = (speakername, from_date, to_date, how_many)
        c.execute('select phrase, count(phrase) from noun_phrases where speakername=? and date>=? and date<=? group by phrase order by count(phrase) desc limit ?', values)
    else:
        values = (speakername, how_many)
        c.execute('select phrase, count(phrase) from noun_phrases where speakername=? AND phrase NOT IN ("I","it") group by phrase order by count(phrase) desc limit ?', values)
    for row in c:
        print row
    c.close()


def get_phrase_usage(speakername, phrase, from_date=None, to_date=None):
    ''' Gets the count of how many time the speaker used this phrase between two optional dates '''
    c = conn.cursor()
    if from_date and to_date:
        values = (speakername, '%'+phrase+'%', from_date, to_date)
        c.execute('select count(phrase) from noun_phrases where speakername=? and phrase LIKE ? and date>=? and date<=? group by phrase', values)
    else:
        values = (speakername, '%'+phrase+'%')
        c.execute('select phrase, count(phrase) from noun_phrases where speakername=? and phrase LIKE ? group by phrase', values)
    for row in c:
        print row
    c.close()


def get_speakers_for_noun_phrase(phrase, how_many=25, from_date=None, to_date=None):
    c = conn.cursor()
    if from_date and to_date:
        values = (phrase, from_date, to_date, how_many)
        c.execute('select speakername, count(speakername) from noun_phrases where phrase=? and date>=? and date<=? group by speakername order by count(speakername) desc limit ?', values)
    else:
        values = (phrase, how_many)
        c.execute('select speakername, count(speakername) from noun_phrases where phrase=? group by speakername order by count(speakername) desc limit ?', values)
    for row in c:
        print row
    c.close()

def get_speakers_for_fragment(phrase, how_many=25, from_date=None, to_date=None):
    c = conn.cursor()
    if from_date and to_date:
        values = ('%'+phrase+'%', from_date, to_date, how_many)
        c.execute('select speakername, count(speakername) from noun_phrases where phrase LIKE ? and date>=? and date<=? group by speakername order by count(speakername) desc limit ?', values)
    else:
        values = ('%'+phrase+'%', how_many)
        c.execute('select speakername, count(speakername) from noun_phrases where phrase LIKE ? group by speakername order by count(speakername) desc limit ?', values)
    for row in c:
        print row
    c.close()

def get_noun_phrases_with(fragment, how_many=25, from_date=None, to_date=None):
    c = conn.cursor()
    if from_date and to_date:
        values = ('%'+fragment+'%', from_date, to_date, how_many)
        c.execute('select phrase, count(phrase) from noun_phrases where phrase LIKE ? and date>=? and date<=? group by phrase order by count(phrase) desc limit ?', values)
    else:
        values = ('%'+fragment+'%', how_many)
        c.execute('select phrase, count(phrase) from noun_phrases where phrase LIKE ? group by phrase order by count(phrase) desc limit ?', values)
    for row in c:
        print row
    c.close()

def load_noun_phrases(phrase, from_date=None, to_date=None):
    c = conn.cursor()
    if from_date and to_date:
        values = (phrase, from_date, to_date)
        c.execute('select * from noun_phrases where phrase=? and date>=? and date<=? order by date desc', values)
    else:
        values = (phrase,)
        c.execute('select * from noun_phrases where phrase=? order by date desc', values)
    for row in c:
        print row
    c.close()

def load_noun_phrases_for_speaker(phrase, speaker, from_date=None, to_date=None):
    c = conn.cursor()
    if from_date and to_date:
        values = (phrase, speaker, from_date, to_date)
        c.execute('select * from noun_phrases where phrase=? and speakername=? and date>=? and date<=? order by date desc', values)
    else:
        values = (phrase, speaker)
        c.execute('select * from noun_phrases where phrase=? and speakername=? order by date desc', values)
    for row in c:
        print row
    c.close()

def load_noun_phrases_by_fragment(fragment, from_date=None, to_date=None):
    c = conn.cursor()
    if from_date and to_date:
        values = ('%'+fragment+'%', from_date, to_date)
        c.execute('select * from noun_phrases where phrase LIKE ? and date>=? and date<=? order by date desc', values)
    else:
        values = ('%'+fragment+'%',)
        c.execute('select * from noun_phrases where phrase LIKE ? order by date desc', values)
    for row in c:
        print row
    c.close()

def load_noun_phrases_by_fragment_for_speaker(fragment, speaker, from_date=None, to_date=None):
    c = conn.cursor()
    if from_date and to_date:
        values = ('%'+fragment+'%', speaker, from_date, to_date)
        c.execute('select * from noun_phrases where phrase LIKE ? and speakername=? and date>=? and date<=? order by date desc', values)
    else:
        values = ('%'+fragment+'%', speaker)
        c.execute('select * from noun_phrases where phrase LIKE ? and speakername=? order by date desc', values)
    for row in c:
        print row
    c.close()


if __name__=="__main__":
    func = None
    arg1 = None
    arg2 = None
    try:
      opts, args = getopt.getopt(sys.argv[1:],"hf:x:y:",["function","x","y"])
    except getopt.GetoptError:
      print 'app.py -f -x -y'
      sys.exit(2)
    for opt, arg in opts:
      if opt == '-h':
         print 'app.py -f (function) -x (argument 1) -y (argument 2)'
         sys.exit()
      elif opt in ("-f", "--func"):
         func = arg
      elif opt in ("-x", "--x"):
         arg1 = arg
      elif opt in ("-y", "--y"):
         arg2 = arg
    if not func:
         print "You need to provide at least a function to call!"
         sys.exit()

    try:
        if arg1 and arg2:
            globals()[func](arg1, arg2)
        elif arg1:
            globals()[func](arg1)
        else:
            globals()[func]()
        # test, do another one
        get_noun_phrases_for_speaker('Ian Gordon Campbell')
    except:
        print "Error in function call"
    #get_noun_phrases_for_speaker('Ian Gordon Campbell')
    #get_speakers_for_noun_phrase('energy use')
    #get_noun_phrases_with('terror')
    #get_speakers_for_fragment('terror')
    #get_phrase_usage('Ian Gordon Campbell', 'energy use')
    #load_noun_phrases('energy use')
    #load_noun_phrases_for_speaker('energy use','Ian Gordon Campbell')
    #load_noun_phrases_by_fragment('terror')