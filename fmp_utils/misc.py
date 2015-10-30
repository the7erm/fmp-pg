
def to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, (str,)):
        value = value.lower()
        if value in ('t','true','1','on'):
            return True
        if not value or value in('f', '0', 'false', 'off', 'null',
                                 'undefined'):
            return False
    return bool(value)