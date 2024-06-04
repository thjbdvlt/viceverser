import hunspell
import informifier
import spacy.lookups
import spacy.tokens.token
import viceverser.default
import viceverser.feats
import viceverser.francais
import viceverser.utils.pos_rules


if not spacy.tokens.token.Token.has_extension("viceverser"):
    spacy.tokens.token.Token.set_extension("viceverser", default=None)


class Lemmatizer:
    """Lemmatise des documents en utilisant HunSpell."""

    def __init__(
        self,
        nlp,
        fp_dic=viceverser.default.FP_DIC,
        fp_aff=viceverser.default.FP_AFF,
        exc=None,
        pos_rules=None,
        lookup_feats=viceverser.default.LOOKUP,
    ):
        """Crée un objet pour lemmatiser une série de documents.

        Args:
            nlp:  le modèle de langue chargé par spacy
            fp_dic (str):  fichier .dic pour hunspell (lexique).
            fp_aff (str):  fichier .aff pour hunspell (règles de flexions).
            exc (dict):  des exceptions.

        Note:
            Les mots du lexique hunspell doivent avoir l'attribut `po:` (part-of-speech).

        pour initier le lemmatiser, j'instancie différents objets qui vont me servir pour la lemmatisation:
            - un objet `Lookups` dans lequel mettre des tables d'accessions rapides, pour éviter de répéter inutilement des opérations.
            - un objet `HunSpell` à partir d'un fichier .dic (qui définit un lexique de base) et .aff (qui définit des règles combinatoires de variations autour du lexique).

        si aucune fonction n'est passée pour `rule_lemmatize`:
            - un objet `Informitif`, issu d'un petit module que j'ai écrit pour ça et qui sert à trouver l'infinitif d'un verbe à partir de l'une de ses formes conjuguée, et de déterminer à quelle sous-groupe il appartient (parmi les verbes du premier groupe). l'idée est de pouvoir, en rencontrant un nouveau verbe, donner à hunspell un modèle pour construire toutes les formes possibles que ce verbe peut prendre.
        """

        if exc is None:
            exc = viceverser.francais.lemmes_exceptions.exc

        if pos_rules is None:
            pos_rules = viceverser.utils.pos_rules.default_list(nlp)

        # instanciation des objets utilisés par le lemmatizer
        self.lookups = spacy.lookups.Lookups()
        self.hobj = hunspell.HunSpell(fp_dic, fp_aff)
        self.nlp = nlp
        self.pos_priorities = pos_rules
        strings = nlp.vocab.strings
        self.strings = strings

        # ajoute une table pour chaque pos tag
        for i in self.pos_priorities.keys():
            self.lookups.add_table(i, {})

        # ajoute les exceptions dans les tables
        for pos in exc.keys():
            t = self.lookups.get_table(pos)
            for word, lemme in exc[pos].items():
                t.set(strings[word], {"stem": lemme, "morph": None})

    def find_lemma(self, word, norm, upos) -> str:
        """Trouve le lemme d'un mot.

        Args:
            word (str):  le mot.
            norm (int):  la hash value de la norme du mot.
            upos (str):  le part-of-speech du mot.

        Returns (str):  le lemme proposé.

        plusieurs méthodes sont essayées successivement:
            1. première solution, la plus simple: si le mot est dans la table, alors retourne le lemme correspondant. (idéalement, il faudrait faire qqch avec le part-of-speech ici, même pour la table. typiquement pour sommes/somme.)
            2. si le mot n'est pas déjà dans la table, le chercher dans le dictionnaire hunspell. si un stemme est trouvé, l'utiliser comme lemme et ajouter la relation mot-lemme dans la table (pour ne pas avoir à appeler plusieurs fois des fonctions de hunspell sur des mots identiques).
            3. s'il s'agit d'un mot composé (autrice-compositrice), je décompose le mot et lemmatise chaque composant, avant de les réaggréger pour construire le lemme du mot composé: "autrice-compositrice" -> "auteurice-compositeurice".
            4. en fonction du part-of-speech, j'essaie de reconstruire le lemme à partir d'une série de règles plus ou moins simples.
            5. si aucune méthode au-dessus n'a fonctionné, le lemme est identique à token.norm_
        (docstring pas à jour!)
        """

        l = self.lookups.get_table(upos)

        x = l.get(norm)
        if x is not None:
            return x

        x = self.search_lemma_hunspell(word=word, upos=upos)
        if x is not None:
            l.set(norm, x)
            return x

        x, morph = self.rule_lemmatize(word=word, upos=upos)
        if morph:
            morph = viceverser.feats.morph_to_feats(morph)
        y = {"stem": x, "morph": morph}
        l.set(norm, y)
        return y

    def find_lemma_composed(self, word, norm, upos):
        """Trouve le lemme d'un mot composé.

        Args:
            word (str):  le mot.
            norm (int):  la hash value de la norme du mot.
            upos (str):  le part-of-speech du mot.

        Returns (str): le lemme proposé.
        """

        l = self.lookups.get_table(upos)
        strings = self.strings

        x = l.get(norm)
        if x is not None:
            return x

        keyhaslemme = l.get(norm)
        if keyhaslemme is not None:
            return keyhaslemme

        subwords = [
            self.find_lemma(
                word=s,
                norm=strings[s],
                upos=("adp", upos),
            )
            for s in word.split("-")
            if s.strip() != ""
        ]
        lemme_ = "-".join([s["stem"] for s in subwords])
        composednorm = strings[lemme_]
        x = l.get(composednorm)
        if x is not None:
            l.set(norm, x)
            return x
        else:
            morph = [s["morph"] for s in subwords]
            y = {"stem": lemme_, "morph": morph}
            l.set(norm, y)
            l.set(composednorm, y)
            return y

    def search_lemma_hunspell(self, word, upos):
        """cherche un lemme correspondant au mot dans un lexique hunspell.

        Args:
            word (str):  le mot.
            upos (str):  le part-of-speech du mot.

        Returns (str, None):  le lemme proposé.

        si un lemme avec la même catégorie grammaticale (part-of-speech tag) est trouvé, alors il est retourné. sinon, cherche dans l'ordre des upos les plus proches du upos du mot. (si le mot correspond à une entrée, un lemme sera de toute façon retourné, si possible avec la même catégorie grammaticale.)

        exemples
        --------

            1. `word=rire, upos=noun`
                -> ("rire", "noun")

            2. `word=rire, upos=verb`
                -> ("rire", "verb")

            3. `word=rire, upos=aux`
                -> ("rire", "verb")

            4. `word=t8âùèildv, upos=aux`
                -> None
        """

        ho = self.hobj

        if ho.spell(word) is False:
            return None

        d = {}
        x = ho.analyze(word)

        for lex_entry in x:
            attrs = lex_entry.decode().split()
            po_tags = []
            stems = []
            is_ = []
            for a in attrs:
                prefix = a[:3]
                if prefix == "po:":
                    po_tags.append(a[3:])
                elif prefix == "st:":
                    stems.append(a[3:])
                elif prefix == "is:":
                    is_.append(a)
            if len(stems) == 0:
                continue
            stem = stems[0]
            for tag in po_tags:
                d[tag] = {
                    "stem": stem,
                    "morph": " ".join(is_),
                    "pos": po_tags,
                }

        tagsprio = self.pos_priorities[upos]
        for tag in tagsprio:
            if tag in d.keys():
                result = d[tag]
                result["morph"] = viceverser.feats.morph_to_feats(
                    result["morph"]
                )
                return d[tag]
        if len(d) == 0:
            return None
        result = list(d)[0]
        result["morph"] = viceverser.feats.morph_to_feats(
            result["morph"]
        )
        return result

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
        upos = token.pos_.lower()
        x = self.lookups.get_table(upos).get(norm)
        if x is not None:
            token.lemma_ = x["stem"]
            token._.viceverser = x["morph"]
            return
        elif "-" in token.norm_:
            fn = self.find_lemma_composed
        else:
            fn = self.find_lemma
        d = fn(word=word, norm=norm, upos=upos)
        return d

    def rule_lemmatize(self, word: str, upos: str) -> str:
        """Lemmatise un mot à l'aide de règles spécifiques à son POS.

        Args:
            word (str): le mot.
            upos (str): le part-of-speech du mot.
            hobj (Hunspell):  le lexique Hunspell.

        Returns (tuple[str, str]): le lemme proposé et une description morphologique.

        Règles relatives au part-of-speech:
            - verb: reconstitue l'infinitif d'un verbe.
            - noun+adj: enlève un éventuel "s" et "x" final.
            - dans les autres cas, retourne simplement le mot lui-même, sans modification.
        """

        if upos in ("verb", "aux") and word[-2:] != "er":
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
            d = self.get_lemma(token)
            token.lemma_ = d["stem"]
            token._.viceverser = d["morph"]
        return doc


@spacy.Language.factory(
    "viceverser_lemmatizer",
    default_config={"name": "viceverser_lemmatizer"},
)
def create_viceverser_lemmatizer(nlp, name):
    return Lemmatizer(nlp=nlp)
