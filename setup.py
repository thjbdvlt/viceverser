from setuptools import setup

setup(
    name="viceverser",
    entry_points={
        "spacy_factories": ["viceverser_lemmatizer = viceverser.lemmatizer:create_viceverser_lemmatizer"]
    }
)
