from base64 import b64decode
import re


class LicenseCheck:

    def __init__(self, platform = None):
        self.platform = platform

    def _validate_signed_license(self, signed_license):

        signed_license = signed_license.split('.')[0]
        license = b64decode(signed_license)
        license = license.decode("utf-8")

        if not self.platform:
            return

        for line in license.split('\n'):
            match = re.match(r"platform_type:\s*\"(\w*)\"", line)
            if match:
                license_platform_type = match.group(1)
                if license_platform_type !=  self.platform:
                    raise RuntimeError(f"The license is for \"{license_platform_type}\", but \"{self.platform}\" license is required.")

    def validate(self, license):
        self._validate_signed_license(license["spec"]["signed_license"])







