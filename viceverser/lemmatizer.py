import hunspell
import informifier
import spacy.lookups
from spacy.tokens import Doc
from spacy.parts_of_speech import NAMES as POS_NAMES
import viceverser.francais.lemmes_exceptions
import viceverser.utils.pos_rules
from typing import Union, Callable


class Lemmatizer:
    def __init__(
        self,
        nlp,
        dic: str,
        aff: str,
        exc=None,
        pos_rules=None,
        pfx: str = "pfx",
    ):

        if exc is None:
            exc = viceverser.francais.lemmes_exceptions.exc

        if pos_rules is None:
            pos_rules = viceverser.utils.pos_rules.default_list(nlp)

        self.upos_lower = {i: POS_NAMES[i].lower() for i in POS_NAMES}

        self.lookups = spacy.lookups.Lookups()
        self.hobj = hunspell.HunSpell(dic, aff)
        self.nlp = nlp
        self.pos_priorities = pos_rules
        self.strings = nlp.vocab.strings
        self.pfx = pfx

        for i in self.pos_priorities.keys():
            self.lookups.add_table(i, {})

        for pos in exc.keys():
            t = self.lookups.get_table(pos)
            for word, lemme in exc[pos].items():
                t.set(self.strings[word], (lemme, [pos], None))

    def find_lemma(self, word, norm, upos) -> str:
        """Find the lemma of a word."""

        # get the table associated to the word's pos
        table = self.lookups.get_table(upos)

        # if the norm already is the table, returns the corresponding value
        if norm in table:
            return table[norm]

        # try to get word's lemma using hunspell
        lemma = self.search_lemma_hunspell(word=word, upos=upos)
        if lemma:
            table[norm] = lemma
            return lemma

        # fallback using rule lemmatization if hunspell failed
        lemma = self.rule_lemmatize(word=word, upos=upos)
        table[norm] = lemma
        return lemma

    def find_lemma_compound(self, word: str, norm: int, upos: str) -> str:
        """Find the lemma of a hyphen-based compound word."""

        # get the table (according to word's pos)
        table = self.lookups.get_table(upos)
        strings = self.strings

        # if the word already is in the table, returns corresponding value
        if norm in table:
            return table[norm]

        # split the compound word into subwords
        subwords = [s for s in word.split("-") if s != ""]

        # end function if empty
        if len(subwords) == 0:
            return ("-", None, None)

        # find lemma for each subword
        subwords = [
            self.find_lemma(
                word=s,
                norm=strings[s],
                upos=(self.pfx, upos),
            )
            for s in subwords
        ]

        # join sub-lemmas
        lemme_ = "-".join([s[0] for s in subwords])
        compoundnorm = strings[lemme_]

        # check if lemma is in the table and add it if it's not
        if compoundnorm in table:
            lemme = table[compoundnorm]
            table[norm] = lemme
            return lemme

        # pos = [s[1] for s in subwords][-1]
        # pos = subwords[-1][1] # whyyy
        # y = (lemme_, pos)
        y = (lemme_, upos)
        table.set(norm, y)
        table.set(compoundnorm, y)
        return y

    def search_lemma_hunspell(self, word, upos):
        """Search for a lemma using Hunspell."""
        ho = self.hobj

        # end function if unknown word
        if not ho.spell(word):
            return None

        # analyze with hunspell
        analysis = ho.analyze(word)
        d = {}

        for lex_entry in analysis:
            attrs = lex_entry.decode().split()  # TODO: do not decode
            po_tags = set()
            stem = None
            for a in attrs:
                if a.startswith('po:'):
                    po_tags.add(a[3:])
                elif a.startswith('st:'):
                    if not stem:
                        stem = a[3:]
            if stem:
                for tag in po_tags:
                    d[tag] = (stem, sorted(po_tags))

        # end function if empty dict
        if not d:
            return None

        # chose the stem that has the best position in pos_priorities
        tagsprio = self.pos_priorities[upos]
        for tag in tagsprio:
            if tag in d:
                return d[tag]

        return None

    def get_lemma(self, token):
        """Assigne un lemme à un token.

        Args:
            token (Token): le token.

        Returns (None)

        Note:
            l'attribut `token.lemma_` est modifié par cette méthode.
        """

        word = token.norm_
        norm = token.norm
        upos = self.upos_lower[token.pos]
        table = self.lookups.get_table(upos)

        if norm in table:
            return table[norm]
        elif "-" in word:
            fn = self.find_lemma_compound
        else:
            fn = self.find_lemma

        return fn(word=word, norm=norm, upos=upos)

    def rule_lemmatize(self, word: str, upos: str) -> str:
        if upos in ("verb", "aux") and not word.endswith("er"):
            lemma, like = informifier.informifier(word)
            self.hobj.add_with_affix(lemma, like)

        elif upos in ("noun", "adj"):
            if word[-1] in ("x", "s"):
                lemma = word[:-1]

            else:
                lemma = word

        else:
            lemma = word

        return lemma

    def __call__(self, doc: Doc) -> Doc:
        """Lemmatize a Doc."""

        for token in doc:
            token.lemma_ = self.get_lemma(token)

        return doc


@spacy.Language.factory(
    "viceverser_lemmatizer",
    default_config={"name": "viceverser_lemmatizer"},
)
def create_viceverser_lemmatizer(
    nlp,
    name,
    dic: Union[str, Callable],
    aff: Union[str, Callable],
):
    if callable(dic):
        dic = dic()
    if callable(aff):
        aff = aff()
    return Lemmatizer(nlp, dic, aff)
