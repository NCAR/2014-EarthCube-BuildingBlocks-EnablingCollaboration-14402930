# https://github.com/carltonnorthern/nickname-and-diminutive-names-lookup

import collections
import csv
import operator
import os

class NameDenormalizer(object):
    def __init__(self, filename=None):
        lookup = collections.defaultdict(list)
        with open(filename) as f:
            reader = csv.reader(f)
            for line in reader:
                matches = set(line)
                for match in matches:
                    lookup[match].append(matches)
        self.lookup = lookup

    def __getitem__(self, name):
        name = name.lower()
        if name not in self.lookup:
            raise KeyError(name)
        names = reduce(operator.or_, self.lookup[name])
        if name in names:
            names.remove(name)
        return names

    def get(self, name, default=None):
        try:
            return self[name]
        except KeyError:
            return default
