def _image_paths(path_prefix, images):
    result = []
    for index, image in enumerate(images):
        result.append(dict(path="{}/{}/image".format(path_prefix, index), value=image['image']))
    return result


def get_image_paths(pod_json):
    if 'spec' not in pod_json:
        raise Exception('not a valid pod definition')

    spec = pod_json['spec']
    paths = []

    if 'initContainers' in spec:
        paths = paths + _image_paths("/spec/initContainers", spec['initContainers'])

    if 'containers' in spec:
        paths = paths + _image_paths("/spec/containers", spec['containers'])

    return paths


def make_replace_patch_operator(image_prefix, image_paths):
    result = []
    for i in image_paths:
        if i['value'].startswith(image_prefix):
            # don't add prefix when it has already added
            continue
        result.append(dict(op="replace", path=i['path'], value="{}{}".format(image_prefix, i['value'])))
    return result
