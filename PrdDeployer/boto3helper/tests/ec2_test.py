import unittest
import boto3

from ec2 import to_name_dict, get_instance_names, get_module_instances

class DummyEC2Instance(object):
    """A dummy class that pretends to be boto3.ec2.Instance"""
    def __init__(self, name, id, private_ip_address):
        self.id = id
        self.private_ip_address = private_ip_address
        self.tags = [
            {
                'Key': 'Name',
                'Value': name,
            },
            {
                'Key': 'Category',
                'Value': 'test',
            },
            {
                'Key': 'Product',
                'Value': 'cloud-basic',
            },
        ]


class EC2TestCase(unittest.TestCase):
    def setUp(self):
        self.profile = "cn-prd"
        self.region = "cn-north-1"
        self.region_code = 'cn1'
        self.boto3_session = boto3.Session(profile_name=self.profile,
                                           region_name=self.region)
        self.ec2res = self.boto3_session.resource('ec2')
        self.dummy_env = 'test'
        self.dummy_instances_info = [
            {'id': 'i-00000000', 'name': 'test-mod-1.0.0-cn1-a-0', 'ip': '192.168.100.0'},
            {'id': 'i-22222222', 'name': 'test-mod-1.0.0-cn1-a-10', 'ip': '192.168.100.10'},
            {'id': 'i-11111111', 'name': 'test-mod-1.0.0-cn1-a-1', 'ip': '192.168.100.1'},
        ]
        self.dummy_instances = []
        for info in self.dummy_instances_info:
            self.dummy_instances.append(DummyEC2Instance(
                info['name'],
                info['id'],
                info['ip'],
            ))


    def test_to_name_dict(self):
        d = to_name_dict(self.dummy_instances)
        for name in d:
            for info in self.dummy_instances_info:
                if name == info['name']:
                    self.assertEqual(d[name].id, info['id'])
                    break


    def test_get_instance_names(self):
        names = get_instance_names(self.dummy_instances)
        self.assertEqual(names, [
            'test-mod-1.0.0-cn1-a-0',
            'test-mod-1.0.0-cn1-a-1',
            'test-mod-1.0.0-cn1-a-10',
        ])


    def test_get_module_instances(self):
        module = 'connector'
        version = '2.0.1'
        instances = get_module_instances(self.ec2res, module, version)
        self.assertEqual(len(instances), 60)


    def test_complex(self):
        module = 'connector'
        version = '2.0.1'
        instances = get_module_instances(self.ec2res, module, version)
        names = get_instance_names(instances)
        print(names)


if __name__ == "__main__":
    unittest.main()
