
import unittest
from unittest.mock import MagicMock, Mock
from kubernetes.client import V1Container, V1ResourceRequirements, V1PodList, V1PodStatus
from kubespawner.objects import make_pod

from src.resources_validation import ResourcesValidation
from src.primehub_utils import *

_TEST_GROUP = "PrimeHub-unit-test"
_TEST_USER = "Test-user"

class ResourcesValidationMock(ResourcesValidation):
    def __init__(self, request_info, pods=[], group_info={}, mock=False):
        super().__init__(request_info, mock=mock)

        self.namespace = 'mock'
        self.kube_api = Mock()

        pod_list = V1PodList(items=pods)
        self.kube_api.list_namespaced_pod.return_value = pod_list

        self.fetch_group_info = Mock(return_value=group_info)

# {cpu, gpu, memory} user
# {cpu, gpu, memory} user, group
# resource_type -> 'cpu', 'gpu', 'memory'
def resource_parameters_generator(resource_type, user, group):
    request = {
        'cpu': None,
        'gpu': None,
        'memory': 1024 * 1024 * 300  # 300Mi
    }
    quota = {
        'cpu': None,
        'gpu': None,
        'memory': None
    }
    usage = {
        'cpu': None,
        'gpu': None,
        'memory': None
    }

    if user:  # request should grater than quota
        request[resource_type] = 2
        quota['name'] = _TEST_USER
        quota[resource_type] = 1

    if group:
        request[resource_type] = 2
        quota['name'] = _TEST_GROUP
        quota[resource_type] = 3
        usage[resource_type] = 3

    return request, quota, usage

def pod(containers, add_user=False):
    p = make_pod(name='test',
                 image='image',
                 cmd=['jupyterhub-singleuser'],
                 port=8888,
                 image_pull_policy='IfNotPresent'
                 )
    p.metadata.labels['primehub.io/group'] = escape_to_primehub_label(_TEST_GROUP)
    if add_user:
        p.metadata.labels['primehub.io/user'] = escape_to_primehub_label(_TEST_USER)
    p.spec.containers = containers
    p.status = V1PodStatus()
    p.status.phase = "Pending"
    return p

def none_resource_container():
    c = V1Container(name='container')
    c.resources = V1ResourceRequirements()
    return c

def resource_container(cpu, gpu, memory):
    c = V1Container(name='container')
    settings = {
        "cpu": str(cpu),
        "memory": str(memory),
        "nvidia.com/gpu": str(gpu)

    }
    c.resources = V1ResourceRequirements(limits=settings, requests=settings)
    return c

class objdict(dict):
    def __getattr__(self, name):
        if name in self:
            return self[name]
        else:
            raise AttributeError("No such attribute: " + name)

    def __setattr__(self, name, value):
        self[name] = value

    def __delattr__(self, name):
        if name in self:
            del self[name]
        else:
            raise AttributeError("No such attribute: " + name)

class TestValidateResources(unittest.TestCase):
    def test_user_quota_fail(self):
        for resource_type in ['cpu', 'gpu', 'memory']:
            rv = ResourcesValidationMock({}, mock=True)
            self.assertFalse(rv.validate_resources("USER",
                *resource_parameters_generator(resource_type, True, False)))
            self.assertTrue(rv.last_error_message.startswith(
                'User {} exceeded {}'.format(_TEST_USER, resource_type)))

    def test_group_quota_fail(self):
        for resource_type in ['cpu', 'gpu', 'memory']:
            rv = ResourcesValidationMock({}, mock=True)
            self.assertFalse(rv.validate_resources("GROUP",
                *resource_parameters_generator(resource_type, False, True)))
            self.assertTrue(rv.last_error_message.startswith(
                'Group {} exceeded {}'.format(_TEST_GROUP, resource_type)))

    def test_convert_cpu_values_to_float(self):
        rv = ResourcesValidationMock({}, mock=True)
        self.assertEqual(0.5, convert_cpu_values_to_float('500m'))
        self.assertEqual(1.5, convert_cpu_values_to_float('1500m'))
        self.assertEqual(1, convert_cpu_values_to_float('1'))

    def test_resource_none_resources_container(self):
        pods = [pod([none_resource_container()], add_user=True)]
        rv = ResourcesValidationMock({}, pods=pods, mock=True)
        self.assertEqual((0, 0, 0), rv.get_group_resource_usage(dict(name=_TEST_GROUP)))
        self.assertEqual((0, 0, 0), rv.get_user_resource_usage_in_group(dict(name=_TEST_GROUP), dict(name=_TEST_USER)))

    def test_resource_normal_container(self):
        pods = [pod([resource_container(1, 0, 1024 ** 3)], add_user=True)]
        rv = ResourcesValidationMock({}, pods=pods, mock=True)
        self.assertEqual((1, 0, 1024 ** 3), rv.get_group_resource_usage(dict(name=_TEST_GROUP)))
        self.assertEqual((1, 0, 1024 ** 3), rv.get_user_resource_usage_in_group(dict(name=_TEST_GROUP), dict(name=_TEST_USER)))

    def test_resource_normal_with_kernel_gateway_container(self):
        pods = [pod([none_resource_container(), resource_container(1, 1, 1024 ** 3)], add_user=True)]
        rv = ResourcesValidationMock({}, pods=pods, mock=True)
        self.assertEqual((1, 1, 1024 ** 3), rv.get_group_resource_usage(dict(name=_TEST_GROUP)))
        self.assertEqual((1, 1, 1024 ** 3), rv.get_user_resource_usage_in_group(dict(name=_TEST_GROUP), dict(name=_TEST_USER)))

    def test_resource_with_literal(self):
        pods = [pod([none_resource_container(), resource_container('1000m', 1, '2G')], add_user=True)]
        rv = ResourcesValidationMock({}, pods=pods, mock=True)
        self.assertEqual((1, 1, 1024 ** 3 * 2), rv.get_group_resource_usage(dict(name=_TEST_GROUP)))
        self.assertEqual((1, 1, 1024 ** 3 * 2), rv.get_user_resource_usage_in_group(dict(name=_TEST_GROUP), dict(name=_TEST_USER)))

    def test_user_resource_usage(self):
        pods = [pod([resource_container('500m', 0, 0), resource_container('1000m', 1, '2G')], add_user=True)]
        rv = ResourcesValidationMock({}, pods=pods, mock=True)
        self.assertEqual((1.5, 1, 1024 ** 3 * 2), rv.get_group_resource_usage(dict(name=_TEST_USER)))
        self.assertEqual((1.5, 1, 1024 ** 3 * 2), rv.get_user_resource_usage_in_group(dict(name=_TEST_GROUP), dict(name=_TEST_USER)))

    def test_failed_qa_1(self):
        request = {
            'cpu': 0.5,
            'gpu': None,
            'memory': 1024 * 1024 * 300  # 300Mi
        }
        quota = {
            'name': _TEST_USER,
            'cpu': 0.5,
            'gpu': None,
            'memory': None
        }
        usage = {
            'cpu': None,
            'gpu': None,
            'memory': None
        }
        rv = ResourcesValidationMock({}, mock=True)
        self.assertTrue(rv.validate_resources("USER", request, quota, usage))

        quota = {
            'name': _TEST_GROUP,
            'cpu': 0.5,
            'gpu': None,
            'memory': None
        }
        usage = {
            'cpu': 0.5,
            'gpu': None,
            'memory': None
        }

        resource_type = 'cpu'
        self.assertFalse(rv.validate_resources("GROUP", request, quota, usage))
        self.assertTrue(rv.last_error_message.startswith(
            'Group {} exceeded {}'.format(_TEST_GROUP, resource_type)))

    def test_validate_resources_with_cpu_conversion(self):
        request_info = {
            'request': {
                'object': {
                    'spec': {
                        'containers': [
                            {
                                'resources': {
                                    'limits': {
                                        'cpu': '500m'
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        group_quota = {
            'name': _TEST_GROUP,
            'cpu': 1,
            'gpu': None,
            'memory': None
        }
        user_quota = {
            'name': _TEST_USER,
            'cpu': 1,
            'gpu': None,
            'memory': None
        }

        resource_type = 'cpu'
        pods = [pod([resource_container('510m', 0, 1024 ** 3)])]
        rv = ResourcesValidationMock({}, pods=pods, mock=True)

        cpu_request, gpu_request, memory_request = rv.get_request_resources(request_info)
        request = dict(cpu=cpu_request, gpu=gpu_request, memory=memory_request)

        group_cpu_usage, group_gpu_usage, group_memory_usage = rv.get_group_resource_usage(dict(name=_TEST_GROUP))
        user_cpu_usage, user_gpu_usage, user_memory_usage = rv.get_user_resource_usage_in_group(dict(name=_TEST_GROUP), dict(name=_TEST_USER))
        group_usage = {
            'cpu': group_cpu_usage,
            'gpu': group_gpu_usage,
            'memory': group_memory_usage
        }
        user_usage = {
            'cpu': user_cpu_usage,
            'gpu': user_gpu_usage,
            'memory': user_memory_usage
        }

        self.assertFalse(rv.validate_resources("USER", request, user_quota, user_usage))
        self.assertFalse(rv.validate_resources("GROUP", request, group_quota, group_usage))
        self.assertTrue(rv.last_error_message.startswith(
            'Group {} exceeded {}'.format(_TEST_GROUP, resource_type)))

    def test_validate(self):
        request_info = {
            'request': {
                'object': {
                    'metadata': {
                        'labels': {
                            'primehub.io/group': escape_to_primehub_label(_TEST_GROUP),
                            'primehub.io/user': escape_to_primehub_label(_TEST_USER)
                        }
                    },
                    'spec': {
                        'containers': [
                            {
                                'resources': {
                                    'limits': {
                                        'cpu': '500m'
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }
        pods = [pod([resource_container('510m', 0, 1024 ** 3)])]
        group_info = {
            'data': {
                'groups': [
                    {
                        'name': _TEST_GROUP,
                        'projectQuotaCpu': 1,
                        'projectQuotaGpu': None,
                        'projectQuotaMemory': None,
                        'quotaCpu': 1,
                        'quotaGpu': None,
                        'quotaMemory': None
                    }
                ]
            }
        }

        rv = ResourcesValidationMock(request_info, pods=pods, group_info=group_info, mock=True)
        self.assertFalse(rv.validate())
        self.assertTrue(rv.last_error_message.startswith(
            'User {} exceeded {}'.format(_TEST_USER, 'cpu')))