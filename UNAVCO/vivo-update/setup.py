# -*- coding: utf-8 -*-
from setuptools import setup, find_packages

setup(
    name='grabDatacite',
    author='Benjamin Gross',
    version="0.1",
    license='MIT',
    packages=find_packages(),
    include_package_data=False,
    install_requires=["rdflib","SPARQLWrapper", "requests",
    				  "lxml","jsonpickle","tabulate",
    				  "fuzzywuzzy","python-Levenshtein"],
)
