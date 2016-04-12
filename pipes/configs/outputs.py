"""Write output files for configurations."""
import json
import logging
from pprint import pformat

import gogoutils

from .utils import DeepChainMap, get_template

LOG = logging.getLogger(__name__)


def convert_ini(config_dict):
    """Convert _config_dict_ into a list of INI formatted strings.

    Args:
        config_dict (dict): Configuration dictionary to be flattened.

    Returns:
        (list) Lines to be written to a file in the format of KEY1_KEY2=value.
    """
    config_lines = []

    for env, configs in sorted(config_dict.items()):
        for resource, app_properties in sorted(configs.items()):
            try:
                for app_property, value in sorted(app_properties.items()):
                    variable = '{env}_{resource}_{app_property}'.format(
                        env=env,
                        resource=resource,
                        app_property=app_property).upper()

                    if isinstance(value, (dict, DeepChainMap)):
                        safe_value = "'{0}'".format(json.dumps(dict(value)))
                    else:
                        safe_value = json.dumps(value)

                    line = "{variable}={value}".format(variable=variable,
                                                       value=safe_value)
            except AttributeError:
                resource = resource.upper()
                app_properties = "'{}'".format(json.dumps(app_properties))
                line = '{0}={1}'.format(resource, app_properties)

            LOG.debug('INI line: %s', line)
            config_lines.append(line)
    return config_lines


def write_variables(app_configs=None, out_file='', git_short=''):
    """Append _application.json_ configs to _out_file_, .exports, and .json.

    Variables are written in INI style, e.g. UPPER_CASE=value. The .exports file
    contains 'export' prepended to each line for easy sourcing. The .json file
    is a minified representation of the combined configurations.

    Args:
        app_configs (dict): Environment configurations from _application.json_
            files, e.g. {'dev': {'elb': {'subnet_purpose': 'internal'}}}.
        out_file (str): Name of INI file to append to.
        git_short (str): Short name of Git repository, e.g. forrest/core.

    Returns:
        True upon successful completion.
    """
    generated = gogoutils.Generator(*gogoutils.Parser(git_short).parse_url())

    json_configs = {}
    for env, configs in app_configs.items():
        if env is not 'pipeline':
            rendered_configs = json.loads(get_template('configs.json.j2',
                                                       env=env,
                                                       app=generated.app))
            json_configs[env] = dict(DeepChainMap(configs, rendered_configs))

    json_configs['pipeline'] = app_configs['pipeline']
    LOG.debug('Compiled configs:\n%s', pformat(json_configs))

    config_lines = convert_ini(json_configs)

    with open(out_file, 'at') as jenkins_vars:
        LOG.info('Appending variables to %s.', out_file)
        jenkins_vars.write('\n'.join(config_lines))

    with open(out_file + '.exports', 'wt') as export_vars:
        LOG.info('Writing sourceable variables to %s.', export_vars.name)
        export_vars.write('\n'.join('export {0}'.format(line)
                                    for line in config_lines))

    with open(out_file + '.json', 'wt') as json_handle:
        LOG.info('Writing JSON to %s.', json_handle.name)
        LOG.debug('Total JSON dict:\n%s', json_configs)
        json.dump(json_configs, json_handle)

    return True