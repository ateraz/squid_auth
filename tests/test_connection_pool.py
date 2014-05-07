from nose.tools import assert_equal, assert_less, assert_raises
from lib import ConnnectionPool


class TestConnectionPool(object):
    def setup(self):
        self.config = {host: 'host', name: 'name', user: 'user', 
        			   passwd: 'pass'}

    def test_new_pool(self):
        pool = ConnnectionPool(self.config)
        assert_equal

    def test_unknown_property(self):
        with assert_raises(KeyError):
            self.config['unknown_key']

    def test_nested_property(self):
        assert_equal(self.config['group']['key'], 'value')
