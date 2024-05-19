import informifier


class RuleLemmatizer:
    def __init__(self):
        self.inform = informifier.Informitif()

    def rule_lemmatize(self, word: str, upos: str) -> str:
        """lemmatise un mot à l'aide de règles spécifiques à son POS.

        - verb: reconstitue l'infinitif d'un verbe.
        - noun+adj: enlève un éventuel "s" et "x" final.
        dans les autres cas, retourne simplement le mot lui-même, sans modification.
        """

        if upos in ("verb", "aux"):
            lemma, _ = self.inform(word)
            return lemma
        elif word[-1] in ("x", "s") and upos in ("noun", "adj"):
            return word[:-1]
        else:
            return word

    def __call__(self, **kwargs):
        return self.rule_lemmatize(**kwargs)
