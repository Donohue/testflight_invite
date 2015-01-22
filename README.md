# TestFlightInvite

TestFlightInvite is a Python / Ruby script that will add TestFlight beta testers to the iTunes Connect portal for your app.

# About

TestFlightInvite can be used as a stand-alone program or as part of another Python / Ruby project.

The script works by performing the necessary web requests to log a developer into iTunes Connect, and use the returned authentication cookies to perform the invite web request.

*NOTE:* testflight\_invite requires your iTunes Connect password to complete the TestFlight invite. If you use the script as part of another project you will need to store your iTunes Connect password somewhere it can be retrieved in plaintext in order to pass to the library. On the command line your iTunes Connect password is entered using the [getpass](https://docs.python.org/2/library/getpass.html) library, which allows you to enter your password using stdin without echoing the password on the command line.

## Use as a stand-alone program

Usage:

    python testflight_invite.py <iTC login email> <App ID> <Invitee Email> <Invitee First Name (Optional)> <Invitee Last Name (Optional)>
    ruby   testflight_invite.rb <iTC login email> <iTC login password> <App ID> <Invitee Email> <Invitee First Name (Optional)> <Invitee Last Name (Optional)>

Example Run:

    python testflight_invite.py <iTC login email> <App ID> <Invitee Email>
    iTunes Connect Password: 
    Invite Successful

## Use as part of another script

Python:

    from testflight_invite import TestFlightInvite, TFInviteDuplicateException
    try:
        invite = TestFlightInvite(<iTC email>, <iTC password>, <App ID>)
        res = invite.addTester(<Email>, <First Name (optional)>, <Last Name(optional)>)
        # addTester returns the request response (JSON) as a string
        data = json.loads(res)
        print '%d beta testers!' % len(data['data']['users'])
    except TFInviteDuplicateException as e:
        print '%s is already a beta tester!' % email
    except Exception as e:
        print 'Oops! Something went wrong!'

Ruby:

    require 'testflight_invite'
    begin
        invite = TestFlight::Invite.new(<iTC email>, <iTC password>, <App ID>)
        result = invite.add_tester(<Email>, <First Name (optional)>, <Last Name(optional)>)
        # addTester returns "SUCCESS" or "ERROR"
        puts "beta tester added!" if result == "SUCCESS"
    rescue TestFlight::InviteDuplicateException => e
        puts "#{email} is already a beta tester!"
    rescue Exception => e
        puts 'Oops! Something went wrong!'
    end

# Credits

This script is heavily based off of the [appdailysales](https://github.com/kirbyt/appdailysales) project by [Kirby Turner](https://github.com/kirbyt) and friends.

testflight\_invite.py was created by [Donohue](https://github.com/Donohue)

testflight\_invite.rb was created by [dmagliola](https://github.com/dmagliola)

