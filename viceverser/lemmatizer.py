"""lemmatisation du français avec hunspell pour spacy

a) s'il s'agit d'un mot simple, utiliser la fonction `stem` de hunspell pour trouver le lemme (arrivions -> arriver). si possible, trouver un lemme qui a la même catégorie grammaticale (ex. conseillons -> conseiller (verbe)), mais parfois le pos-tagging fait des erreurs, et alors il faudra trouver un lemme d'une autre catégorie grammaticale.
b) s'il s'agit d'un mot composé (avec un ou plusieurs trait(s) d'union(s)), découper le mots en ses différents composant et analyser comme en a) chacun de ces composants, puis les aggréger. par exemple: "auteur-compositeur" -> ["auteurice", "compositeurice"] -> "auteurice-compositeurice".
"""

from hunspell import HunSpell
from spacy.lookups import Lookups
from typing import Union, Callable
from spacy.tokens.doc import Doc
from spacy.tokens.token import Token


class Lemmatizer:
    """lemmatise des documents en utilisant hunspell."""

    def __init__(
        self,
        nlp,
        fp_dic: str,
        fp_aff: str,
        exc: dict[dict[str:str]] = None,
        pos_rules: dict[str:list] = None,
        rule_lemmatize: Callable = None,
    ):
        """crée un objet pour lemmatiser une série de documents.

        nlp:  la pipeline spacy avec le modèle, vocab, etc.
        fp_dic:  fichier .dic pour hunspell (lexique).
        fp_aff:  fichier .aff pour hunspell (règles de flexions).

        les mots du lexique hunspell doivent avoir l'attribut `po:` (part-of-speech).

        pour initier le lemmatiser, j'instancie différents objets qui vont me servir pour la lemmatisation:
            - un objet `Lookups` dans lequel mettre des tables d'accessions rapides, pour éviter de répéter inutilement des opérations.
            - un objet `HunSpell` à partir d'un fichier .dic (qui définit un lexique de base) et .aff (qui définit des règles combinatoires de variations autour du lexique).

        si aucune fonction n'est passée pour `rule_lemmatize`:
            - un objet `Informitif`, issu d'un petit module que j'ai écrit pour ça et qui sert à trouver l'infinitif d'un verbe à partir de l'une de ses formes conjuguée, et de déterminer à quelle sous-groupe il appartient (parmi les verbes du premier groupe). l'idée est de pouvoir, en rencontrant un nouveau verbe, donner à hunspell un modèle pour construire toutes les formes possibles que ce verbe peut prendre.
        """

        # valeurs par défaut des arguments
        if exc is None:
            from viceverser.francais.lemmes_exceptions import exc

            exc = exc
        if pos_rules is None:
            from viceverser.utils.pos_rules import default_list

            pos_rules = default_list(nlp)
        if rule_lemmatize is None:
            from viceverser.francais.rule_lemmatize import (
                RuleLemmatizer,
            )

            rule_lemmatize = RuleLemmatizer()

        # ajoute l'extension si elle n'existe pas
        if not Token.has_extension("viceverser"):
            Token.set_extension("viceverser", default=None)

        # instanciation des objets utilisés par le lemmatizer
        self.lookups = Lookups()
        self.hobj = HunSpell(fp_dic, fp_aff)
        self.nlp = nlp
        self.pos_priorities = pos_rules
        self.rule_lemmatize = rule_lemmatize
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
        """trouve le lemme d'un mot.

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

        x = self.rule_lemmatize(word=word, upos=upos)
        y = {"stem": x, "morph": None}
        l.set(norm, y)
        return y

    def find_lemma_composed(self, word, norm, upos):
        """trouve le lemme d'un mot composé."""

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

    def search_lemma_hunspell(
        self, word: str, upos: str
    ) -> Union[tuple[str, str], None]:
        """cherche un lemme correspondant au mot dans un lexique hunspell.

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
            for a in attrs:
                if a[:3] == "po:":
                    po_tags.append(a[3:])
                elif a[:3] == "st:":
                    stems.append(a[3:])
            if len(stems) == 0:
                return None
            stem = stems[0]
            for t in po_tags:
                d[t] = {"stem": stem, "morph": attrs}
        tagsprio = self.pos_priorities[upos]
        for t in tagsprio:
            if t in d.keys():
                return d[t]
        return None

    def set_lemma(self, token: Token) -> None:
        """détermine le lemme d'un token."""

        word: str = token.norm_
        norm: int = token.norm
        upos: str = token.pos_.lower()
        x = self.lookups.get_table(upos).get(norm)
        if x is not None:
            token.lemma_ = x["stem"]
            token._.viceverser = x["morph"]
            return
        elif "-" in token.norm_:
            fn: Callable = self.find_lemma_composed
        else:
            fn: Callable = self.find_lemma
        d = fn(word=word, norm=norm, upos=upos)
        token.lemma_ = d["stem"]
        token._.viceverser = d["morph"]

    def __call__(self, doc: Doc) -> Doc:
        """attribue un lemme à chaque token d'un doc."""

        for token in doc:
            self.set_lemma(token)
        return doc
