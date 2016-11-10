# -*- coding: utf-8 -*-

import os, sys
import xml.etree.ElementTree as etree      
import urllib
from sgmllib import SGMLParser

from mako.template import Template

representative_debates_loc = 'http://data.openaustralia.org/scrapedxml/representatives_debates/'
senate_debates_loc = 'http://data.openaustralia.org/scrapedxml/senate_debates/'

class URLLister(SGMLParser):
    def reset(self):
        SGMLParser.reset(self)
        self.urls = []

    def start_a(self, attrs):
        href = [v for k, v in attrs if k=='href']
        if href:
            self.urls.extend(href)

class Major(object):
    def __init__(self, title):
        self.title = title
        self.minors = []

class Minor(object):
    def __init__(self, title):
        self.title = title
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
                #interjections.append((p['speakername'], trunc(p['text'], 200)))
                interjections.append((p['speakername'], t))
            elif p['talktype']=='speech' and len(self.parts)>1:
                t = to_text(p['node'], -1)
                #interjections.append((p['speakername'], trunc(p['text'], 200, reverse=True)))
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

def trunc(content, length=100, suffix='...', reverse=False):
    if len(content) <= length:
        return content
    else:
        if reverse:
            content = content[::-1]
        s = ' '.join(content[:length+1].split(' ')[0:-1]) + suffix
        if reverse:
            return s[::-1]
        else:
            return s

def truncate_paragraphs(text, num=1, reverse=False):
    text = '</p>'+text.strip()+'<p>'
    parts = text.split('</p><p>')[1:-1]
    ret = ''
    if reverse:
        print 'XX=',len(parts[-1*num:])
        for p in parts[-1*num:]:
            ret = "%s%s%s%s" % (ret, '<p>', p, '</p>')
        return ret
    else:
        for p in parts[:num]:
            ret = "%s%s%s%s" % (ret, '<p>', p,'</p>')
        return ret


def handle_major_heading(node):
    return node.text.strip()
    #print node.attrib
    pass

def handle_minor_heading(node):
    return node.text.strip()
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

        
"""
for major in majors:
    #print major.title
    for minor in major.minors:
        for speech in minor.interjected_speeches():
            print '# ',major.title
            print '# ',minor.title
            for interjection in speech:
                print "%s: %s" % interjection
"""


def process_xml(xml_file):
    ''' Processes an xml file returning majors '''
    tree = etree.parse(xml_file)
    root = tree.getroot()
    #print stats(root)
    majors = []
    for child in root:
        data = handle(child)
        if child.tag=='major-heading':
            majors.append(Major(data))
        elif child.tag=='minor-heading':
            majors[-1].minors.append(Minor(data))
        else:
            majors[-1].minors[-1].add_event(child.tag, data)
    return majors

def xml_to_interjections(xml_file, html_file, prev):
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
        f.write(pt.render(slides=slides, date=xml_file.split('.')[0], prev=prev))


def process_loc(loc, save_dir, force=False):
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
            if force or not os.path.exists(dest_file):
                urllib.urlretrieve (loc + url, url)
                xml_to_interjections(url, dest_file, prev)
                prev = html_file
                os.unlink(url)


if __name__=="__main__":
    senate_dest = os.path.join('html','s')
    representative_dest = os.path.join('html','r')
    if not os.path.exists(senate_dest):
        os.makedirs(senate_dest)
    if not os.path.exists(representative_dest):
        os.makedirs(representative_dest)
    process_loc(senate_debates_loc, senate_dest, force=True)
    process_loc(representative_debates_loc, representative_dest)


