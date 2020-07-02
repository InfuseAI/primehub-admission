import unittest
from unittest.mock import Mock
from kubernetes import client
from src.pvc_check import PvcCheck
import json
import os

class PvcCheckMock(PvcCheck):
    def __init__(self, request_info, mock=False):
        super().__init__(request_info, mock=mock)

        self.kube_api = Mock()
        self.namespace = 'mock'
        self.pod = self._load_pod_example()

        pvc_list = self._load_pvcs()
        self.kube_api.list_namespaced_persistent_volume_claim.return_value = pvc_list

    def _load_pvcs(self):
        pvcs = []
        names = ['project-foo', 'project-bar']
        for name in names:
            pvc = client.V1PersistentVolumeClaim()
            pvc.metadata = client.V1ObjectMeta(namespace=self.namespace, name=name)
            pvcs.append(pvc)
        return client.V1PersistentVolumeClaimList(items=pvcs)

    def _load_pod_example(self):
        test_file_dir = os.path.dirname(os.path.realpath(__file__))
        pod_json = os.path.join(test_file_dir, "jupyter-user-pod.json")
    
        with open(pod_json) as fh:
            return json.loads(fh.read())

class TestPvcCheck(unittest.TestCase):

    def test_remove_pvc(self):
        excepted = [
            {'op': 'add', 'path': '/metadata/annotations', 'value': {}},
            {'op': 'add', 'path': '/metadata/annotations/pvc-not-found', 'value': 'project-not-found-2,project-claim-not-found-1'},
            {'op': 'replace', 'path': '/spec/containers/0/env/1', 'value': {'name': 'CHOWN_EXTRA', 'value': '/project/foo'}},
            {'op': 'remove', 'path': '/spec/containers/0/volumeMounts/3'},
            {'op': 'remove', 'path': '/spec/containers/0/volumeMounts/1'},
            {'op': 'remove', 'path': '/spec/volumes/4'},
            {'op': 'remove', 'path': '/spec/volumes/2'},
        ]

        check = PvcCheckMock({}, mock=True)
        patches = check.remove_not_found()

        self.assertEqual(excepted, patches)
