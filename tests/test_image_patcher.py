import unittest
from primehub_admission.image_patcher import *
import json
import os


def pod_example():
    test_file_dir = os.path.dirname(os.path.realpath(__file__))
    pod_json = os.path.join(test_file_dir, "keycloak-pod.json")

    with open(pod_json) as fh:
        return json.loads(fh.read())


class ImagePatcher(unittest.TestCase):

    def test_patch_request(self):
        excepted = [
            {'path': '/spec/initContainers/0/image',
             'value': 'registry.aiacademy.tw/aai/keycloak/theme:4.1.0-primehub-8203da4'},
            {'path': '/spec/containers/0/image', 'value': 'jboss/keycloak:4.1.0.Final'},
            {'path': '/spec/containers/1/image', 'value': 'gcr.io/cloudsql-docker/gce-proxy:1.11'}
        ]

        # verify get_image_paths can extract (path, value) pairs
        self.assertEqual(excepted, get_image_paths(pod_example()))

        # verify json-patch with prefix
        excepted_with_prefix = [
            {'path': '/spec/initContainers/0/image', 'value': 'primehub.airgap:5000/foo:c8763', 'op': 'replace'},
            {'path': '/spec/containers/1/image', 'value': 'primehub.airgap:5000/foo:barbar', 'op': 'replace'}
        ]
        excepted = [
            {'path': '/spec/initContainers/0/image', 'value': 'foo:c8763', 'op': 'replace'},
            {'path': '/spec/containers/1/image', 'value': 'foo:barbar', 'op': 'replace'},
            # this will drop, because it has already added prefix
            {'path': '/spec/containers/2/image', 'value': 'primehub.airgap:5000/foo:barbar', 'op': 'replace'}
        ]
        self.assertEqual(excepted_with_prefix,
                         make_replace_patch_operator("primehub.airgap:5000/", excepted))
