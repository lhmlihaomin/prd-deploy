import unittest
from tags import to_dict, get_value_by_key, get_name, \
    get_resource_name
import copy

class DummyResource(object):
    """A dummy resource class that pretends to be an AWS Resource"""
    def __init__(self, tags):
        self.id = "dummy-abcd1234"
        self.tags = tags


class TagsTestCase(unittest.TestCase):
    def setUp(self):
        # a list of tags 
        self.tags_no_name = [
            {
                'Key': 'a',
                'Value': '1'
            },
            {
                'Key': 'b',
                'Value': '2'
            },
            
        ]

        self.tags = copy.copy(self.tags_no_name)
        self.tags.append({
            'Key': 'Name',
            'Value': 'John'
        })

    def test_to_dict(self):
        self.assertEqual(to_dict(self.tags_no_name), {'a':'1', 'b':'2'})

    def test_get_value_by_key(self):
        # test basic functionality:
        self.assertEqual(get_value_by_key(self.tags, 'a'), '1')
        self.assertEqual(get_value_by_key(self.tags, 'b'), '2')
        # test case sensitivity:
        self.assertIsNone(get_value_by_key(self.tags, 'A', case_sensitive=True))
        self.assertEqual(get_value_by_key(self.tags, 'A', case_sensitive=False), '1')

    def test_get_name(self):
        self.assertEqual(get_name(self.tags), 'John')
        self.assertIsNone(get_name(self.tags_no_name))

    def test_get_resource_name(self):
        res = DummyResource(self.tags)
        self.assertEqual(get_resource_name(res), 'John')
        res.tags = self.tags_no_name
        self.assertIsNone(get_resource_name(res))


if __name__ == "__main__":
    unittest.main()
    