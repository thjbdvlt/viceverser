lemmatisation du français avec [hunspell](http://hunspell.github.io/)[^1] pour [spacy](https://spacy.io/api).

ce module propose une manière alternative de [lemmatiser](https://spacy.io/api/lemmatizer) des mots en tirant parti de la facilité avec laquelle on peut, grâce à hunspell, remanier des lexiques, par exemple en ajoutant des mots ou en définissant de nouvelles règles de flexions (par exemple pour l'écriture inclusive). au passage, les tokens se voient attribués des informations supplémentaires issus de l'analyse morphologique: `Token._.vv_pos` (part-of-speech définit pour le mot dans le lexique hunspell) et `Token._.vv_morph` (les caractéristiques morphologiques: la flexion du mot par rapport au lemme).

usage
-----

pour l'ajouter comme composant d'une _pipeline_:

```python
import spacy
import viceverser

nlp = spacy.load("fr_core_news_lg")
nlp.add_pipe("viceverser_lemmatizer", after="morphologizer")
# fonctionne mieux si des part-of-speech sont attribués avant,
# (en français, c'est le morphologizer qui les attribue).
```

installation
------------

```bash
# le module dépend d'un autre mini-module: informifier,
# pour l'analyse des néo-verbes (qui permet ici de récupérer 
# l'analyse morphologique de verbes hors lexique).
git clone https://github.com/thjbdvlt/informifier informifier
cd informifier
pip install .

git clone https://github.com/thjbdvlt/viceverser viceverser
cd viceverser
pip install .
```

[^1]: hunspell est un programme qui effectue des corrections orthographiques (utilisé notamment par libreoffice, openoffice, firefox). mais il réalise en même temps une analyse grammaticale des mots.

part-of-speech
--------------

ce module est fait pour être utilisé dans une pipeline spacy, et je l'ai écrit parce les modèles actuellement (avril 2024) proposés par spacy ne correspondaient pas à mes besoins. outre la difficulté qu'ils ont à lemmatiser des textes utilisant l'écriture inclusive et les mots composés, l'un des défauts de ces modèles est qu'ils sont parfois assez imprécis dans l'assignation des _part-of-speech tags_ (les verbes à l'impératifs présents sont par exemple systématiquement taggés comme étant des noms). or, la lemmatisation dépend des _part-of-speech tags_: le lemme de `sommes (noun)` est _somme_ tandis que le lemme de `sommes (verb)` est _être_.
la pseudo-solution que je propose est la suivante:

```python
tags = {"verb": [
    # tout en haut de chaque liste: le tag lui-même.
    "verb", 
    # les verbes sont souvent confondus avec les auxiliaires.
    # je place donc "aux" tout en haut de la liste.
    "aux",
    # quelques fois, les verbes sont confondus avec des nouns.
    "noun",  
    # ...
    # les verbes ne sont jamais confondus avec de la ponctuation.
    # je peux donc mettre ponctuation tout en bas de la liste.
    "punct",
    ],
    # ..
}
```

un exemple: admettons que dans la phrase _Parle vite!_, le modèle considère que _Parle_ est un nom. la fonction de lemmatisation va utiliser hunspell pour regarder si _parle_ est une forme connue. comme c'est le cas, la fonction prends la liste de priorité pour le tag _nom_. elle commence ainsi:

```python
["noun", "verb", "adj", "..."]
```

la fonction prend, dans l'ordre, chacun de ces tags et regarde si un lemme dans le lexique hunspell lui correspond. comme aucun lemme ne correspond à _parle (nom)_, la fonction essaie avec _parle (verbe)_ et il y a un résultat (_parler_) qui devient donc le lemme du mot. pour que cela puisse fonctionner, il faut donc que le lexique (dans hunspell) attribue aux mots un (ou plusieurs) _part-of-speech_ via l'attribut `po:`.

mots composés
-------------

les lemmes des mots composés (_artistes-peintres_, _autrice-compositrice-interprète_) sont obtenus par la concaténation des lemmes de leurs composants: _artistes-peintres_ deviendra _artiste-peintres_, les deux mots _artistes_ et _peintres_ ayant été mis au singulier. si le lexique considère que _auteurice_ est le lemme de _autrice_, alors _autrice-compositrice_ deviendra _auteurice-compositeurice_.

| mot          | lemme          |
| --           | --             |
|autrices-compositrices|auteurices-compositeurices|

l'avantage de cette méthode est qu'elle ne nécessite pas de connaître à l'avance tous les mots composés possibles (virtuellement infinis). elle peut toutefois produire des résultats déconcertants (et intéressants):

| mot          | lemme          |
| --           | --             |
| peut-être    | pouvoir-être   |
| soi-disant   | soi-dire       |
| gratte-ciel  | gratter-ciel   |
| compte-rendu | compter-rendre |
| vis-à-vis    | voir-à-voir    |
| c'est-à-dire | ce être-à-dire |
| vice-versa   | vice-verser    |

rule lemmatizer
---------------

dans certains cas, le mot ne correspond à aucune forme répertoriée dans le lexique hunspell. pour ces cas, une fonction est définie qui construit le lemme par application de règles (_rule-based lemmatization_). celle proposée par défaut est relative au _part-of-speech tag_: s'il s'agit d'un adjectif ou d'un nom, j'enlève simplement les pluriels en `s` ou `x`, s'il s'agit d'un verbe, je considère d'un verbe du premier groupe car la quasi-totalité des _néo-verbes_ sont des verbes du premier groupe, et j'essaie de reconstruire l'infinitif du verbe à partir de sa forme (ce que je fais en utilisant un autre mini-module que j'ai écrit pour ça: [informifier](https://github.com/thjbdvlt/informifier)), dans tous les autres cas, le lemme est le mot inchangé.

dependancies
------------

- [spacy](https://spacy.io/api)
- [pyhunspell](https://github.com/pyhunspell/pyhunspell)
- [informifier](https://github.com/thjbdvlt/informifier)
