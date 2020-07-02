from kubernetes import client, config
import json
import os

class PvcCheck:

    def __init__(self, request_info, mock=False):
        self.request_info = request_info
        self.label_selector = os.environ.get('PVC_LABEL_SELECTOR', 'app!=jupyterhub,app!=primehub-group')

        if mock is False:
            config.load_incluster_config()
            self.kube_api = client.CoreV1Api()
            self.namespace = self.request_info['request']['namespace']
            self.pod = self.request_info['request']['object']

    def remove_not_found(self): 
        volumes = self._get_pod_volumes()
        if len(volumes) == 0:
            return []

        pvcs = self.kube_api.list_namespaced_persistent_volume_claim(self.namespace, label_selector=self.label_selector)
        existing_pvc_names = [x.metadata.name for x in pvcs.items]

        patches = []
        not_found_volume_names = []
        not_found_volume_claim_names = []

        for v in volumes:
            if not v['claim_name'] in existing_pvc_names:
                patches.append(dict(op="remove", path="/spec/volumes/{}".format(v['index'])))
                not_found_volume_names.append(v['name'])
                not_found_volume_claim_names.append(v['claim_name'])

        if len(not_found_volume_names) == 0:
            return []

        for c_index, c in enumerate(self.pod.get('spec', {}).get('containers', [])):
            not_found_mount_pathes = []
            for vm_index, vm in enumerate(c.get('volumeMounts', [])):
                name = vm.get('name', None)
                if name in not_found_volume_names:
                    patches.append(dict(op="remove", path="/spec/containers/{}/volumeMounts/{}".format(c_index, vm_index)))
                    not_found_mount_pathes.append(vm.get('mountPath'))

            if len(not_found_mount_pathes) == 0:
                continue

            for e_index, e in enumerate(c.get('env', [])):
                name = e.get('name', None)
                if name == 'CHOWN_EXTRA':
                    extra_pathes = e.get('value', '').split(',')
                    value = ','.join([item for item in extra_pathes if item not in not_found_mount_pathes])
                    patches.append(dict(op="replace", path="/spec/containers/{}/env/{}".format(c_index, e_index), value=dict(name=name, value=value)))

        if len(patches) > 0:
            patches.append(dict(op="add", path="/metadata/annotations/pvc-not-found", value=','.join(not_found_volume_claim_names)))
            if self.pod.get('metadata', {}).get('annotations', None) is None:
                patches.append(dict(op="add", path="/metadata/annotations", value={}))

        # To preserve the index order, apply the patches in reverse order
        patches.reverse()
        return patches

    def _get_pod_volumes(self):
        volumes = []
        for index, v in enumerate(self.pod.get('spec', {}).get('volumes', [])):
            claim_name = v.get('persistentVolumeClaim', {}).get('claimName', None)
            if claim_name == None or claim_name.startswith('claim-'):
                continue
            volumes.append(dict(name=v['name'], claim_name=claim_name, index=index))
        return volumes
