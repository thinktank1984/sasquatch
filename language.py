
from solverUtilities import *
from z3 import *
import math
import random

from corpus import verbs, latexTable, sample_corpus

TENSES = 6
LS = 0 # latent strings
LF = 0 # latent flags

# map between tipa and z3 character code
ipa2char = { 'p': 'Pp', 'b': 'Pb', 'm': 'Pm', 'f': 'Pf', 'v': 'Pv', 'T': 'PT', 'D': 'PD', 'R': 'PR', 't': 'Pt', 'd': 'Pd',
             'n': 'Pn', 'r': 'Pr', 's': 'Ps', 'z': 'Pz', 'l': 'Pl', 'S': 'PS', 'Z': 'PZ', 'j': 'Pj', 'k': 'Pk', 'w': 'Pw',
             'g': 'Pg', 'N': 'PN', 'P': 'PP', 'h': 'Ph', 'i': 'Pi', 'I': 'PI', 'e': 'Pe', 'E': 'PE', '\\ae': 'PQ', '@': 'P@',
             '2': 'P2', 'A': 'PA', 'a': 'Pa', '5': 'P5', '0': 'P0', 'o': 'Po', 'U': 'PU', 'u': 'Pu'
             }
char2ipa = {}
for k in ipa2char: char2ipa[ipa2char[k]] = k

Phoneme, phonemes = EnumSort('Phoneme', tuple(char2ipa.keys()))
z3char = {}
for p in phonemes:
    z3char[str(p)] = p

Place, places = EnumSort('Place', ('NoPlace','LABIAL','CORONAL','DORSAL'))
place_table = { 'LABIAL': 'p b f v m w',
                'CORONAL': 'r t d T D s z S Z n l',
                'DORSAL': 'k g h j N' }
Voicing, voices = EnumSort('Voice', ('VOICED','UNVOICED'))
voice_table = { 'VOICED': 'b m v D R d n z Z j l g N i I e E @ 2 A a 5 0 o U u \\ae',
                'UNVOICED': 'p f T t r s S w P h k'}
Manner, manners = EnumSort('Manner', ('NoManner','STOP','FRICATIVE','NASAL','LIQUID','GLIDE'))
manner_table = { 'STOP': 'p b t d k g',
                 'FRICATIVE': 'f v T D s z Z S h',
                 'NASAL': 'm n N',
                 'LIQUID': 'l r',
                 'GLIDE': 'j w'}
Sibilant, sibilance = EnumSort('Sibilant', ('NoSibilant','SIBILANT'))
sibilant_table = { 'SIBILANT': 's z S Z'}

# maximum string length
maximum_length = 9


def morpheme():
    l = integer()
    constrain(l < maximum_length+1)
    constrain(l > -1)
    ps = [ Const(new_symbol(), Phoneme) for j in range(maximum_length) ]
    return tuple([l]+ps)


def extract_string(m, v):
    rv = ""
    l = m[v[0]].as_long()
    ps = list(v)[1:]
    for j in range(l):
        c = str(m[ps[j]])
        cp = char2ipa[c]
        if cp[0] == '\\':
            rv += cp + " "
        else:
            rv += cp
    return "\\textipa{%s}" % rv

def constrain_phonemes(ps,correct):
    l = ps[0]
    ps = list(ps)[1:]
    correct = correct.split(' ')
    constrain(l == len(correct))
    
    correct = [ z3char[ipa2char[c]] for c in correct ]
    assert(len(correct) < maximum_length+1)
    for j in range(len(correct)):
        constrain(ps[j] == correct[j])

def concatenate(p,q):
    r = morpheme()
    lr = r[0]
    r = list(r)[1:]
    lp = p[0]
    p = list(p)[1:]
    lq = q[0]
    q = list(q)[1:]
    
    constrain(lr == lp+lq)
    constrain(lr < maximum_length+1)
    
    for j in range(maximum_length):
        constrain(Implies(lp > j,
                          r[j] == p[j]))
        constrain(Implies(lp == j,
                          And(*[ Implies(lq > i, r[i+j] == q[i])
                                 for i in range(maximum_length-j) ])))
    return tuple([lr]+r)
                          
                          


def last_one(ps):
    constrain(ps[0] > 0)
    ending = Const(new_symbol(), Phoneme)
    for j in range(1,maximum_length+1):
        constrain(Implies(ps[0] == j,ending == ps[j]))
    return ending


def extract_feature(p, sort, realizations, table):
    return_value = Const(new_symbol(), sort)
    renderings = [str(v) for v in realizations ]
    table = [ (realizations[renderings.index(name)],
               [ z3char[ipa2char[m]] for m in matches.split(' ') ])
              for name, matches in table.iteritems() ]
    if renderings[0] == 'No'+str(sort): # this will be the default case
        expression = realizations[0]
    else:
        expression = table[0][0] # pick a default arbitrarily
        table = table[1:]
    for answer, possibilities in table:
        expression = If(Or(*[ p == possibility for possibility in possibilities ]),
                        answer,
                        expression)
    constrain(return_value == expression)
    return return_value

def voice(p):
    return extract_feature(p, Voicing, voices, voice_table)
def manner(p):
    return extract_feature(p, Manner, manners, manner_table)
def place(p):
    return extract_feature(p, Place, places, place_table)
def sibilant(p):
    return extract_feature(p, Sibilant, sibilance, sibilant_table)


def primitive_string():
    thing = morpheme()
    def evaluate_string(i):
        return thing
    def print_string(m):
        return extract_string(m,thing)
    m = real()
    constrain(m == logarithm(44)*thing[0])
    return evaluate_string, m, print_string

enum_rule('VOICE', list(voices))
enum_rule('PLACE', list(places)[1:])
enum_rule('MANNER', list(manners)[1:])
enum_rule('SIBILANT', list(sibilance)[1:])

rule('VOICE-GUARD', [],
     lambda m: '?',
     lambda i: True)
rule('VOICE-GUARD', ['VOICE'],
     lambda m, g: g,
     lambda i, f: f == voice(i['last']))

rule('MANNER-GUARD', [],
     lambda m: '?',
     lambda i: True)
rule('MANNER-GUARD', ['MANNER'],
     lambda m, g: g,
     lambda i, f: f == manner(i['last']))

rule('PLACE-GUARD', [],
     lambda m: '?',
     lambda i: True)
rule('PLACE-GUARD', ['PLACE'],
     lambda m, g: g,
     lambda i, f: f == place(i['last']))

rule('SIBILANT-GUARD', [],
     lambda m: '?',
     lambda i: True)
rule('SIBILANT-GUARD', ['SIBILANT'],
     lambda m, g: g,
     lambda i, f: f == sibilant(i['last']))

rule('GUARD', ['VOICE-GUARD','MANNER-GUARD','PLACE-GUARD','SIBILANT-GUARD'],
     lambda m, v, ma, g, s: ("[ %s %s %s %s ]" % (v,g,ma,s)).replace(' ?',''),
     lambda i, f, ma, g, s: And(f,ma,g,s))


rule('STEM', [],
     lambda m: 'lemma',
     lambda i: i['lemma'])
indexed_rule('STEM', 'stem', LS,
             lambda i: i['stems'])
indexed_rule('FLAG', 'flag', LF,
             lambda i: i['flags'])

if LF > 0:
    rule('GUARD',['FLAG'],
         lambda m,v: v,
         lambda i,v: v)
rule('RETURN',['STEM','STRING'],
     lambda m, stem, suffix: stem if suffix == '\\textipa{}' else "(append %s %s)" % (stem,suffix),
     lambda i, p, q: concatenate(p,q))
rule('CONDITIONAL',['GUARD','RETURN','CONDITIONAL'],
     lambda m, p,q,r: "(if %s %s %s)" % (p,q,r),
     lambda i, p,q,r: conditional(p,q,r))
rule('CONDITIONAL',['RETURN'],
     lambda m, r: r,
     lambda i, r: r)
primitive_rule('STRING',
               primitive_string)

print sample_corpus(10,20,True)
os.exit()
observations = minimal_pairs
N = len(observations)
#latexTable(observations)

maximum_length = max([len(w.split(' ')) for ws in observations for w in ws ])

# for each tense, a different rule
programs = [ generator(3,'CONDITIONAL') for j in range(TENSES) ]

inputs = [ {'stems': [morpheme() for i in range(LS)],
            'flags': [boolean() for i in range(LF) ],
            'lemma': morpheme() }
           for j in range(N) ]
for j in range(N):
    inputs[j]['last'] = last_one(inputs[j]['lemma'])


for t in range(TENSES):
    for n in range(N):
        o = programs[t][0](inputs[n])
        constrain_phonemes(o, observations[n][t])

def printer(m):
    
    model = ""
    for t in range(TENSES):
        model += "Tense %i: %s\n" % (t,programs[t][2](m))
    model += "\n"
    for j in range(N):
        model += "lemma = %s\n" % extract_string(m,inputs[j]['lemma'])
        model += "\t".join(["stem[%i] = %s" % (t,extract_string(m,inputs[j]['stems'][t])) 
                            for t in range(LS) ])
        model += "\n"
        model += "\t".join(["flag[%i] = %s" % (f,extract_bool(m,inputs[j]['flags'][f]))
                            for f in range(LF) ])
        model += "\n"
    return model


flat_stems = [ v for sl in inputs for v in sl['stems'] ] + [ v['lemma'] for v in inputs ]
total = summation([N*TENSES*LF] + [p[1] for p in programs ] + [logarithm(44)*s[0] for s in flat_stems ])


compressionLoop(printer,total)

