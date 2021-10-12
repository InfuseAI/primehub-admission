import unittest
import pytest
import base64
from primehub_admission.license_check import LicenseCheck

def _encode(data):
    return base64.b64encode(data.encode()).decode('utf-8') + ".xxxx"

ee_license = _encode("""licensed_to: "InfuseAI"
started_at: "2020-01-01T00:00:00Z"
expired_at: "2021-12-31T12:59:00Z"
max_group: 9999
max_node: 1000
max_model_deploy: 1000
platform_type: "enterprise"
""")

deploy_license = _encode("""licensed_to: "InfuseAI"
started_at: "2020-01-01T00:00:00Z"
expired_at: "2021-12-31T12:59:00Z"
max_group: 9999
max_node: 1000
max_model_deploy: 1000
platform_type: "deploy"
""")

no_platform_license = _encode("""licensed_to: "InfuseAI"
started_at: "2020-01-01T00:00:00Z"
expired_at: "2021-12-31T12:59:00Z"
max_group: 9999
max_node: 1000
max_model_deploy: 1000
""")

class TestLicenseCheck(unittest.TestCase):
    def test_enterprise(self):
        license_check = LicenseCheck('enterprise')

        license_check._validate_signed_license(ee_license)

        with pytest.raises(RuntimeError) as e:
            license_check._validate_signed_license(deploy_license)

        license_check._validate_signed_license(no_platform_license)

    def test_deploy(self):
        license_check = LicenseCheck('deploy')

        with pytest.raises(RuntimeError) as e:
            license_check._validate_signed_license(ee_license)


        license_check._validate_signed_license(deploy_license)

        license_check._validate_signed_license(no_platform_license)

    def test_no_platfrom(self):
        license_check = LicenseCheck()

        license_check._validate_signed_license(ee_license)

        license_check._validate_signed_license(deploy_license)

        license_check._validate_signed_license(no_platform_license)