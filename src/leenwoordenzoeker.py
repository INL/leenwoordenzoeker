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
from glob import glob

import pandas as pd
from collections import Counter
from lxml import etree

ns = {'fo':'http://ilk.uvt.nl/folia',
	  'xlink':'http://www.w3.org/1999/xlink',
	  'xml':'http://www.w3.org/XML/1998/namespace'}

def main():
    # Ensure proper usage.
    if len(sys.argv) != 2:
        print("Probleem met input! Gebruik als: python leenwoordenapplicatie.py filename")
        exit(1)

    # Map all relevant data in loanword database.
    table = pd.read_csv('Leenwoordenzoeker_(Leenwrdb-CW-EWB)_laatste_versie.tsv',sep='\t')
    mapping = list(zip(table.trefwoord.str.lower(), table.POS, table.geleend_uit))
    mapping2 = dict(zip(table.trefwoord.str.lower(), table.geleend_uit))
    mapping3 = dict(zip(table.trefwoord.str.lower(), table.POS))

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
    compound_pattern = re.compile(r'(?:(%s))'%r'|'.join(compounds))

    # Map POS tags in loanword database to POS tags used in FoLiA format.
    pos_mapping = {'zelfstandig naamwoord':'n', 'bijvoeglijk naamwoord':'adj', 'werkwoord':'ww',
                   'telwoord':'tw', 'voornaamwoord':'vnw', 'lidwoord':'lid', 'voorzetsel':'vz',
                   'voegwoord':'vg', 'bijwoord':'bw', 'tussenwerpsel':'tsw'}

    # Make pairs of words in database and their POS tag for easy comparison.
    pairs = ['_'.join([w, pos_mapping.get(p, 'NaN')]) for w, p, t in mapping if w.isalpha()]
    word_pairs = [r'\b{}\b'.format(w.lower()) for w in pairs]
    pairs_pattern = re.compile(r'(?:%s)'%r'|'.join(word_pairs))

    # Open text input file.
    path_to_xml = sys.argv[1]
    directory, filename = os.path.split(path_to_xml)
    with open(path_to_xml, 'rt') as input_xml:
        tree = etree.parse(input_xml)

    # Also make pairs of words in text and their POS tag for easy comparison.
    rows = []
    words = tree.xpath('.//fo:w', namespaces=ns)
    lem_pos = ' '.join(['_'.join((w.find('fo:lemma[@class]',namespaces=ns).get('class','None'),
                        w.find('fo:pos[@head]',namespaces=ns).get('head','None'))) for w in words])

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
    loanwords_in_text = pairs_pattern.findall(' '.join(to_compare))

    # Find all borrowed compounds (both multiple-word and hyphenated).
    borrowed_compounds_in_text = [w for w,i in compound_pattern.findall(' '.join(to_compare_2))]

    # Add all single words without POS tag to list of hits.
    hits = []
    for loanword in loanwords_in_text:
        hits.append(loanword.split('_')[0])

    # Add all compounds to the list of hits.
    hits.extend(borrowed_compounds_in_text)

    number_of_words = len(words_in_input)
    number_of_unique_words = len(set(words_in_input))
    number_of_loanwords = len(loanwords_in_text)
    number_of_unique_loanwords = len(set(loanwords_in_text))

    percentage_of_words = '{:.1%}'.format(number_of_loanwords / number_of_words)
    percentage_of_unique_words = '{:.1%}'.format(number_of_unique_loanwords / number_of_unique_words)

    print('Totaal aantal woorden:', number_of_words)
    print('Totaal aantal unieke woorden:', number_of_unique_words)
    print('Totaal aantal leenwoorden:', number_of_loanwords)
    print('Totaal aantal unieke leenwoorden:', number_of_unique_loanwords)
    print('\n')
    print('Leenwoorden als percentage van woorden:', percentage_of_words)
    print('Leenwoorden als percentage van unieke woorden:', percentage_of_unique_words)
    print('\n')

    # Find all words that correspond with words in the loanword database (for non-compounds, also having corresponding POS tags).
    results = Counter([mapping2.get(h, 'NaN') for h in hits]).most_common()

    # Only find all unique loanwords.
    results_unique = Counter([mapping2.get(h, 'NaN') for h in set(hits)]).most_common()

    # Print all found languages with their total number of hits and number of unique hits.
    for language, language_hits in results:
        for language_unique, language_hits_unique in results_unique:
            if language_unique == language:
                hits_unique = language_hits_unique
        print(language)
        print('------------------------')
        print('Woorden:', language_hits)
        print('Unieke woorden:', hits_unique)
        print('\n')

    # Print all unique words with their number of occurrences.
    print('Alle unieke leenwoorden:')
    print('------------------------')
    for hit in sorted(set(hits)):
        occurrences = hits.count(hit)
        language = mapping2.get(hit)
        pos = mapping3.get(hit)
        print('{:30} {:30} {:30} {}'.format(hit, pos, language, occurrences))

if __name__ == "__main__":
    main()