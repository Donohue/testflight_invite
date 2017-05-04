#!/usr/bin/python
#
# testflight_invite.py
#
# TestFlight Inviter
# Copyright 2014-2015 Brian Donohue
#
# Version 1.0
#
# Latest version and additional information available at:
#   http://appdailysales.googlecode.com/
#
# This script will automate TestFlight invites for Apple's TestFlight integration.
#
# This script is heavily based off of appdailysales.py (https://github.com/kirbyt/appdailysales)
# Original Maintainer
#   Kirby Turner
#
# Original Contributors:
#   Leon Ho
#   Rogue Amoeba Software, LLC
#   Keith Simmons
#   Andrew de los Reyes
#   Maarten Billemont
#   Daniel Dickison
#   Mike Kasprzak
#   Shintaro TAKEMURA
#   aaarrrggh (Paul)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import json
import urllib
import urllib2
import cookielib
import re
import sys
import os
import requests
from getpass import getpass

import logging
logger = logging.getLogger(__name__)

class ITCException(Exception):
    def __init__(self,value):
        self.value = value
    def __str__(self):
        return repr(self.value);

class TFInviteDuplicateException(Exception):
    pass

# There is an issue with Python 2.5 where it assumes the 'version'
# cookie value is always interger.  However, itunesconnect.apple.com
# returns this value as a string, i.e., "1" instead of 1.  Because
# of this we need a workaround that "fixes" the version field.
#
# More information at: http://bugs.python.org/issue3924
class MyCookieJar(cookielib.CookieJar):
    def _cookie_from_cookie_tuple(self, tup, request):
        name, value, standard, rest = tup
        version = standard.get('version', None)
        if version is not None:
            version = version.replace('"', '')
            standard["version"] = version
        return cookielib.CookieJar._cookie_from_cookie_tuple(self, tup, request)

class TestFlightInvite:
    urlITCBase = 'https://itunesconnect.apple.com%s'

    def __init__(self, itcLogin, itcPassword, appId, proxy='', groupId=None, contentProviderId=None):
        self.itcLogin = itcLogin
        self.itcPassword = itcPassword
        self.appId = str(appId)
        self._service_key = None
        self.proxy = proxy
        if groupId is not None:
            self.groupId = groupId
        if contentProviderId is not None:
            self.contentProviderId = contentProviderId
        self.opener = self.createOpener()
        self.loggedIn = False

    def readData(self, url, data=None, headers={}, method=None):
        request = urllib2.Request(url, data, headers)
        if method is not None:
            request.get_method = lambda: method
        urlHandle = self.opener.open(request)
        return urlHandle.read()

    def createOpener(self):
        handlers = []                                                       # proxy support
        if self.proxy:                                                      # proxy support
            handlers.append(urllib2.ProxyHandler({"https": self.proxy}))    # proxy support

        cj = MyCookieJar();
        cj.set_policy(cookielib.DefaultCookiePolicy(rfc2965=True))
        cjhdr = urllib2.HTTPCookieProcessor(cj)
        handlers.append(cjhdr)                                              # proxy support
        return urllib2.build_opener(*handlers)                              # proxy support

    @property
    def service_key(self):
        if self._service_key:
            return self._service_key

        jsUrl = self.urlITCBase % '/itc/static-resources/controllers/login_cntrl.js'
        content = self.readData(jsUrl)
        matches = re.search(r"itcServiceKey = '(.*)'", content)
        if not matches:
            raise ValueError('Unable to find iTunes Connect Service key')
        return matches.group(1)

    def getGroups(self):
        text = self.readData('https://itunesconnect.apple.com/testflight/v2/providers/{teamId}/apps/{appId}/groups'.format(
            teamId=self.contentProviderId, appId=self.appId
        ))
        data = json.loads(text)
        return data['data']

    def getDefaultExternalGroupId(self):
        if not hasattr(self, 'groupData'):
            self.groupData = self.getGroups()
        defaultExternalGroups = [g for g in self.groupData if g['isDefaultExternalGroup']]
        if len(defaultExternalGroups) > 0:
            return defaultExternalGroups.pop()['id']
        else:
            return None

    def getFirstContentProviderId(self):
        # Sample return value
        # => {"associatedAccounts"=>
        #   [{"contentProvider"=>{"contentProviderId"=>11142800, "name"=>"Felix Krause", "contentProviderTypes"=>["Purple Software"]}, "roles"=>["Developer"], "lastLogin"=>1468784113000}],
        #  "sessionToken"=>{"dsId"=>"8501011116", "contentProviderId"=>18111111, "expirationDate"=>nil, "ipAddress"=>nil},
        text = self.readData("https://itunesconnect.apple.com/WebObjects/iTunesConnect.woa/ra/user/detail")
        data = json.loads(text)
        account = data['data']['associatedAccounts'][0]
        return account['contentProvider']['contentProviderId']

    def login(self):
        if not self.loggedIn:
            data = {
                'accountName': self.itcLogin,
                'password': self.itcPassword,
                'rememberMe': 'false'
            }
            headers = {
                'Content-Type': 'application/json',
                'X-Requested-With': 'XMLHttpRequest',
                'Accept': 'application/json, text/javascript'
            }

            loginUrl = 'https://idmsa.apple.com/appleauth/auth/signin?widgetKey=%s' % self.service_key
            self.readData(
                'https://idmsa.apple.com/appleauth/auth/signin?widgetKey=%s' % self.service_key,
                data=json.dumps(data),
                headers=headers
            )

            if not hasattr(self, 'contentProviderId'):
                self.contentProviderId = self.getFirstContentProviderId()
                logger.info('Guessed contentProviderId: {}'.format(self.contentProviderId))
                # print self.contentProviderId

            if not hasattr(self, 'groupId'):
                self.groupId = self.getDefaultExternalGroupId()
                logger.info('Guessed groupId: {}'.format(self.groupId))

        self.loggedIn = True

    def numTesters(self):
        self.login()
        endpoint = '/WebObjects/iTunesConnect.woa/ra/user/externalTesters/%s/' % self.appId
        urlWebsiteExternalTesters = self.urlITCBase % endpoint
        externalResponse = self.readData(
            "https://itunesconnect.apple.com/WebObjects/iTunesConnect.woa/ra/user/externalTesters/%s/" % self.appId,
            headers={'Content-Type': 'application/json'}
        )
        data = json.loads(externalResponse)
        return len(data['data']['users'])

    def addTester(self, email, firstname='', lastname=''):
        self.login()
        params = { 'email': email, 'firstName': firstname, 'lastName': lastname }
        try:
            text = self.readData(
                'https://itunesconnect.apple.com/testflight/v2/providers/{teamId}/apps/{appId}/testers'.format(
                    teamId=self.contentProviderId, appId=self.appId
                ),
                json.dumps(params),
                headers={'Content-Type': 'application/json'}
            )
        except urllib2.HTTPError as e:
            raise

        testerResponseBody = json.loads(text)
        testerId = testerResponseBody['data']['id']
        params = {
            'groupId': self.groupId,
            'testerId': testerId,
        }

        try:
            return self.readData(
                'https://itunesconnect.apple.com/testflight/v2/providers/{teamId}/apps/{appId}/groups/{groupId}/testers/{testerId}'.format(
                    teamId=self.contentProviderId, appId=self.appId, groupId=self.groupId, testerId=testerId
                ),
                json.dumps(params),
                headers={'Content-Type': 'application/json'},
                method='PUT'
            )
        except urllib2.HTTPError as e:
            raise

def usage():
    print 'Usage: %s <iTC login email> <App ID> <Invitee Email> <Invitee First Name (Optional)> <Invitee Last Name (Optional)' % sys.argv[0]

def main():
    if len(sys.argv) < 4:
        usage()
        return -1

    itcLogin = sys.argv[1]

    try:
        appId = int(sys.argv[2])
    except Exception as e:
        print 'Invalid App ID'
        usage()
        sys.exit(-1)

    email = sys.argv[3]
    firstName = sys.argv[4] if len(sys.argv) > 4 else ''
    lastName = sys.argv[5] if len(sys.argv) > 5 else ''

    try:
        itcPassword = getpass('iTunes Connect Password: ')
        assert len(itcPassword)
    except:
        print '\nFailed to get iTunes Connect password. Aborting...'
        usage()
        return -1

    try:
        invite = TestFlightInvite(itcLogin, itcPassword, appId)
        invite.addTester(email, firstName, lastName)
        print 'Invite Successful'
    except TFInviteDuplicateException as e:
        print '%s already a tester for AppID %d' % (email, appId)
        return -2
    except Exception as e:
        print 'Invite Failed: %s' % str(e)
        return -3

if __name__ == '__main__':
    sys.exit(main())
