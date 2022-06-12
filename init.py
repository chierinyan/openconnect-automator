#!/usr/bin/python3

import json
import sys, subprocess

from poplib import POP3_SSL
from email import message_from_bytes

from time import sleep
from datetime import datetime, timedelta, timezone

import logging
LOG_FORMAT = '[%(asctime)s][%(levelname)s] %(message)s'

logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)


CREDENTIALS_PATH = '/credentials.json'
try:
    with open(CREDENTIALS_PATH) as cf:
        credentials = json.load(cf)
except FileNotFoundError:
    logging.critical('Failed to find credentials.')
    exit(233)


TUN_INTERFACE = 'hku'

OPENCONNECT_CMD = ['openconnect',
    '--no-dtls',
    '--useragent', 'AnyConnect',
    '--interface', TUN_INTERFACE,
    '--reconnect-timeout', '30',
    '--script',
    'vpn-slice --prevent-idle-timeout --incoming 147.8.0.0/16 10.64.0.0/12;' +
    f'if echo $reason | grep -Eq "^(re)?connect"; then curl -Ssk {credentials["ddns_url"]}; fi',
    credentials['openconnect']['server']
]


class MailClient:
    def __init__(self):
        self.pop_server = POP3_SSL(credentials['mail']['server'])
        self.pop_server.user(credentials['mail']['address'])
        self.pop_server.pass_(credentials['mail']['password'])

    def download_last_mail(self):
        try:
            mail_count = len(self.pop_server.list()[1])
            while mail_count > 0:
                mail_bytes_list = self.pop_server.retr(mail_count)[1]
                mail_bytes = b'\n'.join(mail_bytes_list)
                mail = message_from_bytes(mail_bytes)
                if 'HKU 2FA Email Token Code' in mail['Subject']:
                    return mail
            logging.info('No mail found in selected mailbox')
        except Exception as e:
            logging.error(e)

        return None

    def parse_token(self):
        initial_time = datetime.now(timezone(timedelta(hours=8)))
        for _ in range(30):
            sleep(10)
            mail = self.download_last_mail()
            if mail is None:
                continue

            sent_time = datetime.strptime(mail['Date'].split(', ')[-1], '%d %b %Y %H:%M:%S %z')
            delta = sent_time - initial_time
            if timedelta(seconds=-10) < delta < timedelta(minutes=5):
                token = mail['Subject'].split()[-1]
                self.pop_server.quit()
                return token
        return None

def main():
    logging.info('Starting new connection')

    oc = subprocess.Popen(OPENCONNECT_CMD, bufsize=1,
                          stdin=subprocess.PIPE, stdout=sys.stdout, stderr=sys.stderr,
                          encoding='utf-8')
    oc.stdin.write(credentials['openconnect']['username']+'\n')
    oc.stdin.write(credentials['openconnect']['password']+'\n')

    token = MailClient().parse_token()
    if token:
        oc.stdin.write(token+'\n')
        oc.wait()
    else:
        logging.fatal(f'Failed getting token')
        exit(233)


if __name__ == '__main__':
    main()
