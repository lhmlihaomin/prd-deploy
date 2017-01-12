"""
Helper functions to quickly extract wanted value(s) from boto3's default 
tags structure.
e.g. 
# Original format:
[
    {
        "Key": "tag1",
        "Value": "value1",
    },
    {
        "Key": "tag2",
        "Value": "value2",
    },
    ...
]
# -- becomes -->
{
    "tag1": "value1",
    "tag2": "value2",
    ...
}

Author: lihaomin@tp-link.com.cn
Copyright: whatever fucks.
"""

def to_dict(tags):
    """Convert boto3's complex tags format to a simple dict."""
    ret = {}
    for tag in tags:
        ret.update({
            tag['Key']: tag['Value']
        })
    return ret


def get_value_by_key(tags, key, case_sensitive=True):
    """Find the value for the given key."""
    if case_sensitive:
        for tag in tags:
            if tag['Key'] == key:
                return tag['Value']
    else:
        key = key.lower()
        for tag in tags:
            if tag['Key'].lower() == key:
                return tag['Value']
    return None


def get_name(tags):
    """Find the tag with key 'Name/name'."""
    for tag in tags:
        if tag['Key'].lower() == 'name':
            return tag['Value']
    return None


def get_resource_name(res):
    """Find the name tag of a resource instance."""
    return get_name(res.tags)
    