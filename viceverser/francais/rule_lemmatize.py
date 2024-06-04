import informifier


class RuleLemmatizer:
    def __init__(self):
        self.inform = informifier.Informitif()

    def rule_lemmatize(self, word: str, upos: str) -> str:
        """Lemmatise un mot à l'aide de règles spécifiques à son POS.

        Args:
            word (str): le mot.
            upos (str): le part-of-speech du mot.

        Returns (str): le lemme proposé.

        Règles relatives au part-of-speech:
            - verb: reconstitue l'infinitif d'un verbe.
            - noun+adj: enlève un éventuel "s" et "x" final.
            - dans les autres cas, retourne simplement le mot lui-même, sans modification.
        """

        if upos in ("verb", "aux") and word[-2:] != "er":
            lemma, like = self.inform(word)
            return lemma  # il faudrait tout retourner et faire l'analyse morphologique
        elif word[-1] in ("x", "s") and upos in ("noun", "adj"):
            return word[:-1], {"is:pl"}
        else:
            return word, {}

    def __call__(self, **kwargs):
        return self.rule_lemmatize(**kwargs)
