import twilio
import urllib2

class SmsException(Exception):
    pass

class SmsNotifier:
    
    def __init__(self, sid, auth, number, api):
        self.account_sid = sid
        self.auth_token = auth
        self.phone_number = number
        self.api_version = api

    def send_sms(self, number, message):
        account = twilio.Account(self.account_sid, self.auth_token)
        data = {'From': self.phone_number,
                'To': number,
                'Body': message
        }
        try:
            account.request('/%s/Accounts/%s/SMS/Messages' % (self.api_version, self.account_sid), \
                'POST', data)
        except urllib2.HTTPError:
            raise SmsException
