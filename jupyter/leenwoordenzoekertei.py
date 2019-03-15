# leenwoordenzoeker.py (Leenwoordenzoeker v1.2)
#
# KNAW Humanities Cluster
# Meertens Instituut
#
# Joey Stofberg & Kaspar Beelen
#
# EN: Application for identifying loanwords in Dutch-language texts.
#
# The program presumes an input file in the XML-based FoliA annotation format.
# It provides both absolute and relative numbers of the loanwords and unique loanwords in the input text.
# It provides the number of loanwords and unique loanwords per language.
# Finally, it provides a list of all (unique) loanwords.
#
# NL: Applicatie om leenwoorden te identificeren in Nederlandstalige teksten.
#
# Gaat uit van een XML-bestand in een FoLiA-indeling als input.
# Geeft zowel absolute als relatieve aantallen van de leenwoorden en unieke leenwoorden in de invoertekst.
# Geeft per taal aan welke aantallen leenwoorden en unieke leenwoorden daaruit afkomstig zijn.
# Verschaft ten slotte een lijst van alle (unieke) leenwoorden.

import os
import re
import sys
import requests
from jinja2 import Template
from glob import glob

import pandas as pd
from collections import Counter
from lxml import etree

nsFolia = {'fo':'http://ilk.uvt.nl/folia',
	  'xlink':'http://www.w3.org/1999/xlink',
	  'xml':'http://www.w3.org/XML/1998/namespace'}

ns = {'tei':"http://www.tei-c.org/ns/1.0",'xlink':'http://www.w3.org/1999/xlink',
          'xml':'http://www.w3.org/XML/1998/namespace'}

# Map POS tags in loanword database to POS tags used in FoLiA format.
pos_mapping_frog = {'zelfstandig naamwoord':'n', 'bijvoeglijk naamwoord':'adj', 'werkwoord':'ww',
                     'telwoord':'tw', 'voornaamwoord':'vnw', 'lidwoord':'lid', 'voorzetsel':'vz',
                     'voegwoord':'vg', 'bijwoord':'bw', 'tussenwerpsel':'tsw'}
  
pos_mapping = {'zelfstandig naamwoord':'NOU-C', 'bijvoeglijk naamwoord':'AA', 'werkwoord':'VRB',
                     'telwoord':'NUM', 'voornaamwoord':'PD', 'lidwoord':'PD', 'voorzetsel':'ADP',
                     'voegwoord':'CON', 'bijwoord':'ADV', 'tussenwerpsel':'INT'}


server = "http://openconvert.clarin.inl.nl/openconvert/file"


def tagString(inputText):
  response = requests.post(server, data = {'tagger':'chn-tagger', 'output': 'raw', 'format':'text', 'to':'tei',  'method':'asdata'},files=dict(input=inputText), stream=False)
  return response.content


def slurpURL(url):
  response = requests.get(url)
  return response.content 

class LoanWordStats:
  def __init__(self,dataFile):
      table = pd.read_csv(dataFile,sep='\t')
      mapping = list(zip(table.trefwoord.str.lower(), table.POS, table.geleend_uit))
      self.word2language = dict(zip(table.trefwoord.str.lower(), table.geleend_uit))
      self.word2pos = dict(zip(table.trefwoord.str.lower(), table.POS))
  
      # Find all multiple-word compounds in database.
      multiple_word_compounds = [w for w in set(table.trefwoord) if len(w.split())>1 and w.replace(' ', '').isalpha()]
  
      # Find all words containing a hyphen in database.
      hyphenated_words = []
      containing_hyphen = [w for w in set(table.trefwoord) if '-' in w]
  
      # Only include words with a hyphen in the middle, and delete information separator characters from words.
      for word in containing_hyphen:
          if '\x1e' in word:
              hyphenated_words.append(word.replace('\x1e', ''))
          elif not word.startswith('-') or word.endswith('-'):
              hyphenated_words.append(word)
  
      compounds = (sorted(multiple_word_compounds + hyphenated_words))
      compounds = [r'\b{}\b'.format(w.lower()) for w in compounds if w]
      self.compound_pattern = re.compile(r'(?:(%s))'%r'|'.join(compounds))
  
  
      # Make pairs of words in database and their POS tag for easy comparison.
      pairs = ['_'.join([w, pos_mapping.get(p, 'NaN')]) for w, p, t in mapping if w.isalpha()]
      word_pairs = [r'\b{}\b'.format(w.lower()) for w in pairs]
      self.pairs_pattern = re.compile(r'(?:%s)'%r'|'.join(word_pairs))
  
  def findFromFile(self,fileName):
    with open(fileName) as x: fileContents = x.read()
    self.find(fileContents)
 
  def findFromURL(self,url):
      content = slurpURL(url)
 
      content = re.sub('<.*?>', '', content.decode("utf-8"))
      
      self.findFromString(content)

  def find(self,arg):
      if (os.path.isfile(arg)):
          self.findFromFile(arg)
      else:
        if (arg.startswith('http')):
          self.findFromURL(arg)
        else:
          self.findFromString(arg)

  def findFromString(self,fileContents):
      # Ensure proper usage.
  
      # Map all relevant data in loanword database.
 
      taggedXML = tagString(fileContents)

      tree=etree.fromstring(taggedXML)

      # Open text input file.
      
      #path_to_xml = sys.argv[1]
      #directory, filename = os.path.split(path_to_xml)
      #with open(path_to_xml, 'rt') as input_xml:
      #    tree = etree.parse(input_xml)
  
  
      # Also make pairs of words in text and their POS tag for easy comparison.
      rows = []
  
      #words = tree.xpath('.//fo:w', namespaces=ns)
      #lem_pos = ' '.join(['_'.join((w.find('fo:lemma[@class]',namespaces=ns).get('class','None'),
      #                    w.find('fo:pos[@head]',namespaces=ns).get('head','None'))) for w in words])
  
      words = tree.xpath('.//tei:w', namespaces=ns)
      lem_pos = ' '.join(['_'.join((w.attrib.get('lemma','None'),
                          re.sub('\(.*', '', w.attrib.get('type','None')))) for w in words])

      # Make list of words with POS tags and list of words without POS tags.
      to_compare = []
      to_compare_2 = []
      pos = set()
      words_in_input = lem_pos.split(' ')
      for word in words_in_input:
          # Treat all words with the POS tag 'SPEC' as nouns. 
          if '_SPEC' in word:
              word = word.replace('_SPEC', '_N')
          to_compare.append(word.lower())
          to_compare_2.append(word.lower().split('_')[0])
          pos.add(word.split('_')[-1])
  
      # Find all loanwords in the text.
      loanwords_in_text = self.pairs_pattern.findall(' '.join(to_compare))
  
      # Find all borrowed compounds (both multiple-word and hyphenated).
      borrowed_compounds_in_text = [w for w in self.compound_pattern.findall(' '.join(to_compare_2))] # was w,i
  
      # Add all single words without POS tag to list of hits.
      hits = []
      for loanword in loanwords_in_text:
          hits.append(loanword.split('_')[0])
  
      # Add all compounds to the list of hits.
      hits.extend(borrowed_compounds_in_text)
 

      # now prepare and print report

      self.number_of_words = len(words_in_input)
      self.number_of_unique_words = len(set(words_in_input))
      self.number_of_loanwords = len(loanwords_in_text)
      self.number_of_unique_loanwords = len(set(loanwords_in_text))
 
      self.percentage_of_words = '{:.1%}'.format(self.number_of_loanwords / (self.number_of_words + 0.0))
      self.percentage_of_unique_words = '{:.1%}'.format(self.number_of_unique_loanwords / (self.number_of_unique_words + 0.0))
  
  
      # Find all words that correspond with words in the loanword database (for non-compounds, also having corresponding POS tags).
      results = Counter([self.word2language.get(h, 'NaN') for h in hits]).most_common()
  
      # Only find all unique loanwords.
      results_unique = Counter([self.word2language.get(h, 'NaN') for h in set(hits)]).most_common()
  

      # Print all found languages with their total number of hits and number of unique hits.
      self.language_stats = { }
      for language, language_hits in results:
          for language_unique, language_hits_unique in results_unique:
              if language_unique == language:
                  hits_unique = language_hits_unique
          self.language_stats[language] = (language_hits, hits_unique)
  
      # Print all unique words with their number of occurrences.
      self.allLoanWords = []
      for hit in sorted(set(hits)):
          occurrences = hits.count(hit)
          language = self.word2language.get(hit)
          pos = self.word2pos.get(hit)
          self.allLoanWords.append( (hit,occurrences, language, pos) )
          # print('{:30} {:30} {:30} {}'.format(hit, pos, language, occurrences))
 
  def printReport(self):
      print('Totaal aantal woorden:', self.number_of_words)
      print('Totaal aantal unieke woorden:', self.number_of_unique_words)
      print('Totaal aantal leenwoorden:', self.number_of_loanwords)
      print('Totaal aantal unieke leenwoorden:', self.number_of_unique_loanwords)
      print('\n')
      print('Leenwoorden als percentage van woorden:', self.percentage_of_words)
      print('Leenwoorden als percentage van unieke woorden:', self.percentage_of_unique_words)
      print('\n')
     
      for language in sorted(self.language_stats):      
          (language_hits, hits_unique) = self.language_stats[language]
          print(language)
          print('------------------------')
          print('Woorden:', language_hits)
          print('Unieke woorden:', hits_unique)
          print('\n')

      print('Alle unieke leenwoorden:')
      print('------------------------')

      for (hit,occurrences,language,pos) in sorted(self.allLoanWords):
         print('{:30} {:30} {:30} {}'.format(hit, pos, language, occurrences))
  
  def reportHTML(self):
      t = Template("""
      <div>
        <h3>Overzicht</h3>
        <table>
        <tr><td>Totaal aantal woorden<td> {{ number_of_words }} </tr>
        <tr><td>Totaal aantal unieke woorden<td> {{ number_of_unique_words }} </tr>
        <tr><td>Totaal aantal leenwoorden<td> {{ number_of_loanwords }} ({{ percentage_of_words }}) </tr>
        <tr><td>Totaal aantal unieke leenwoorden<td> {{ number_of_unique_loanwords }}  ({{ percentage_of_unique_words }}) </tr>
        </table>
        <table>
        <h3>Per taal<h3>
         <tr><th>Taal</th><th>Woorden</th><th>Unieke woorden</th></tr>
        {%for language in language_stats.keys()   %}
              <tr>
                 <td>{{ language }}
                 <td> {{ language_stats[language][0] }}
                 <td> {{ language_stats[language][1] }}
              </tr>
        {% endfor %}
        </table>
        <h3>Alle unieke leenwoorden</h3>
         <table>
         <tr><th>Woord</th><th>Frequentie</th><th>Taal</th><th>Woordsoort</th></tr>
        {%for loanword in allLoanWords %}
              <tr>
                 <td>{{ loanword[0] }}
                 <td> {{ loanword[1] }}
                 <td> {{ loanword[2] }}
                 <td> {{ loanword[3] }}
              </tr>
        {% endfor %}
        </table>
      </div>
      """)   
      s = t.render(number_of_words=self.number_of_words,
                    number_of_unique_words=self.number_of_unique_words,
                    number_of_loanwords=self.number_of_loanwords,
                    number_of_unique_loanwords=self.number_of_unique_loanwords,
                    language_stats = self.language_stats,
                    allLoanWords = sorted(self.allLoanWords),
                    percentage_of_words = self.percentage_of_words,
                    percentage_of_unique_words = self.percentage_of_unique_words)
      return s
     
def main():
  if len(sys.argv) != 2:
    print("Probleem met input! Gebruik als: python leenwoordenapplicatie.py filename")
    exit(1)
  lwFinder = LoanWordStats('leenwoord_data.tsv')
  lwFinder.find(sys.argv[1])
  lwFinder.printReport()
  print(lwFinder.reportHTML())
 
if __name__ == "__main__":
    main()
