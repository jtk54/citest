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

"""Provides base support for mutating Requests in HttpAgents."""

class RequestMutator(object):
  """Base class for objects that mutate urllib2.Request objects.

  This class is intended to be used as a filter in HttpAgent to append/provide
  context-specific information to the request before it is sent. This is helpful
  to establish Http session or authentication/authorization state in the request
  in a modular way in HttpAgent.
  """
  def mutate_request(self, req):
    """Placeholder for specializations to perform actual Request mutations."""
    raise NotImplementedError()
