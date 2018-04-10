#!/usr/bin/python
"""
Simple example of how to use the API interface to create a new update plan.
"""

import requests

s = requests.session()
s.headers.update({
    'Authorization': 'Token 2195fda909b9e6ef24ad6b06985ef38c566751de'
})

url = "http://localhost:8000/update/api/new_updateplan/"

data = {
    "project_name": u"deleteme",
    "project_code": "DELETEME",
    "managers": [
        "lihaomin"
    ],
    "update_steps": [
        {
            "profile": "cn-alpha",
            "region": "cn-north-1",
            "module": "moduleA",
            "update_version": "1.0.1",
            "current_version": "1.0.1",
            "update_time": "2018-01-08 12:00:00",
            "service_type": "tomcat",
            "load_balancer_names": "my_load_balancer1,my_load_balancer1",
            "count": 3,
            "config": {
                "Key1": "Value1",
                "Key2": "Value2"
            }
        },
        {
            "profile": "cn-alpha",
            "region": "cn-north-1",
            "module": "moduleB",
            "current_version": "1.0.2",
            "update_version": "1.0.2",
            "update_time": "2018-01-08 12:00:00",
            "service_type": "java",
            "load_balancer_names": "",
            "count": 2,
            "config": {
                "a": 1,
                "b": 2
            }
        }
    ],
}

resp = s.post(url, json=data)
