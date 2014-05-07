from nose.tools import assert_equal, assert_less, assert_raises
from lib import Config


class TestConfig(object):
    def setup(self):
        self.config = Config('tests/config.yml')

    def test_new_config(self):
        assert_equal(self.config['key'], 'value')

    def test_unknown_property(self):
        with assert_raises(KeyError):
            self.config['unknown_key']

    def test_nested_property(self):
        assert_equal(self.config['group']['key'], 'value')
