#!/usr/bin/ruby
#
# testflight_invite.rb
#
# TestFlight Inviter
# Copyright 2014-2015 Daniel Magliola
# Copyright 2014-2015 Brian Donohue
#
# Version 1.0
#
# Latest version and additional information available at:
#   http://appdailysales.googlecode.com/
#
# This script will automate TestFlight invites for Apple's TestFlight integration.
#
# This script is translated directly from Brian Donohue's script from Python into Ruby.
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

require 'net/http'
require 'json'

module TestFlight
  class ITCException < StandardError
  end

  class InviteDuplicateException < StandardError
  end

  class RemoveTesterException < StandardError
  end

  class Invite
    BASE_URL = 'itunesconnect.apple.com'

    def initialize(itc_login, itc_password, app_id)
      @itc_login = itc_login
      @itc_password = itc_password
      @app_id = app_id
      @logged_in = false
    end

    def add_tester(email, first_name = '', last_name = '')
      login
      url = "/WebObjects/iTunesConnect.woa/ra/user/externalTesters/#{@app_id}/"
      params = { users: [{emailAddress: {errorKeys: [], value: email},
                          firstName: {value: first_name},
                          lastName: {value: last_name},
                          testing: {value: true}
                         }]}

      response = request(url, :post, params.to_json)
      raise TestFlight::InviteDuplicateException.new if response.code.to_i == 500 # 500 if tester already exists... This is not how you HTTP, Apple.
      return JSON.parse(response.body)['statusCode']
    end

    def remove_tester(email)
      login
      url = "/WebObjects/iTunesConnect.woa/ra/user/externalTesters/#{@app_id}/"

      params = { users: [{emailAddress: {errorKeys: [], value: email},
        firstName: {value: ''},
        lastName: {value: ''},
        testing: {value: false}
      }]}

      # Fetch the number of users *before* we remove remove our user (You are awesome Apple)
      num_testers_before_delete = num_testers

      # POST
      response = request(url, :post, params.to_json)

      raise TestFlight::RemoveTesterException.new("server error") if response.code.to_i == 500 # 500 if tester already exists... This is not how you HTTP, Apple.

      result = JSON.parse(response.body)

      # Now fetch the number of users *after* the DELETE.  Apple sure must hate developers...
      num_testers_after_delete = result["data"]["users"].count

      # If DELETE was successful, there should be 1 less user from num_testers
      num_testers_deleted = num_testers_before_delete - num_testers_after_delete;

      raise RemoveTesterException.new("failed to remove tester #{email}") if num_testers_deleted == 0

      return JSON.parse(response.body)['statusCode']
    end

    def num_testers
      login
      url = "/WebObjects/iTunesConnect.woa/ra/user/externalTesters/#{@app_id}/"
      data = JSON.parse(request(url, :get).body)
      return data['data']['users'].length
    end

    private

    def login
      return if @logged_in
      # Go to the iTunes Connect website and retrieve the form action for logging into the site.
      url = "/WebObjects/iTunesConnect.woa"
      response = request(url, :get)
      match = response.body.match('" action="(.*)"')

      # Login to iTunes Connect web site
      url = match[1]
      params = { 'theAccountName' =>  @itc_login, 'theAccountPW' => @itc_password, '1.Continue.x' => '0', '1.Continue.y' => '0', 'inFrame' => '0', 'theAuxValue' => ''}
      response = request(url, :post, URI.encode_www_form(params))
      if response.body.include?('Your Apple ID or password was entered incorrectly.')
        raise TestFlight::ITCException.new('User or password incorrect.')
      end
      @logged_in = true
    end

    def request(url, method, params = nil)
      headers = {}
      headers['Cookie'] = @cookie unless @cookie.nil?

      http = Net::HTTP.new(BASE_URL, 443)
      http.use_ssl = true
      if method == :post
        response = http.post(url, params, headers)
      else
        response = http.get(url, headers)
      end
      @cookie = response.to_hash['set-cookie'].collect{|ea|ea[/^.*?;/]}.join
      response
    end
  end
end

def usage
  puts 'Usage: <iTC login email> <iTC login password> <App ID> <Invitee Email> <Invitee First Name (Optional)> <Invitee Last Name (Optional)'
end

def main
  if ARGV.count < 4
    usage
    exit
  end
  invite = TestFlight::Invite.new(ARGV[0], ARGV[1], ARGV[2])
  result = invite.add_tester(ARGV[3], ARGV[4], ARGV[5])
  puts result
end

# run Main() only if the script was the main, not loaded or required
main if __FILE__==$0
