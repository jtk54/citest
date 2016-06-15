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

# Standard python modules.
import requests
import urllib2

from bs4 import BeautifulSoup

# Our modules.
from ..service_testing import request_mutator
from ..service_testing import idp_manager

GOOGLE_ACCOUNT_LOGIN_URL = 'https://accounts.google.com/ServiceLogin'
GOOGLE_ACCOUNT_LOGOUT_URL = 'https://www.google.com/accounts/Logout'

class GoogleIDPSession(request_mutator.RequestMutator,
                       idp_manager.IDPSessionManager):
  """Utility for accessing applications that use Google as an identity provider.

  This automates Google OAuth2/SAML account authentication and scope approval
  after a redirect from a third party application.

  The intended workflow is the following:

  * Target some resource in a third party application.
  * The third party application needs some information in your Google account.
  * The third party application redirects you to Google to sign in and approve
    the scopes the application is requesting. (This is automated by this class).
  * A Http session is established with Google and tracked with Cookies in
    the request/response headers.
  * Possibly, a Http session is established with the third party application
    as well.
  * Make requests in the established session scope.
  * Log out after the necessary exchange is made.

  This class automtes both the Google account login and scope approval to create
  an authenticated HTTP session, and provides access to the session cookies for
  use with urllib2 Requests. Both direct access to the Cookies and mutating
  requests via RequestMutator methods are supported.

  Example usage:
    # target_url should forward to 'accounts.google.com/ServiceLogin' page
    # via an OAuth2 or SAML redirect.
    target_url = "http://<gate_host>/credentials"
    logout_url = "http://<gate_host>/auth/logout"
    session = GoogleIDPSession(target_url,
                           "user@domain.net",
                           "secret_pass_word",
                           logout_url=logout_url)
    session.initialize()
    req = urllib2.Request(url=target_url)
    self.mutate_request(req) # loads cookies into request header
    resp = urllib2.urlopen(req)
    session.terminate()
  """


  def __init__(
      self, target_url, login, password,
      user_approval_url='https://accounts.google.com/ServiceLoginAuth',
      logout_url=None):
    """Construct an instance.

    Args:
      target_url [String]: A URL that will eventually redirect to
        'https://accounts.google.com/ServiceLogin' given a new session.
      login [String]: Username/email to login as.
      password: [String] Password for the provided login.
      user_approval_url [String]: (Optional) The URL for a Google user to grant
        approval to an application. Can override if necessary.
      logout_url [String]: (Optional) The logout url of the application we are
        authenticating to.
    """
    self.__session = requests.session()
    self.__target_url = target_url
    self.__login = login
    self.__password = password
    self.__user_approval_url = user_approval_url
    self.__logout_url = logout_url
    self.__is_initialized = False


  def initialize(self):
    """Initialize a session using Google as the IDP."""
    if self.__is_initialized:
      return

    try:
      login_resp = self.__session.get(self.__target_url)
    except Exception as e:
      __throw_http_session_exception(e, 'GET', self.__target_url)

    if (GOOGLE_ACCOUNT_LOGIN_URL
        not in login_resp.url[:len(GOOGLE_ACCOUNT_LOGIN_URL)]):
      raise idp_manager.IDPSessionError(
        'Target URL did not redirect to Google account login page.'
      )
    login_form_inputs = (BeautifulSoup(login_resp.content)
        .find('form')
        .find_all('input'))
    login_dict = {}
    for input in login_form_inputs:
      if input.has_attr('value'):
        login_dict[input['name']] = input['value']

    login_dict['Email'] = self.__login
    login_dict['Passwd'] = self.__password
    try:
      post_response = self.__session.post(self.__user_approval_url,
                                          data=login_dict)
    except Exception as e:
      __throw_http_session_exception(e, 'POST', self.__user_approval_url)

    approval_form = BeautifulSoup(post_response.content).find('form')
    approval_dict = {}
    for input in approval_form.find_all('input'):
      if input.has_attr('value'):
        approval_dict[input['name']] = input['value']
    approval_dict['submit_access'] = 'true'
    try:
      self.__session.post(approval_form['action'], data=approval_dict)
    except Exception as e:
      __throw_http_session_exception(e, 'POST', approval_form['action'])
    self.__is_initialized = True


  def terminate(self):
    """Log out of the current authenticated Google session and the target
    service's session if applicable.
    """
    if self.__logout_url:
      try:
        self.__session.post(self.__logout_url)
      except Exception as e:
        __throw_http_session_exception(e, 'POST', self.__logout_url)

    try:
      self.__session.post(GOOGLE_ACCOUNT_LOGOUT_URL)
    except Exception as e:
      __throw_http_session_exception(e, 'POST', GOOGLE_ACCOUNT_LOGOUT_URL)
    self.__session.cookies = None


  @property
  def cookies(self):
    """Get the HTTP session cookies from the current Google session.

    Returns:
      The collection of Cookie objects associated with the authenticated Google
      session as a CookieJar object.
      CookieJar documentation: https://docs.python.org/2.7/library/cookielib.html#cookiejar-and-filecookiejar-objects
    """
    if not self.__session.cookies:
      raise AttributeError('No Http session cookies present!')
    return self.__session.cookies


  def mutate_request(self, req):
    """Add the Google Session cookies to the request header.

    Args:
      req [urllib2.Request]: The request to add the Google Session cookies to.
    """
    if not isinstance(req, urllib2.Request):
      raise TypeError('req not urllib2.Request: ' + req.__class__.__name__)
    self.cookies.add_cookie_header(req)


def __throw_http_session_exception(cause, method, url):
  """Throw an exception caused by trying to access a url in the session flow.

  Args:
    cause [Exception]: Exception that was caught during the HTTP execution.
    method [String]: Name of the HTTP method that was executed during the
      failure.
    url [String]: Target URL of the HTTP method.

  Returns:
    IDPSessionError with a pointer to the cause Exception and a reasonable
      error message.
  """
  msg = "%s failed targeting %s" % (method, url)
  raise idp_manager.IDPSessionError(msg, cause)
