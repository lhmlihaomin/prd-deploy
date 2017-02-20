#!/usr/bin/python

import os
import sys

import django
import paramiko

from ec2mgr.models import EC2Instance

class SshHandler(object):
    """Handles SSH related operations"""
    def __init__(self, ec2instance, pem_dir):
        self.ec2instance = ec2instance
        self.pem_dir = pem_dir
        self.key_filename = os.path.sep.join([
            pem_dir,
            self.ec2instance.key_pair+'.pem'
        ])
        self.host = self.ec2instance.private_ip_address
        self.username = self.ec2instance.username
        self._init_sshclient()

    def _init_sshclient(self):
        self.client = paramiko.client.SSHClient()
        self.client.load_system_host_keys()
        auto_add_policy = paramiko.client.AutoAddPolicy()
        self.client.set_missing_host_key_policy(auto_add_policy)
        self.connected = False

    def _connect_sshclient(self):
        if not self.connected:
            self.client.connect(
                self.host,
                username=self.username,
                key_filename=self.key_filename,
                timeout=10)
            self.connected = True

    def run(self, cmd):
        """execute a command"""
        self._connect_sshclient()
        stdin, stdout, stderr = self.client.exec_command(cmd)
        return (
            stdout.channel.recv_exit_status(),
            stdout.read(),
            stderr.read()
        )

    def close(self):
        if self.connected:
            self.client.close()
            self.connected = False

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

