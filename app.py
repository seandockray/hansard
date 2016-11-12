# -*- coding: utf-8 -*-

import os, sys
import getopt
import xml.etree.ElementTree as etree      
import urllib
from sgmllib import SGMLParser
from HTMLParser import HTMLParser

from mako.template import Template
import sqlite3

representative_debates_loc = 'http://data.openaustralia.org/scrapedxml/representatives_debates/'
senate_debates_loc = 'http://data.openaustralia.org/scrapedxml/senate_debates/'
conn = sqlite3.connect('db.sql')

class URLLister(SGMLParser):
    def reset(self):
        SGMLParser.reset(self)
        self.urls = []

    def start_a(self, attrs):
        href = [v for k, v in attrs if k=='href']
        if href:
            self.urls.extend(href)

class MLStripper(HTMLParser):
    def __init__(self):
        self.reset()
        self.fed = []
    def handle_data(self, d):
        self.fed.append(d)
    def get_data(self):
        return ''.join(self.fed)

class Major(object):
    def __init__(self, title, id):
        self.title = title
        self.id = id
        self.minors = []

class Minor(object):
    def __init__(self, title, id):
        self.title = title
        self.id = id
        self.timeline = []
        self.current_speech = None

    def add_event(self, type, data):
        if type=='speech' and self.current_speech and data['talktype']!='speech':
            self.current_speech.add(data)
        elif type=='speech' and self.current_speech and data['talktype']=='speech' and (data['approximate_wordcount']<50):
            data['talktype'] = 'interjection'
            self.current_speech.add(data)
        elif type=='speech':
            if self.current_speech:
                self.timeline.append(self.current_speech)
            self.current_speech = Speech(data)
        elif self.current_speech:
            self.timeline.append(self.current_speech)
            self.current_speech = None
        else:
            self.timeline.append((type, data))

    def print_timeline(self):
        for event in self.timeline:
            if type(event) is Speech:
                print '...',event.speakername, event.participants()
                print event.interjections()
            else:
                print '...',event[0]

    def interjected_speeches(self):
        ''' Returns all speeches with interjections '''
        for event in self.timeline:
            if type(event) is Speech:
                interjections = event.interjections()
                if interjections:
                    yield event, interjections

class Speech(object):
    def __init__(self, data):
        self.speakername = data['speakername']
        self.id = data['id']
        self.url = data['url']
        self.time = data['time']
        self.parts = [data,]
        self.bickers = []

    def add(self, data):
        self.parts.append(data)

    def participants(self):
        return [d['speakername'] for d in self.parts]

    def get_script(self):
        text = []
        for p in self.parts:
            text.append((p['speakername'], to_text(p['node'])))
        return text

    def interjections(self, include_supplementary_questions=False, min_run=3):
        interjections = []
        for p in self.parts:
            if p['talktype']=='interjection':
                t = to_text(p['node'])
                interjections.append((p['speakername'], t)) 
            elif p['talktype']=='continuation' and p['approximate_wordcount']<150:
                t = to_text(p['node'])
                interjections.append((p['speakername'], t))
            elif p['talktype']=='continuation':
                t = to_text(p['node'], 1)
                interjections.append((p['speakername'], t))
            elif p['talktype']=='speech' and len(self.parts)>1:
                t = to_text(p['node'], -1)
                interjections.append((p['speakername'], t))
        # filtering out supplementary questions, which aren't that interesting
        if not include_supplementary_questions and len(interjections)<4:
            for i in interjections:
                if 'supplementary question' in i[1] or 'final supplementary question' in i[1]:
                    interjections = [] 
        # filter out anything below the minimu run
        if len(interjections)<min_run:
            interjections = []
        return interjections


def to_text(node, truncate=False):
    r = ''
    paras = []
    for p in node:
        try:
            paras.append('<%s>%s</%s>' % (p.tag, etree.tostring(p, method='html'), p.tag))
        except:
            pass
    if not truncate:
        return "\n".join(paras)
    elif truncate>0:
        return "\n".join(paras[:truncate])
    elif truncate<0:
        return "\n".join(paras[truncate:])


def handle_major_heading(node):
    return node.text.strip(), node.attrib['id'].split('/')[-1]
    #print node.attrib
    pass

def handle_minor_heading(node):
    return node.text.strip(), node.attrib['id'].split('/')[-1]
    #print node.attrib
    pass

def handle_speech(node):
    ret = {'speakername': '', 'talktype': '', 'approximate_wordcount': 0, 'url': '', 'time':'', 'id':'', 'node': node}
    if 'speakername' not in node.attrib or ('nospeaker' in node.attrib and node.attrib['nospeaker']=='true'):
        ret['speakername'] = '***'
    else:
        ret['speakername'] = node.attrib['speakername']
    ret['url'] = node.attrib['url']
    ret['time'] = node.attrib['time']
    ret['id'] = node.attrib['id'].split('/')[-1]
    ret['talktype'] = 'interjection' if ret['speakername'] in ['Opposition Senators','Honourable Senators'] else node.attrib['talktype']
    ret['approximate_wordcount'] = int(node.attrib['approximate_wordcount'])
    return ret

def handle_bills(node):
    ''' Handles bills '''
    return
    #print node.attrib
    print '= BILLS'
    for child in node:
        if child.tag=='bill':
            # {url, id}
            print '- ', child.text

def handle_division(node):
    ''' Handles a division (a vote) '''
    return
    time = node.attrib['time']
    counts = {}
    for child in node:
        if child.tag=='divisioncount':
            counts = child.attrib
    print 'division at %s' % time
    print counts
    


def handle(node):
    ''' Handles any kind of node '''
    func_name = 'handle_%s' % node.tag.replace('-','_')
    try:
        return globals()[func_name](node)
    except NameError:
        print "I can't handle these tags yet: ", node.tag
        return False


def stats(node):
    ''' Gets numbers of different components of transcript '''
    counts = {}
    for child in root: 
        if child.tag not in counts:
            counts[child.tag] = 1
        else:
            counts[child.tag] += 1
    return counts


def process_xml(xml_file):
    ''' Processes an xml file returning majors '''
    tree = etree.parse(xml_file)
    root = tree.getroot()
    #print stats(root)
    majors = []
    for child in root:
        data = handle(child)
        if child.tag=='major-heading':
            majors.append(Major(data[0], data[1]))
        elif child.tag=='minor-heading':
            majors[-1].minors.append(Minor(data[0], data[1]))
        else:
            majors[-1].minors[-1].add_event(child.tag, data)
    return majors

def xml_to_interjections(xml_file, html_file, date, prev):
    ''' Extracts all interjections from an xml file and saves to html '''
    majors = process_xml(xml_file)
    pt = Template(filename='templates/template.html', input_encoding='utf-8', output_encoding='utf-8')
    st = Template(filename='templates/slide.html')
    slides = []
    for major in majors:
        for minor in major.minors:
            for speech, interjections in minor.interjected_speeches():
                slides.append(st.render(interjections=interjections, id=speech.id, minor_heading=minor.title, url=speech.url))
    with open(html_file, 'w') as f:
        print "- wrote ",len(slides),"slides to ",html_file
        f.write(pt.render(slides=slides, date=date, prev=prev))


def process_loc(loc, save_dir, xml_dir, force=False, keep_xml=False, index=False):
    ''' Processes an online directory of hansard xml files '''
    usock = urllib.urlopen(loc)
    parser = URLLister()
    parser.feed(usock.read())
    usock.close()
    parser.close()
    count = 1
    prev = '#'
    for url in parser.urls:
        if url.endswith('.xml'):
            print url, ",", count, " of ", len(parser.urls)
            html_file = url.split('.')[0]+'.html'
            dest_file = os.path.join(save_dir, html_file)
            xml_file = os.path.join(xml_dir, url)
            if not os.path.exists(xml_file):
                print ".. Downloading"
                urllib.urlretrieve (loc + url, xml_file)
                # For now, always index the new xml files
                try:
                    print ".. Indexing noun phrases"
                    process_speeches(xml_file, xml_file.split('/')[2].split('.')[0], xml_file.split('/')[1])
                except:
                    print 'Failed to index:',xml_file
            if index:
                print ".. Indexing noun phrases"
                process_speeches(xml_file, xml_file.split('/')[2].split('.')[0], xml_file.split('/')[1])
            if force or not os.path.exists(dest_file):
                print ".. Building HTML"
                xml_to_interjections(xml_file, dest_file, url.split('.')[0], prev)
                prev = html_file
            if not keep_xml:
                os.unlink(xml_file)
            count += 1

def process_speeches(xml_file, date, house):
    c = conn.cursor()
    year = date.split('-')[0]
    count = 0
    #from textblob import TextBlob
    from pattern.en import parsetree
    from pattern.search import search
    majors = process_xml(xml_file)
    for major in majors:
        for minor in major.minors:
            for event in minor.timeline:
                if type(event) is Speech:
                    for speaker, speech in event.get_script():
                        s = MLStripper()
                        s.feed(speech)
                        #blob = TextBlob(s.get_data())
                        #print blob.noun_phrases
                        pt = parsetree(s.get_data(), relations=True, lemmata=True)
                        noun_phrases = [match.constituents()[0].string.lower() for match in search('NP', pt) if match.constituents()[0].string.lower() not in ['i','you','it']]
                        #adjectives = [match.constituents()[0].string.lower() for match in search('JJ', pt) ]
                        for np in noun_phrases:
                            query = """insert into noun_phrases 
                                (phrase, speakername, speechid, headingid, headingtitle, date, year, house, url) 
                                values (?, ?, ?, ?, ?, ?, ?, ?, ?) """
                            values = (np, speaker, event.id, minor.id, minor.title, date, year, house, event.url)
                            try:
                                c.execute(query, values)
                            except:
                                print query
                                print                        
                        count += len(noun_phrases)
                        
            conn.commit()
    print count
    c.close()


###
# DB related
###
def init_db():
    c = conn.cursor()
    try:
        c.execute('''drop table noun_phrases''')
    except:
        pass
    c.execute('''create table noun_phrases
(phrase text, speakername text, speechid text, headingid text, headingtitle text, date text, year text, house text, url text)''')        
    conn.commit()
    c.close()


if __name__=="__main__":
    force = False # force rebuild the html
    keep = False # keep xml files around
    index = False #index the noun phrases?
    try:
      opts, args = getopt.getopt(sys.argv[1:],"hfkci",["force","keep","create","index"])
    except getopt.GetoptError:
      print 'app.py -f -k'
      sys.exit(2)
    for opt, arg in opts:
      if opt == '-h':
         print 'app.py -f (force rebuild of html) -k (keep xml files) -i(index noun phrases) -c (create database)'
         sys.exit()
      elif opt in ("-f", "--force"):
         force = True
      elif opt in ("-k", "--keep"):
         keep = True
      elif opt in ("-i", "--index"):
         index = True        
      elif opt in ("-c", "--create"):
         init_db()
         print "Initialized the database"
         sys.exit()
    # Now the program
    xml_senate_dest = os.path.join('xml','s')
    xml_representative_dest = os.path.join('xml','r')
    senate_dest = os.path.join('html','s')
    representative_dest = os.path.join('html','r')
    if not os.path.exists(xml_senate_dest):
        os.makedirs(xml_senate_dest)
    if not os.path.exists(xml_representative_dest):
        os.makedirs(xml_representative_dest)
    if not os.path.exists(senate_dest):
        os.makedirs(senate_dest)
    if not os.path.exists(representative_dest):
        os.makedirs(representative_dest)
    process_loc(senate_debates_loc, senate_dest, xml_senate_dest, force=force, keep_xml=keep, index=index)
    process_loc(representative_debates_loc, representative_dest, xml_representative_dest, force=force, keep_xml=keep, index=index)
    
    
    #get_noun_phrases_for_speaker('Ian Gordon Campbell')
    #get_speakers_for_noun_phrase('energy use')
    #get_noun_phrases_with('terror')
    #get_speakers_for_fragment('terror')
    #get_phrase_usage('Ian Gordon Campbell', 'energy use')
    #load_noun_phrases('energy use')
    #load_noun_phrases_for_speaker('energy use','Ian Gordon Campbell')
    #load_noun_phrases_by_fragment('terror')