# Copyright 2016 Google Inc. All Rights Reserved.
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

"""Provides base support for managing identity provider sessions."""

class IDPSessionManager(object):
  """Base class for objects that manage identity provider sessions.

  This class is intended to be used in Http sessions where a third-party
  application delegates to an identity provider (IDP) for authentication and
  authorization of access scopes. Operations to initialize IDP sessions
  and revoke/terminate the sessions are provided.
  """

  def initialize(self):
    """Placeholder for specializations to initialize IDP sesisons."""
    raise NotImplementedError()

  def terminate(self):
    """Placeholder for specializations to terminate IDP sessions."""
    raise NotImplementedError()

class IDPSessionError(Exception):
  """Exception for errors in IDP session initialization."""
  def __init__(self, message, cause=None):
    self.message = message
    self.cause = cause
