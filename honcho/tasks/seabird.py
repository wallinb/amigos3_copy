import re
from datetime import datetime
from logging import getLogger
from collections import namedtuple
import time

from honcho.config import UNIT, DATA_TAGS, SEP
from honcho.core.imm import active_line, imm_components, REMOTE_RESPONSE_END
from honcho.tasks.sbd import queue_sbd
from honcho.core.data import log_data
from honcho.util import (
    serial_request,
    fail_gracefully,
    log_execution,
    serialize_datetime,
    deserialize_datetime,
)

logger = getLogger(__name__)

_DATA_KEYS = (
    'TIMESTAMP',
    'DEVICE_ID',
    'TEMPERATURE',
    'CONDUCTIVITY',
    'PRESSURE',
    'SALINITY',
)
_VALUE_KEYS = _DATA_KEYS[2:]
DATA_KEYS = namedtuple('DATA_KEYS', _DATA_KEYS)(*_DATA_KEYS)
VALUE_KEYS = namedtuple('VALUE_KEYS', _VALUE_KEYS)(*_VALUE_KEYS)
VALUE_CONVERSIONS = {
    VALUE_KEYS.TEMPERATURE: float,
    VALUE_KEYS.CONDUCTIVITY: float,
    VALUE_KEYS.PRESSURE: float,
    VALUE_KEYS.SALINITY: float,
}
STRING_CONVERSIONS = {
    VALUE_KEYS.TEMPERATURE: '{0:.4f}',
    VALUE_KEYS.CONDUCTIVITY: '{0:.5f}',
    VALUE_KEYS.PRESSURE: '{0:.3f}',
    VALUE_KEYS.SALINITY: '{0:.4f}',
}
SAMPLE = namedtuple('SAMPLE', DATA_KEYS)


def query_samples(serial, device_id, samples=6):
    raw = serial_request(
        serial, '#{0}DN{1}'.format(device_id, samples), REMOTE_RESPONSE_END, timeout=10
    )

    return raw


def query_status(serial, device_id):
    raw = serial_request(
        serial, '#{0}GetSD'.format(device_id), REMOTE_RESPONSE_END, timeout=10
    )

    return raw


def parse_samples(device_id, raw):
    pattern = (
        re.escape('<RemoteReply>')
        + '(?P<data>.*)'
        + re.escape('<Executed/>\r\n')
        + re.escape('</RemoteReply>\r\n')
    )
    match = re.search(pattern, raw, flags=re.DOTALL)

    header, values = match.group('data').strip().split('\r\n\r\n')
    header = dict([el.strip() for el in row.split('=')] for row in header.split('\r\n'))
    values = [[el.strip() for el in row.split(',')] for row in values.split('\r\n')]
    samples = [
        SAMPLE(
            TIMESTAMP=datetime.strptime(' '.join(row[4:-1]), '%d %b %Y %H:%M:%S'),
            DEVICE_ID=device_id,
            **dict(
                (key, VALUE_CONVERSIONS[key](row[i]))
                for i, key in enumerate(VALUE_KEYS)
            )
        )
        for row in values
    ]

    return samples


def parse_status(raw):
    pattern = (
        re.escape('<RemoteReply>')
        + re.escape('<StatusData')
        + r".*SerialNumber='(?P<serial>\d+)'"
        + re.escape('>')
        + re.escape('<DateTime>')
        + '(?P<DateTime>.*)'
        + re.escape('</DateTime>')
        + re.escape('<vMain>')
        + '(?P<vMain>.*)'
        + re.escape('</vMain>')
        + re.escape('<vLith>')
        + '(?P<vLith>.*)'
        + re.escape('</vLith>')
        + re.escape('<Executed/>\r\n</RemoteReply>')
    )
    match = re.search(pattern, raw)

    return match.groupdict()


def get_recent_samples(device_ids, n=6):
    samples = []
    with imm_components():
        with active_line() as serial:
            for device_id in device_ids:
                raw = query_samples(serial, device_id, n)
                samples.extend(parse_samples(device_id, raw))

    return samples


def get_averaged_samples(device_ids, n=6):
    samples = get_recent_samples(device_ids, n)
    averaged_samples = []

    for device_id in device_ids:
        device_samples = [sample for sample in samples if sample.DEVICE_ID == device_id]
        timestamp = datetime.fromtimestamp(
            sum(time.mktime(sample.TIMESTAMP.timetuple()) for sample in samples) / n
        )
        averaged = SAMPLE(
            TIMESTAMP=timestamp,
            DEVICE_ID=device_id,
            **dict(
                (key, sum(getattr(sample, key) for sample in device_samples) / float(n))
                for key in VALUE_KEYS
            )
        )

        averaged_samples.append(averaged)

    return averaged_samples


def serialize(sample):
    serialized = SEP.join(
        [serialize_datetime(sample.TIMESTAMP), sample.DEVICE_ID]
        + [STRING_CONVERSIONS[key].format(getattr(sample, key)) for key in VALUE_KEYS]
    )

    return serialized


def deserialize(serialized):
    split = serialized.split(SEP)

    deserialized = SAMPLE(
        TIMESTAMP=deserialize_datetime(split[0]),
        DEVICE_ID=split[1],
        **dict(
            (key, VALUE_CONVERSIONS[key](split[2 + i]))
            for i, key in enumerate(VALUE_KEYS)
        )
    )

    return deserialized


def print_samples(samples):
    print(', '.join(DATA_KEYS))
    print('-' * 80)
    for sample in samples:
        print(serialize(sample).replace(SEP, ', '))


def start(device_ids):
    with imm_components():
        with active_line() as serial:
            for device_id in device_ids:
                expected_response = 'start logging.*' + REMOTE_RESPONSE_END
                serial_request(
                    serial,
                    '#{0}StartNow'.format(device_id),
                    expected_response,
                    timeout=10,
                )


def stop(device_ids):
    with imm_components():
        with active_line() as serial:
            for device_id in device_ids:
                expected_response = 'logging stopped.*' + REMOTE_RESPONSE_END
                serial_request(
                    serial, '#{0}Stop'.format(device_id), expected_response, timeout=10,
                )


def set_interval(device_ids, interval):
    with imm_components():
        with active_line() as serial:
            for device_id in device_ids:
                serial_request(
                    serial,
                    '#{0}SampleInterval={1}'.format(device_id, interval),
                    REMOTE_RESPONSE_END,
                    timeout=10,
                )


@fail_gracefully
@log_execution
def execute():
    samples = get_averaged_samples(UNIT.SEABIRD_IDS)
    for sample in samples:
        serialized = serialize(sample)
        log_data(serialized, DATA_TAGS.SBD)
        queue_sbd(DATA_TAGS.SBD, serialized)


if __name__ == '__main__':
    execute()