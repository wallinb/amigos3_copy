import logging
import re
from time import sleep

from honcho.config import (
    SBD_MAX_SIZE,
    SBD_SIGNAL_TRIES,
    SBD_SIGNAL_WAIT,
)
from honcho.util import serial_request


logger = logging.getLogger(__name__)


def ping(serial):
    expected = re.escape('OK\r\n')
    try:
        logging.debug('Pinging iridium')
        serial_request(serial, 'AT', expected, timeout=10)
    except Exception:
        logging.error('Ping failed')
        raise Exception("Iridium did not respond correctly to ping")
    else:
        logging.debug('Iridium ping ok')


def check_signal(serial):
    expected = re.escape('+CSQ:') + r'(?P<strength>\d)' + re.escape('\r\n')
    try:
        logging.debug('Checking signal')
        response = serial_request(serial, 'AT+CSQ', expected, timeout=10)
    except Exception:
        logging.error('Signal check failed')
        raise Exception("Iridium did not respond correctly to signal query")

    strength = int(re.search(expected, response).groupdict()['strength'])
    logging.debug('Signal strength: {0}'.format(strength))

    return strength


def message_size(message):
    size = len(message.encode('utf-8'))
    return size


def send_sbd(serial, message):
    size = message_size(message)
    assert size <= SBD_MAX_SIZE, "Message is too large: {0} > {1}".format(
        size, SBD_MAX_SIZE
    )

    for _ in xrange(SBD_SIGNAL_TRIES):
        signal = check_signal(serial)
        if signal >= 4:
            break
        sleep(SBD_SIGNAL_WAIT)
    else:
        raise Exception(
            'Signal strength still too low after {0} tries, aborting'.format(
                SBD_SIGNAL_TRIES
            )
        )

    # Initiate write text
    expected = 'READY\r\n'
    serial_request(serial, 'AT+SBDWT', expected, timeout=10)

    # Submit message
    expected = r'(?P<status>\d)' + re.escape('\r\n')
    response = serial_request(serial, message, expected, timeout=30)
    status = int(re.search(expected, response).groupdict()['status'])
    if status:
        raise Exception('SBD write command returned error status')

    # Initiate transfer to GSS
    expected = (
        re.escape('+SBDIX: ')
        + (
            r'(?P<mo_status>\d+), '
            r'(?P<momsn>\d+), '
            r'(?P<mt_status>\d+), '
            r'(?P<mtmsn>\d+), '
            r'(?P<mt_length>\d+), '
            r'(?P<mt_queued>\d+)'
        )
        + re.escape('\r\n')
    )
    response = serial_request(serial, 'AT+SBDIX', expected, timeout=60)
    status = int(re.search(expected, response).groupdict()['mo_status'])
    if status:
        raise Exception('SBD transfer command returned error status')


def clear_mo_buffer(serial):
    logging.debug('Clearing MO buffer')
    expected = r'(?P<status>\d)' + re.escape('\r\n')
    response = serial_request(serial, 'AT+SBDD0', re.escape('\r\n'), timeout=10)
    status = int(re.search(expected, response).groupdict()['status'])
    if status:
        raise Exception('SBD clear mo command returned error status')