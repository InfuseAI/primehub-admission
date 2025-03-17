import json

from kubernetes import client, config
from loguru import logger
from tornado import httpclient

from primehub_admission.primehub_utils import *

GRAPHQL_LAUNCH_CONTEXT_QUERY = '''query ($id: ID!) {
                    system { defaultUserVolumeCapacity }
                    user (where: { id: $id }) { id username isAdmin volumeCapacity
                    groups { name
                            displayName
                            enabledSharedVolume
                            sharedVolumeCapacity
                            homeSymlink
                            launchGroupOnly
                            quotaCpu
                            quotaGpu
                            quotaMemory
                            userVolumeCapacity
                            projectQuotaCpu
                            projectQuotaGpu
                            projectQuotaMemory
                            instanceTypes { name displayName description spec global }
                            images { name displayName description spec global }
                            datasets { name displayName description spec global writable mountRoot homeSymlink launchGroupOnly }
                        }
                } }'''


class ResourcesValidation(object):

    def __init__(self, request_info, group_aggregation_key='primehub.io/group', group_aggregation_key_type='labels', user_aggregation_key='primehub.io/user', user_aggregation_key_type='labels', mock=False):
        self.request_info = request_info
        self.group_aggregation_key = group_aggregation_key
        self.group_aggregation_key_type = group_aggregation_key_type
        self.user_aggregation_key = user_aggregation_key
        self.user_aggregation_key_type = user_aggregation_key_type

        self.last_error_message = ''

        if mock is False:
            config.load_incluster_config()
            self.kube_api = client.CoreV1Api()
            self.namespace = self.request_info['request']['namespace']
            self.httpclient = httpclient.HTTPClient()
            self.admin_endpoint = os.environ.get('GRAPHQL_ENDPOINT', '')
            self.admin_secret = os.environ.get('GRAPHQL_SHARED_SECRET', '')

    def fetch_all_users(self):
        query = '''query {
            users {
                id
                username
            }
        }'''
        headers = {'Content-Type': 'application/json',
                    'Authorization': 'Bearer %s' % self.admin_secret}
        data = {'query': query}
        response = self.httpclient.fetch(self.admin_endpoint,
                                        method='POST',
                                        headers=headers,
                                        body=json.dumps(data))
        result = json.loads(response.body.decode())
        return result

    def fetch_context(self, user_id):
        headers = {'Content-Type': 'application/json',
                    'Authorization': 'Bearer %s' % self.admin_secret}
        data = {'query': GRAPHQL_LAUNCH_CONTEXT_QUERY, 'variables': {'id': user_id}}
        response = self.httpclient.fetch(self.admin_endpoint,
                                        method='POST',
                                        headers=headers,
                                        body=json.dumps(data))
        result = json.loads(response.body.decode())
        return result

    def fetch_group_info(self, group):
        query = '''query ($name: String!) {
                    groups(where: { name_contains: $name }) {
                        name
                        displayName
                        enabledSharedVolume
                        sharedVolumeCapacity
                        homeSymlink
                        launchGroupOnly
                        quotaCpu
                        quotaGpu
                        quotaMemory
                        userVolumeCapacity
                        projectQuotaCpu
                        projectQuotaGpu
                        projectQuotaMemory
                        instanceTypes { name displayName description spec global }
                        images { name displayName description spec global }
                        datasets { name displayName description spec global writable mountRoot homeSymlink launchGroupOnly }
                    }
                }'''
        headers = {'Content-Type': 'application/json',
                    'Authorization': 'Bearer %s' % self.admin_secret}
        data = {'query': query, 'variables': {'name': group['name']}}
        response = self.httpclient.fetch(self.admin_endpoint,
                                        method='POST',
                                        headers=headers,
                                        body=json.dumps(data))
        result = json.loads(response.body.decode())
        return result

    def get_user_and_group_from_request_info(self):
        metadata = self.request_info['request']['object']['metadata']
        username = metadata.get(self.user_aggregation_key_type, {}).get(self.user_aggregation_key, '')
        group_name = metadata.get(self.group_aggregation_key_type, {}).get(self.group_aggregation_key, '')
        if self.user_aggregation_key_type == 'labels':
            username = unescape_primehub_label(username)
        if self.group_aggregation_key_type == 'labels':
            group_name = unescape_primehub_label(group_name)
        return ({'name': username}, {'name': group_name})

    def _get_gpu_resource_from_limits(self, limits):
        if 'nvidia.com/gpu' in limits:
            return limits['nvidia.com/gpu']
        if 'amd.com/gpu' in limits:
            return limits['amd.com/gpu']
        for k, v in limits.items():
            if k.startswith('gpu.intel.com/'):
                return v
        return 0

    def aggregate_resource_usage(self, containers, cpu, gpu, mem):
        for container in containers:
            if container.resources and container.resources.limits:
                cpu += float(convert_cpu_values_to_float(container.resources.limits.get('cpu', 0)))
                gpu += int(self._get_gpu_resource_from_limits(container.resources.limits))
                mem += int(convert_mem_resource_to_bytes(container.resources.limits.get('memory', 0)))
        return (cpu, gpu, mem)

    def get_group_resource_usage(self, group_info):
        cpu, gpu, mem = (0, 0, 0)
        containers = []
        escaped_group_name = escape_to_primehub_label(group_info['name'])
        label_selector="{}={}".format(self.group_aggregation_key, escaped_group_name)

        running_pods = self.kube_api.list_namespaced_pod(self.namespace, label_selector=label_selector, field_selector="status.phase=Running")
        pending_pods = self.kube_api.list_namespaced_pod(self.namespace, label_selector=label_selector, field_selector="status.phase=Pending")
        for pod in running_pods.items:
            containers.extend(pod.spec.containers)
        for pod in pending_pods.items:
            containers.extend(pod.spec.containers)

        cpu, gpu, mem = self.aggregate_resource_usage(containers, cpu, gpu, mem)
        return cpu, gpu, mem

    def get_user_resource_usage_in_group(self, group_info, user_info):
        cpu, gpu, mem = (0, 0, 0)
        containers = []
        if self.user_aggregation_key_type == 'labels':
            escaped_group_name = escape_to_primehub_label(group_info['name'])
            escaped_user_name = escape_to_primehub_label(user_info['name'])
            label_selector="{}={}, {}={}".format(self.group_aggregation_key, escaped_group_name, self.user_aggregation_key, escaped_user_name)

            running_pods = self.kube_api.list_namespaced_pod(self.namespace, label_selector=label_selector, field_selector="status.phase=Running")
            pending_pods = self.kube_api.list_namespaced_pod(self.namespace, label_selector=label_selector, field_selector="status.phase=Pending")
            for pod in running_pods.items:
                containers.extend(pod.spec.containers)
            for pod in pending_pods.items:
                containers.extend(pod.spec.containers)

        elif self.user_aggregation_key_type == 'annotations':
            escaped_group_name = escape_to_primehub_label(group_info['name'])
            label_selector="{}={}".format(self.group_aggregation_key, escaped_group_name)

            running_pods = self.kube_api.list_namespaced_pod(self.namespace, label_selector=label_selector, field_selector="status.phase=Running")
            pending_pods = self.kube_api.list_namespaced_pod(self.namespace, label_selector=label_selector, field_selector="status.phase=Pending")
            for pod in running_pods.items:
                if pod.metadata.annotations.get(self.user_aggregation_key, '') == user_info['name']:
                    containers.extend(pod.spec.containers)
            for pod in pending_pods.items:
                if pod.metadata.annotations.get(self.user_aggregation_key, '') == user_info['name']:
                    containers.extend(pod.spec.containers)

        cpu, gpu, mem = self.aggregate_resource_usage(containers, cpu, gpu, mem)
        return cpu, gpu, mem

    def get_request_resources(self, request_info):
        cpu_request = 0
        gpu_request = 0
        mem_request = 0
        for container in request_info['request']['object']['spec']['containers']:
            request_resources_limit = container.get('resources', {}).get('limits', {})
            cpu_request += float(convert_cpu_values_to_float(request_resources_limit.get('cpu', 0)))
            gpu_request += int(self._get_gpu_resource_from_limits(request_resources_limit))
            mem_request += convert_mem_resource_to_bytes(request_resources_limit.get('memory', 0))
        return cpu_request, gpu_request, mem_request

    def validate_resources(self, quota_type, request, quota, usage):
        """
        parameter structure will be:

        request {
            cpu, gpu, memory
        }

        quota {
            name, cpu, gpu, memory
        }

        usage {
            cpu, gpu, memory
        }
        """
        for resource_type in ['cpu', 'gpu', 'memory']:
            if quota[resource_type] is not None:
                if usage[resource_type] is None:
                    usage[resource_type] = 0

                if request[resource_type] > 0 and (
                        request[resource_type] + usage[resource_type] > quota[resource_type]):
                    self.last_error_message = '{} {} exceeded {} quota: {}, requesting {}'.format(
                                            quota_type.capitalize(), quota['name'], resource_type, quota[resource_type], request[resource_type])
                    logger.debug(self.last_error_message)
                    return False
        return True

    def validate(self):
        user, group = self.get_user_and_group_from_request_info()

        cpu_request, gpu_request, memory_request = self.get_request_resources(self.request_info)
        request = dict(cpu=cpu_request, gpu=gpu_request, memory=memory_request)
        logger.debug("requesting CPU: {} GPU: {} MEM: {}".format(cpu_request, gpu_request, memory_request))

        group_infos = self.fetch_group_info(group).get('data', {}).get('groups', [])
        for g in group_infos:
            if g['name'] == group['name']:
                # TODO: use get method to get limit data
                group_cpu_limit = g['projectQuotaCpu']
                group_gpu_limit = g['projectQuotaGpu']
                group_memory_limit = g['projectQuotaMemory']
                if group_memory_limit:
                    group_memory_limit = group_memory_limit * GiB()

                logger.debug("SPAWN: checking memory limits")

                user_cpu_limit = g['quotaCpu']
                user_gpu_limit = g['quotaGpu']
                user_memory_limit = g['quotaMemory']
                if user_memory_limit:
                    user_memory_limit = user_memory_limit * GiB()

                break

        user_quota_valid = True
        if len(user['name'].replace("escaped-", "")) > 0: # user name label can be omitted
            user_cpu_usage, user_gpu_usage, user_memory_usage = self.get_user_resource_usage_in_group(group, user)
            logger.debug("user {} current: CPU: {} GPU: {} MEM: {}".format(user['name'], user_cpu_usage, user_gpu_usage, user_memory_usage))
            usage = {
                'cpu': user_cpu_usage,
                'gpu': user_gpu_usage,
                'memory': user_memory_usage
            }
            quota = {
                'name': user.get('name', ''),
                'cpu': user_cpu_limit,
                'gpu': user_gpu_limit,
                'memory': user_memory_limit
            }
            user_quota_valid = self.validate_resources("USER", request, quota, usage)

        group_quota_valid = True
        if user_quota_valid:
            group_cpu_usage, group_gpu_usage, group_memory_usage = self.get_group_resource_usage(group)
            logger.debug("project {} current: CPU: {} GPU: {} MEM: {}".format(group['name'], group_cpu_usage, group_gpu_usage, group_memory_usage))
            usage = {
                'cpu': group_cpu_usage,
                'gpu': group_gpu_usage,
                'memory': group_memory_usage
            }
            quota = {
                'name': group.get('name', ''),
                'cpu': group_cpu_limit,
                'gpu': group_gpu_limit,
                'memory': group_memory_limit
            }
            group_quota_valid = self.validate_resources("GROUP", request, quota, usage)

        return (user_quota_valid and group_quota_valid)
