from twisted.trial import unittest
from lib import Config


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.config = Config('../tests/config.yml')

    def test_new_config(self):
        self.assertEqual(self.config['key'], 'value')

    def test_unknown_property(self):
        self.assertRaises(KeyError, self.config.__getitem__, 'unknown_key')

    def test_nested_property(self):
        self.assertEqual(self.config['group']['key'], 'value')
