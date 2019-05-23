"""
Helper functions to achieve certain EC2 related tasks faster.
Functions return ec2.Instance instances (Errrrh!) instead of boto3 iterators.

list of tasks:
1. get instances of a given module & version;
2. get instances that match certain filters;

Author: lihaomin@tp-link.com.cn
Copyright: whatever fucks.
"""
import re

from .tags import get_resource_name


def version_cmp(ver1, ver2):
    """Compare version numbers."""
    arr_ver1 = ver1.split('.')
    arr_ver2 = ver2.split('.')
    len1 = len(arr_ver1)
    len2 = len(arr_ver2)
    # number of comparisons to make:
    cmp_count = min(len1, len2)
    i = 0
    # compare each segment:
    while i < cmp_count:
        try:
            m = int(arr_ver1[i])
        except:
            raise Exception(
                "Cannot parse segment as integer: %s."%(arr_ver1[i])
            )
        try:
            n = int(arr_ver2[i])
        except:
            raise Exception(
                "Cannot parse segment as integer: %s."%(arr_ver2[i])
            )
        if m < n:
            return -1
        if m > n:
            return 1
        i += 1
    # if segments are the same, the longer one wins:
    if len1 < len2:
        return -1
    if len1 > len2:
        return 1
    # otherwise return equal:
    return 0


def name_cmp(x, y):
    """Compare instance names.
    
    For modules with +10 instances, string length needs to be considered, 
    otherwise 'xxx-9' will be greater than 'xxx-10'."""
    len_x = len(x)
    len_y = len(y)
    if len_x < len_y:
        return -1
    if len_x > len_y:
        return 1
    if x < y:
        return -1
    if x > y:
        return 1
    return 0


def to_name_dict(instances):
    """Convert instances to a dictionary with their names as keys."""
    ret = {}
    for instance in instances:
        name = get_resource_name(instance)
        if name is None:
            raise Exception("Instance %s has no 'Name' tag."%(instance.id,))
        else:
            ret.update({name: instance})
    return ret


def get_instance_names(instances):
    """Return a sorted list of instance names."""
    names = [get_resource_name(instance) for instance in instances]
    names.sort(cmp=name_cmp)
    return names


def get_instances_by_filters(ec2res, filters):
    """Get instances by simple dict filters."""
    boto3filters = []
    for filter_name in filters:
        if type(filters[filter_name]) in (str, int, float, unicode):
            filter_values = [filters[filter_name],]
        else:
            filter_values = filters[filter_name]
        boto3filters.append({
            'Name': filter_name,
            'Values': filter_values
        })
    return ec2res.instances.filter(Filters=boto3filters)


def get_module_instances(ec2res, module, version):
    """Get instances with names contain '*-<module>-<version>-*'"""
    filters = {
        'tag:Name': "*-%s-%s-*"%(module, version),
        'instance-state-name': ['running', 'stopped', 'pending', 'stopping', 'shutting-down']
    }
    instances = []
    for instance in get_instances_by_filters(ec2res, filters):
        instances.append(instance)
    try:
        instances.sort(cmp=name_cmp, key=lambda x: get_resource_name(x))
    except Exception as ex:
        raise ex
    return instances


def get_instance_module_version(instance):
    #    env           module          version          region        az           number
    p = "([adeprtuv]+)-([a-zA-Z0-9_]+)-([\d\._a-zA-Z]+)-([a-zA-Z\d]+)-([\da-zA-Z])-(\d+)"
    name = get_resource_name(instance)
    if name is not None:
        m = re.match(p, name)
        if m is not None:
            module = m.groups()[1]
            version = m.groups()[2]
            return (module, version)
        else:
            raise Exception("Invalid instance name: %s"%(name,))
    else:
        raise Exception("Instance name tag not found: %s"%(str(instance.tags,)))
