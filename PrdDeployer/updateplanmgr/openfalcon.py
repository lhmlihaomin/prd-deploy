"""
OpenFalcon related actions.
"""

import requests
import json
import re


def get_falcon_host_name(ec2_instance):
    region_dict = {
        'aps1': 'ap',
        'eu': 'eu',
        'euw1': 'eu',
        'use1': 'us',
        'us': 'us',
        'cn': 'cn',
        'cn1': 'cn',
        'cnn1': 'cn',
    }
    #    env           module          version          region        az           number
    p = r"([adeprtuv]+)-([a-zA-Z0-9_]+)-([\d\._a-zA-Z]+)-([a-zA-Z\d]+)-([\da-zA-Z])-(\d+)"
    m = re.match(p, ec2_instance.name)
    region_code = m.groups()[3]
    host = '/'.join([
        ec2_instance.name,
        region_dict[region_code],
        ec2_instance.private_ip_address
    ])
    return host


def openfalcon_login(login_url, username, password, cert_file=None, cert_key=None, verify=True):
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
    if body.has_key(u'data') and body.has_key(u'msg'):
        if body[u'data'] == u'' and body[u'msg'] == u'':
            return session
    print(body)
    raise Exception("Login failed.")


def openfalcon_enable(session, switch_url, ec2_instances):
    hosts = [
                get_falcon_host_name(ec2_instance) 
                for ec2_instance in ec2_instances
            ]
    data = {
        'category': 'enable',
        'hosts': ',,'.join(hosts)
    }
    response = session.post(switch_url, data)
    return response


def openfalcon_disable(session, switch_url, ec2_instances):
    hosts = [
                get_falcon_host_name(ec2_instance) 
                for ec2_instance in ec2_instances
            ]
    data = {
        'category': 'disable',
        'hosts': ',,'.join(hosts)
    }
    response = session.post(switch_url, data)
    return response


def main():
    login_url = "http://ec2-54-223-180-212.cn-north-1.compute.amazonaws.com.cn:12345/auth/login"
    switch_url = "http://ec2-54-223-180-212.cn-north-1.compute.amazonaws.com.cn:12345/alarm/switch"
    username = "autorepair"
    password = "autorepair"
    session = openfalcon_login(login_url, username, password)
    return session


if __name__ == "__main__":
    session = main()
