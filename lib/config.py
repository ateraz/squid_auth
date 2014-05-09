# -*- test-case-name: tests.test_config -*-
"""Stored in file application config"""

import yaml


class Config(dict):
    """Converts config from file content to dict."""
    def __init__(self, config_path):
    	# Opening file synchronously.
    	# Application shouldn't do anything before config is read.
        dict.__init__(self, yaml.load(file(config_path)))
