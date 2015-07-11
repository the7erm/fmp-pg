
from datetime import datetime
import pytz
import arrow

def utcnow():
    return datetime.utcnow().replace(tzinfo=pytz.utc, microsecond=0)

def ensure_tzinfo(value):
    if value.tzinfo:
        return value
    return value.replace(tzinfo=pytz.utc)

def convert_int_to_dt(value):
    return convert_to_dt(value)

def convert_str_to_dt(value):
    return convert_to_dt(value)

def convert_float_to_dt(value):
    return convert_to_dt(value)

def convert_to_dt(value):
    arw = arrow.get(value)
    dt = arw.datetime
    return ensure_tzinfo(dt)
