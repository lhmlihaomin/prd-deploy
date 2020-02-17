"""
OpenFalcon related actions.
"""

import json
import requests
import re


def get_openfalcon_host_name(instance_name, private_ip_address):
    """Make openfalcon host name w/ 2-letter region"""
    region_dict = {
        'aps1': 'ap',
        'eu': 'eu',
        'euw1': 'eu',
        'use1': 'us',
        'us': 'us',
        'cn': 'cn',
        'cn1': 'cn',
        'cnn1': 'cn',
        'cnnw1': 'cn',
    }
    #    env           module          version          region        az           number
    p = r"([adefmprtuv]+)-([a-zA-Z0-9_]+)-([\d\._a-zA-Z]+)-([a-zA-Z\d]+)-([\da-zA-Z])-(\d+)"
    m = re.match(p, instance_name)
    region_code = m.groups()[3]
    host = '/'.join([
        instance_name,
        region_dict[region_code],
        private_ip_address
    ])
    return host


def openfalcon_login(login_url, 
                     username, 
                     password, 
                     cert_file=None, 
                     cert_key=None, 
                     verify=True):
    """Login using credentials and return a session."""
    session = requests.Session()
    if login_url.startswith("https"):
        # Use HTTPS, set client certificate:
        if cert_file is None or cert_key is None:
            raise Exception("Client certificate can't be None.")
        session.cert = (cert_file, cert_key)
        if not verify:
            session.verify = False
    data_login = {
        'callback': '',
        'ldap': '0',
        'name': username,
        'password': password,
        'sig': ''
    }
    response = session.post(login_url, data_login)
    body = json.loads(response.text)
    if body.has_key(u'msg') and body[u'msg'] == "":
        return session
    raise Exception("Login failed.")


def openfalcon_logout(session, logout_url):
    """Visit logout url to log out session."""
    response = session.get(logout_url)
    return response


def openfalcon_enable(session, switch_url, ec2_instances):
    """Use authenticated session to enable alarms."""
    hosts = [
                get_openfalcon_host_name(ec2_instance.name, ec2_instance.private_ip_address) 
                for ec2_instance in ec2_instances
            ]
    data = {
        'category': 'enable',
        'hosts[]': hosts
    }
    response = session.post(switch_url, data)
    return response


def openfalcon_disable(session, switch_url, ec2_instances):
    """Use authenticated session to disable alarms."""
    hosts = [
                get_openfalcon_host_name(ec2_instance.name, ec2_instance.private_ip_address) 
                for ec2_instance in ec2_instances
            ]
    data = {
        'category': 'disable',
        'hosts[]': hosts
    }
    response = session.post(switch_url, data)
    return response

