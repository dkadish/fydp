import unittest
from options import Config

class TestOptionsParser(unittest.TestCase):
    """Unit tests for the JSON options parser."""

    def test_load_options(self):
        """Test populating system options from a user-supplied config file."""
        opts = Config('test/data/test_config.json')
        self.assertEqual(opts.proxy['debugMode'], True)
        self.assertEqual(opts.proxy['loggingLevel'], 'DEBUG')

    def test_set_defaults(self):
        """Test preservation of default options when overriding configuration isn't provided."""
        opts = Config('test/data/test_config.json')
        self.assertEqual(opts.http['maxConnections'], 10)
        self.assertEqual(opts.http['port'], 1080)
