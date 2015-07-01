
import time
import random
import string
import random

INI_SAFE_CHARCTERS = "!@$%^&*()_-+[]\/?.>,<"

def create_salt(size=68, chars=(string.ascii_letters + 
                                string.digits + INI_SAFE_CHARCTERS)):

    return ''.join(random.SystemRandom().choice(chars) for _ in range(size))
