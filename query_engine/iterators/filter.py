# filter.py
# Author: Thomas MINIER - MIT License 2017-2018
from query_engine.iterators.preemptable_iterator import PreemptableIterator
from query_engine.filter.runtime import FILTER_RUNTIME
from query_engine.filter.utils import compile_literal
from query_engine.protobuf.iterators_pb2 import SavedFilterIterator
from query_engine.iterators.utils import IteratorExhausted
from string import Template


class FilterIterator(PreemptableIterator):
    """A FilterIterator evaluates a FILTER clause on set of mappings"""

    def __init__(self, source, expression, variables):
        super(FilterIterator, self).__init__()
        self._source = source
        self._expression = expression
        self._template = Template(expression)
        self._variables = variables
        self._baseBindings = {key: None for key in self._variables}

    def __repr__(self):
        return "<FilterIterator '{}' (variables: {}) on {}>".format(self._expression, self._variables, self._source)

    def serialized_name(self):
        return "filter"

    def _evaluate(self, bindings):
        b = dict(self._baseBindings)
        for key, value in bindings.items():
            b[key[1:]] = compile_literal(value)
        return eval(self._template.substitute(b), FILTER_RUNTIME)

    async def next(self):
        if not self.has_next():
            raise IteratorExhausted()
        mu = await self._source.next()
        while not self._evaluate(mu):
            mu = await self._source.next()
        return mu

    def has_next(self):
        """Return True if the iterator has more item to yield"""
        return self._source.has_next()

    def save(self):
        """Save and serialize the iterator as a machine-readable format"""
        saved_filter = SavedFilterIterator()
        source_field = self._source.serialized_name() + '_source'
        getattr(saved_filter, source_field).CopyFrom(self._source.save())
        saved_filter.expression = self._expression
        saved_filter.variables.extend(self._variables)
        return saved_filter
