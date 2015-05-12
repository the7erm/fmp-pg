import os

config_dir = os.path.expanduser("~/.fmp")
if not os.path.exists(config_dir):
    os.makedirs(config_dir)
