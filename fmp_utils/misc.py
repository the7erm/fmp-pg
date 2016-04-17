
from time import sleep
from sqlalchemy.exc import InvalidRequestError
import traceback

def to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (str,)):
        value = value.lower()
        if value in ('t','true','1','on'):
            return True
        if not value or value in('f', '0', 'false', 'off', 'null',
                                 'undefined', ''):
            return False

    return bool(value)

def to_int(value):
    if isinstance(value, int):
        return value
    if not value:
        return 0
    try:
        value = int(value)
    except Exception as e:
        value = 0
    return value


def session_add(session, obj, commit=False, close=False):
    added = False
    try_cnt = 0
    while not added:
        if try_cnt > 0:
            print("try_cnt:",try_cnt)
        try:
            session.add(obj)
            added = True
            if try_cnt:
                print("Finally added obj", "-GOOD-")
        except InvalidRequestError as e:
            added = False
            traceback.print_exc()
            print("session_add InvalidRequestError:", e)
            sleep(0.1)
        try_cnt = try_cnt + 1

    if commit:
        session.commit()
    if close:
        session.close()