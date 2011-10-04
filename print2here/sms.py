import urllib
import urllib2

class SmsNotifier:
    
    def __init__(self, sid, auth, number):
        self.account_sid = sid
        self.auth_token = auth
        self.phone_number = number

    def send_sms(self, number, message):
        data = urllib.urlencode({'From': self.phone_number,
                'To': number,
                'Body': message
        })

        try:
            password_mgr = urllib2.HTTPPasswordMgrWithDefaultRealm()
            password_mgr.add_password(None, 'https://api.twilio.com/2010-04-01', self.account_sid, self.auth_token)
            handler = urllib2.HTTPBasicAuthHandler(password_mgr)
            opener = urllib2.build_opener(handler)

            req = opener.open("https://api.twilio.com/2010-04-01/Accounts/%s/SMS/Messages" % self.account_sid, data)
            req.read()
            req.close()
        except urllib2.HTTPError:
            raise
