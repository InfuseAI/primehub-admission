#!/usr/bin/env python

import base64
import copy
import json
import os

import jsonpatch
from flask import Flask, request, jsonify

from primehub_admission.image_patcher import get_image_paths, make_replace_patch_operator
from primehub_admission.license_check import LicenseCheck
from primehub_admission.pvc_check import PvcCheck
from primehub_admission.resources_validation import ResourcesValidation

app = Flask(__name__)


# test connection
@app.route('/', methods=['GET'])
def hello_world():
    return jsonify({'message': 'hello world'})


@app.route('/pvc-check', methods=['POST'])
def pvc_check_webhook():
    selected = select_pod(request.json['request']['object']['metadata'].get('labels', {}))
    if selected:
        try:
            app.logger.debug(request.json)

            check = PvcCheck(request.json)
            json_patch = check.remove_not_found()

            admission_response = {
                "uid": request.json['request']['uid'],
                "allowed": True,
                "patchType": "JSONPatch",
                "patch": base64.b64encode(json.dumps(json_patch).encode()).decode()
            }
        except Exception as e:
            app.logger.error(e)
            admission_response = {
                "allowed": False,
                "status": {
                    "status": 'Failure',
                    "message": str(e),
                    "reason": str(e),
                    "code": 410
                }
            }
    else:
        admission_response = {
            "uid": request.json['request']['uid'],
            "allowed": True,
        }
    return to_admission_review(admission_response)


@app.route('/license-check', methods=['POST'])
def license_check_webhook():
    try:
        app.logger.debug(request.json)
        platform_type = os.environ.get('PLATFORM_TYPE', None)
        if platform_type == 'ee':
            platform_type = 'enterprise'
        license = request.json['request']['object']
        LicenseCheck(platform_type).validate(license)
        admission_response = {
            "uid": request.json['request']['uid'],
            "allowed": True,
            "status": {
                "code": 200,
            }
        }
        return to_admission_review(admission_response)
    except RuntimeError as e:
        app.logger.error(e)
        admission_response = {
            "uid": request.json['request']['uid'],
            "allowed": False,
            "status": {
                "code": 400,
                "message": str(e),
            }
        }
        return to_admission_review(admission_response)
    except Exception as e:
        app.logger.error(e)
        admission_response = {
            "uid": request.json['request']['uid'],
            "allowed": False,
            "status": {
                "code": 500,
                "message": str(e),
            }
        }
        return to_admission_review(admission_response)


@app.route('/image-mutation', methods=['POST'])
def image_mutation_webhook():
    try:
        app.logger.debug(request.json)
        pod = request.json['request']['object']
        prefix = os.environ.get('IMAGE_PREFIX', '')

        if not prefix:
            # it should configure a prefix, example "primehub.airgap:5000/"
            app.logger.debug('no IMAGE_PREFIX, skip to replace image.')
            # skip mutation while prefix is empty
            return to_admission_review(dict(response=dict(allowed=True)))

        json_patch = make_replace_patch_operator(prefix, get_image_paths(pod))
        admission_response = {
            "uid": request.json['request']['uid'],
            "allowed": True,
            "patchType": "JSONPatch",
            "patch": base64.b64encode(json.dumps(json_patch).encode()).decode()
        }
        return to_admission_review(admission_response)
    except Exception as e:
        app.logger.error(e)
        admission_response = {
            "allowed": False,
            "status": {
                "status": 'Failure',
                "message": str(e),
                "reason": str(e),
                "code": 410
            }
        }
        return to_admission_review(admission_response)


@app.route('/', methods=['POST'])
def webhook():
    app.logger.debug(f'request-body: {json.dumps(request.json)}')
    request_info = request.json

    selected = select_pod(request_info['request']['object']['metadata'].get('labels', {}))
    if selected:
        try:
            rv = ResourcesValidation(request_info, \
                                     group_aggregation_key="primehub.io/group", \
                                     group_aggregation_key_type="labels", \
                                     user_aggregation_key="primehub.io/user", \
                                     user_aggregation_key_type="labels")
            allowed = rv.validate()
        except Exception as e:
            app.logger.error(e)
            allowed = True

        if allowed:
            pod_json_modified = stamp_pod_by_admission(copy.deepcopy(request_info['request']['object']))
            patch = jsonpatch.JsonPatch.from_diff(request_info["request"]["object"], pod_json_modified)
            admission_response = {
                "uid": request.json['request']['uid'],
                "allowed": True,
                "patch": base64.b64encode(str(patch).encode()).decode(),
                "patchType": "JSONPatch"
            }
        else:
            admission_response = {
                "uid": request.json['request']['uid'],
                "allowed": False,
                "status": {
                    "status": 'Failure',
                    "message": rv.last_error_message,
                    "reason": rv.last_error_message,
                    "code": 410
                }
            }
    else:
        admission_response = {
            "uid": request.json['request']['uid'],
            "allowed": True,
        }

    return to_admission_review(admission_response)


def to_admission_review(admission_response: dict):
    admission_review = {
        "apiVersion": "admission.k8s.io/v1",
        "kind": "AdmissionReview",
        "response": admission_response
    }
    if 'patch' in admission_response:
        # make sure patchType has been set.
        admission_response["patchType"] = "JSONPatch"
    app.logger.debug(f'admission-review: {json.dumps(admission_review)}')
    return jsonify(admission_review)


def select_pod(labels):
    # We need group in labels to get quota information
    if "primehub.io/group" in labels:
        return True

    return False


def stamp_pod_by_admission(pod_json):
    initContainers = pod_json.get('spec', {}).get('initContainers', [])
    for index, initContainer in enumerate(initContainers):
        if initContainer.get('name', '') == "admission-is-not-found":
            del initContainers[index]
            break
    return pod_json


if __name__ == '__main__':
    # Flask development server
    app.run(host='0.0.0.0', port=5000, debug=os.environ.get('FLASK_DEBUG', 'true') == "true",
            ssl_context=('./ssl/cert.pem', './ssl/key.pem'))
