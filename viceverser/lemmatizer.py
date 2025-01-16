import hunspell
import informifier
import spacy.lookups
import spacy.tokens.token
from spacy.parts_of_speech import NAMES as POS_NAMES
import viceverser.default
import viceverser.feats
import viceverser.francais.lemmes_exceptions
import viceverser.utils.pos_rules
from viceverser.default import FP_AFF, FP_DIC


if not spacy.tokens.token.Token.has_extension("vv_pos"):
    spacy.tokens.token.Token.set_extension("vv_pos", default=None)

if not spacy.tokens.token.Token.has_extension("vv_morph"):
    spacy.tokens.token.Token.set_extension("vv_morph", default=None)

UPOS_LOWER = {i: POS_NAMES[i].lower() for i in POS_NAMES}


class Lemmatizer:
    def __init__(
        self,
        nlp,
        fp_dic=FP_DIC,
        fp_aff=FP_AFF,
        exc=None,
        pos_rules=None,
    ):
        if exc is None:
            exc = viceverser.francais.lemmes_exceptions.exc

        if pos_rules is None:
            pos_rules = viceverser.utils.pos_rules.default_list(nlp)

        self.lookups = spacy.lookups.Lookups()
        self.hobj = hunspell.HunSpell(fp_dic, fp_aff)
        self.nlp = nlp
        self.pos_priorities = pos_rules
        self.strings = nlp.vocab.strings

        for i in self.pos_priorities.keys():
            self.lookups.add_table(i, {})

        for pos in exc.keys():
            t = self.lookups.get_table(pos)
            for word, lemme in exc[pos].items():
                t.set(self.strings[word], (lemme, [pos], None))

    def find_lemma(self, word, norm, upos) -> str:
        l = self.lookups.get_table(upos)

        if norm in l:
            return l[norm]

        x = self.search_lemma_hunspell(word=word, upos=upos)
        if x:
            l[norm] = x
            return x

        x, morph = self.rule_lemmatize(word=word, upos=upos)

        y = (x, None, morph)
        l[norm] = y
        return y

    def find_lemma_composed(self, word: str, norm: int, upos: str):
        l = self.lookups.get_table(upos)
        strings = self.strings

        if norm in l:
            return l[norm]

        subwords = [s for s in word.split("-") if s != ""]

        if len(subwords) == 0:
            return ("-", None, None)

        subwords = [
            self.find_lemma(
                word=s,
                norm=strings[s],
                # pfx? instead of adp?
                upos=("adp", upos),
            )
            for s in subwords
        ]

        lemme_ = "-".join([s[0] for s in subwords])
        composednorm = strings[lemme_]

        if composednorm in l:
            lemme = l[composednorm]
            l[norm] = lemme
            return lemme

        else:
            morph = [s[2] for s in subwords][-1]
            pos = [s[1] for s in subwords][-1]
            y = (lemme_, pos, morph)
            l.set(norm, y)
            l.set(composednorm, y)
            return y

    def search_lemma_hunspell(self, word, upos):
        ho = self.hobj

        if ho.spell(word) is False:
            return None

        d = {}
        x = ho.analyze(word)

        for lex_entry in x:
            attrs = lex_entry.decode().split()
            po_tags = set()
            stems = []
            is_ = []
            for a in attrs:
                prefix = a[:3]
                if prefix == "po:":
                    po_tags.add(a[3:])
                elif prefix == "st:":
                    stems.append(a[3:])
                elif prefix == "is:":
                    is_.append(a)
            if len(stems) == 0:
                continue
            stem = stems[0]
            for tag in po_tags:
                d[tag] = (stem, sorted(po_tags), " ".join(is_))

        tagsprio = self.pos_priorities[upos]
        for tag in tagsprio:
            if tag in d.keys():
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
        upos = UPOS_LOWER[token.pos]
        table = self.lookups.get_table(upos)

        if norm in table:
            return table[norm]
        elif "-" in word:
            fn = self.find_lemma_composed
        else:
            fn = self.find_lemma

        return fn(word=word, norm=norm, upos=upos)

    def rule_lemmatize(self, word: str, upos: str) -> str:
        if upos in ("verb", "aux") and not word.endswith("er"):
            lemma, like = informifier.informifier(word)
            self.hobj.add_with_affix(lemma, like)
            morph = self.hobj.analyze(word)
            if len(morph) > 0:
                morph = morph[0].decode()
            else:
                morph = None

        elif upos in ("noun", "adj"):
            if word[-1] in ("x", "s"):
                morph = "is:pl"
                lemma = word[:-1]

            else:
                morph = "is:sg"
                lemma = word

        else:
            lemma = word
            morph = None

        return lemma, morph

    def __call__(self, doc):
        """Attribue un lemme à chaque token d'un doc.

        Args:
            doc (Doc):  le doc.

        Returns (Doc):  le doc.
        """

        for token in doc:
            lemme, pos, morph = self.get_lemma(token)
            token.lemma_ = lemme
            token._.vv_pos = pos
            token._.vv_morph = morph
        return doc


@spacy.Language.factory(
    "viceverser_lemmatizer",
    default_config={"name": "viceverser_lemmatizer"},
)
def create_viceverser_lemmatizer(nlp, name):
    return Lemmatizer(nlp=nlp)
