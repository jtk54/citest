# Copyright 2015 Google Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Implements ValuePredicate that determines when a given value is 'valid'."""


from ..base import JsonSnapshotable


class ValuePredicate(JsonSnapshotable):
  """Base class denoting a predicate that determines if a JSON value is ok.

   This class must be specialized with a __call__ method that takes a single
   value object and returns None if the value is acceptable, or a JsonError
   explaining why it is not.

   The intent of this class is to check if a JSON object contains fields
   with particular values, ranges or other properties.
  """

  def __call__(self, value):
    """Apply this predicate against the provided value.

    Args:
      value: The value to consider.

    Returns:
      PredicateResult with the value if valid, or error if not valid.
    """
    raise NotImplementedError(
        '__call__() needs to be specialized for {0}'.format(
            self.__class__.__name__))

  def __repr__(self):
    return str(self)

  def __ne__(self, op):
    return not self.__eq__(op)


class PredicateResult(JsonSnapshotable):
  """Base class for predicate results.

  Attributes:
    cause: Typically for errors, if this is non-empty then it indicates
      some upstream reason why this predicate failed that is usually
      out of band (e.g. an exception or preprocessing failure).
    comment: An error message string for reporting purposes only.
    valid: A boolean indicating whether the result is considerd valid or not.
    """

  @property
  def summary(self):
    return '{name} ({valid})'.format(
        name=self.__class__.__name__,
        valid='GOOD' if self.__valid else 'BAD')

  @property
  def comment(self):
    return self.__comment

  @property
  def cause(self):
    return self.__cause

  @property
  def valid(self):
    return self.__valid

  def export_to_json_snapshot(self, snapshot, entity):
    builder = snapshot.edge_builder
    verified_relation = builder.determine_valid_relation(self.__valid)
    builder.make(entity, 'Valid', self.__valid, relation=verified_relation)
    if self.__comment:
      builder.make(entity, 'Comment', self.__comment)
    if self.__cause:
      builder.make(entity, 'Cause', self.__cause)

    # Set a default relation so that this can be picked up when it appears
    # as a list element.
    entity.add_metadata('_default_relation', verified_relation)

  def __init__(self, valid, comment="", cause=None):
    self.__valid = valid
    self.__comment = comment
    self.__cause = cause

  def __repr__(self):
    return str(self)

  def __str__(self):
    return (self.__comment
            or '{0} is {1}'.format(self.__class__.__name__,
                                   'OK' if self.__valid else 'FAILURE'))

  def __nonzero__(self):
    return self.__valid

  def __eq__(self, result):
    if (self.__class__ != result.__class__
        or self.__valid != result.valid
        or self.__comment != result.comment):
      return False

    # If cause was an exception then just compare classes.
    # Otherwise compare causes.
    # We assume cause is None, and Exception, or another PredicateResult.
    # Exceptions do not typically support value equality.
    if self.__cause != result.cause:
      return (isinstance(self.__cause, Exception)
              and self.__cause.__class__ == result.cause.__class__)
    return self.__cause == result.cause

  def __ne__(self, result):
    return not self.__eq__(result)


class CompositePredicateResult(PredicateResult):
  """Aggregates a collection of predicate results into a single response.

  Attributes:
    pred: The ValuePredicate doing the aggregation.
    results: The list of PredicateResponse instances being aggregated.
  """

  @property
  def pred(self):
    return self.__pred

  @property
  def results(self):
    return self.__results

  def export_to_json_snapshot(self, snapshot, entity):
    builder = snapshot.edge_builder
    summary = builder.object_count_to_summary(
        self.__results, subject='mapped result')
    builder.make_mechanism(entity, 'Predicate', self.__pred)
    builder.make(entity, '#', len(self.__results))

    result_entity = snapshot.new_entity(summary='Composite Results')
    for index, result in enumerate(self.__results):
        builder.make(result_entity, '[{0}]'.format(index), result,
                     relation=builder.determine_valid_relation(result),
                     summary=result.summary)
    builder.make(entity, 'Results', result_entity,
                 relation=builder.determine_valid_relation(self))
    super(CompositePredicateResult, self).export_to_json_snapshot(
        snapshot, entity)

  def __str__(self):
    return '{0}'.format(self.__results)

  def __init__(self, valid, pred, results, comment=None, cause=None):
    super(CompositePredicateResult, self).__init__(
        valid, comment=comment, cause=cause)
    self.__pred = pred
    self.__results = results

  def __eq__(self, result):
    return (self.__class__ == result.__class__
            and self.__pred == result.pred
            and self.__results == result.results)


class CompositePredicateResultBuilder(object):
  """Helper class for building a composite result."""

  def __init__(self, pred):
    self.__pred = pred
    self.cause = None
    self.comment = None
    self.__results = []

  def append_result(self, result):
    self.__results.append(result)

  def extend_results(self, results):
    self.__results.extend(results)

  def build(self, valid):
    return CompositePredicateResult(
        valid, self.__pred, self.__results, self.comment, self.cause)
