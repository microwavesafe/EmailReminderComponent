#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys

# random ID
import string
import random

# date string
import datetime

# config files
import yaml

# sending email
import smtplib

# xmpp
import logging
import getpass
from optparse import OptionParser

import sleekxmpp
from sleekxmpp.componentxmpp import ComponentXMPP

# Python versions before 3.0 do not use UTF-8 encoding
# by default. To ensure that Unicode is handled properly
# throughout SleekXMPP, we will set the default encoding
# ourselves to UTF-8.
if sys.version_info < (3, 0):
    reload(sys)
    sys.setdefaultencoding('utf8')
else:
    raw_input = input

global config

class RemindComponent(ComponentXMPP):

    """
    A simple SleekXMPP component that echoes messages.
    """

    def __init__(self, jid, secret, server,port):
        ComponentXMPP.__init__(self, jid, secret, server, port)
        self.add_event_handler("message", self.message)

    def id_generator(self, size=6, chars=string.ascii_uppercase + string.digits):
        return ''.join(random.choice(chars) for _ in range(size))

    def message(self, msg):
        global config

        try:
            server = None
            jid = msg['from'].bare

            # get to email address from config file
            if jid not in config['email_addresses']:
                logging.debug("no mapped address, do not send email or reply")
                return

            # to prevent gmail grouping, add date time to subject line
            # there doesn't seem to be any other way to do this, which is annoying because I don't want crap on the subject line
            emailMsg = "From: " + config['smtp_user'] + "\r\nTo: " + config['email_addresses'][jid] + "\r\nSubject: Reminder (" + datetime.datetime.now().strftime("%Y/%m/%d %H:%M:%S") + ")\r\n\r\n" + msg['body']
            smtpPort = int(config.get('smtp_port', 587))
            server = smtplib.SMTP(config['smtp_server'] + ':' + str(smtpPort))

            # debug smtp connection, if log level set to debug
            if config['logging_level'] == 'debug':
                server.set_debuglevel(1)

            server.ehlo()
            server.starttls()
            server.login(config['smtp_user'], config['smtp_pass'])
            server.sendmail(config['smtp_user'], config['email_addresses'][jid], emailMsg)
            logging.info("mail sent")
            self.send_message(mto=msg['from'], mbody='reminder set', mtype='chat')

        except Exception as e:
            logging.exception("could not send mail")
            self.send_message(mto=msg['from'], mbody='reminder failed', mtype='chat')

        finally:
            if server != None:
                server.quit()


if __name__ == '__main__':
    # Setup the command line arguments.
    optp = OptionParser()

    # Output verbosity options.
    optp.add_option("-l", "--logfile", default=None, help='File where the log will be stored, default is stdout')

    # Config
    optp.add_option('-c', '--config', help='specify config file path', dest='config', default='config.yml')

    opts, args = optp.parse_args()

    with open(opts.config,'r') as ymlfile:
        config = yaml.load(ymlfile)

    # set up component options
    jid = config['component_jid']
    secret = config['component_secret']
    port = int(config.get('component_port',5347))

    # set up logging
    if config['logging_level'] == 'quiet':
        loglevel=logging.ERROR
    elif config['logging_level'] == 'verbose':
        loglevel=5
    elif config['logging_level'] == 'debug':
        loglevel=logging.DEBUG
    else:
        loglevel=logging.INFO

    logging.basicConfig(level=loglevel, format='%(asctime)-24s %(levelname)-8s %(message)s', filename=opts.logfile)

    # Setup the EchoComponent and register plugins. Note that while plugins
    # may have interdependencies, the order in which you register them does
    # not matter.
    xmpp = RemindComponent(jid, secret, 'localhost', port)
    xmpp.registerPlugin('xep_0030') # Service Discovery
    xmpp.registerPlugin('xep_0004') # Data Forms
    xmpp.registerPlugin('xep_0060') # PubSub
    xmpp.registerPlugin('xep_0199') # XMPP Ping

    # Connect to the XMPP server and start processing XMPP stanzas.
    if xmpp.connect():
        xmpp.process(block=True)
        print("Done")
    else:
        print("Unable to connect.")

