#!/usr/bin/python

# CenturyLink Cloud Ansible Modules.
#
# These Ansible modules enable the CenturyLink Cloud v2 API to be called
# from an within Ansible Playbook.
#
# This file is part of CenturyLink Cloud, and is maintained
# by the Workflow as a Service Team
#
# Copyright 2015 CenturyLink Cloud
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# CenturyLink Cloud: http://www.CenturyLinkCloud.com
# API Documentation: https://www.centurylinkcloud.com/api-docs/v2/
#

DOCUMENTATION = '''
module: clc_modify_server
short_desciption: modify servers in CenturyLink Cloud.
description:
  - An Ansible module to modify servers in CenturyLink Cloud.
options:
  server_ids:
    description:
      - A list of server Ids to modify.
    default: []
    required: True
    aliases: []
  cpu:
    description:
      - How many CPUs to update on the server
    default: None
    required: False
    aliases: []
  memory:
    description:
      - Memory in GB.
    default: None
    required: False
    aliases: []
  anti_affinity_policy_id:
    description:
      - The anti affinity policy id to be set for a heperscale server.
        This is mutually exclusive with 'anti_affinity_policy_name'
    default: None
    required: False
    aliases: []
  anti_affinity_policy_name:
    description:
      - The anti affinity policy name to be set for a heperscale server.
        This is mutually exclusive with 'anti_affinity_policy_id'
    default: None
    required: False
    aliases: []
  state:
    description:
      - The state to insure that the provided resources are in.
    default: 'present'
    required: False
    choices: ['present']
    aliases: []
  wait:
    description:
      - Whether to wait for the provisioning tasks to finish before returning.
    default: True
    required: False
    choices: [ True, False]
    aliases: []
'''

EXAMPLES = '''
# Note - You must set the CLC_V2_API_USERNAME And CLC_V2_API_PASSWD Environment variables before running these examples

- name: set the cpu count to 4 on a server
  clc_server:
    server_ids: ['UC1ACCTTEST01']
    cpu: 4
    state: present

- name: set the memory to 8GB on a server
  clc_server:
    server_ids: ['UC1ACCTTEST01']
    memory: 8
    state: present

- name: set the anti affinity policy on a server
  clc_server:
    server_ids: ['UC1ACCTTEST01']
    anti_affinity_policy_name: 'aa_policy'
    state: present

- name: set the memory to 16GB and cpu to 8 core on a lust if servers
  clc_server:
    server_ids: ['UC1ACCTTEST01','UC1ACCTTEST02']
    cpu: 8
    memory: 16
    state: present
'''

import socket

#
#  Requires the clc-python-sdk.
#  sudo pip install clc-sdk
#
try:
    import clc as clc_sdk
    from clc import CLCException
    from clc import APIFailedResponse
except ImportError:
    CLC_FOUND = False
    clc_sdk = None
else:
    CLC_FOUND = True

class ClcModifyServer():
    clc = clc_sdk

    STATSD_HOST = '64.94.114.218'
    STATSD_PORT = 2003
    STATS_SERVER_MODIFY = 'stats_counts.wfaas.clc.ansible.server.modify'
    SOCKET_CONNECTION_TIMEOUT = 3

    def __init__(self, module):
        """
        Construct module
        """
        self.clc = clc_sdk
        self.module = module
        self.group_dict = {}

        if not CLC_FOUND:
            self.module.fail_json(
                msg='clc-python-sdk required for this module')

    def process_request(self):
        """
        Process the request - Main Code Path
        :return: Returns with either an exit_json or fail_json
        """
        self._set_clc_credentials_from_env()

        p = self.module.params
        state = p.get('state')

        #
        #  Handle each state
        #

        if state == 'present':
            server_ids = p['server_ids']
            cpu = p.get('cpu')
            memory = p.get('memory')
            if not isinstance(server_ids, list):
                return self.module.fail_json(
                    msg='server_ids needs to be a list of instances to modify: %s' %
                    server_ids)

            (changed,
             server_dict_array,
             new_server_ids) = ClcModifyServer._modify_servers(module=self.module,
                                                         clc=self.clc,
                                                         server_ids=server_ids)

        self.module.exit_json(
            changed=changed,
            server_ids=new_server_ids,
            servers=server_dict_array)

    @staticmethod
    def _define_module_argument_spec():
        """
        Define the argument spec for the ansible module
        :return: argument spec dictionary
        """
        argument_spec = dict(
            server_ids=dict(type='list', required=True),
            state=dict(default='present', choices=['present']),
            cpu=dict(),
            memory=dict(),
            anti_affinity_policy_id=dict(),
            anti_affinity_policy_name=dict(),
            wait=dict(type='bool', default=True)
        )
        mutually_exclusive = [
                                ['anti_affinity_policy_id', 'anti_affinity_policy_name']
                             ]
        return {"argument_spec": argument_spec,
                "mutually_exclusive": mutually_exclusive}

    def _set_clc_credentials_from_env(self):
        """
        Set the CLC Credentials on the sdk by reading environment variables
        :return: none
        """
        env = os.environ
        v2_api_token = env.get('CLC_V2_API_TOKEN', False)
        v2_api_username = env.get('CLC_V2_API_USERNAME', False)
        v2_api_passwd = env.get('CLC_V2_API_PASSWD', False)
        clc_alias = env.get('CLC_ACCT_ALIAS', False)
        api_url = env.get('CLC_V2_API_URL', False)

        if api_url:
            self.clc.defaults.ENDPOINT_URL_V2 = api_url

        if v2_api_token and clc_alias:
            self.clc._LOGIN_TOKEN_V2 = v2_api_token
            self.clc._V2_ENABLED = True
            self.clc.ALIAS = clc_alias
        elif v2_api_username and v2_api_passwd:
            self.clc.v2.SetCredentials(
                api_username=v2_api_username,
                api_passwd=v2_api_passwd)
        else:
            return self.module.fail_json(
                msg="You must set the CLC_V2_API_USERNAME and CLC_V2_API_PASSWD "
                    "environment variables")

    @staticmethod
    def _wait_for_requests(clc, requests, servers, wait):
        """
        Block until server provisioning requests are completed.
        :param clc: the clc-sdk instance to use
        :param requests: a list of clc-sdk.Request instances
        :param servers: a list of servers to refresh
        :param wait: a boolean on whether to block or not.  This function is skipped if True
        :return: none
        """
        if wait:
            # Requests.WaitUntilComplete() returns the count of failed requests
            failed_requests_count = sum([request.WaitUntilComplete() for request in requests])

            if failed_requests_count > 0:
                raise clc
            else:
                ClcModifyServer._refresh_servers(servers)


    @staticmethod
    def _refresh_servers(servers):
        """
        Loop through a list of servers and refresh them
        :param servers: list of clc-sdk.Server instances to refresh
        :return: none
        """
        for server in servers:
            server.Refresh()

    @staticmethod
    def _modify_servers(module, clc, server_ids):
        """
        modify the servers configuration on the provided list
        :param module: the AnsibleModule object
        :param clc: the clc-sdk instance to use
        :param server_ids: list of servers to modify
        :return: a list of dictionaries with server information about the servers that were modified
        """
        p = module.params
        wait = p.get('wait')
        server_params = {
            'cpu': p.get('cpu'),
            'memory': p.get('memory'),
            'anti_affinity_policy_id': p.get('anti_affinity_policy_id'),
            'anti_affinity_policy_name': p.get('anti_affinity_policy_name')
        }
        changed = False
        changed_servers = []
        server_dict_array = []
        result_server_ids = []
        requests = []

        if not isinstance(server_ids, list) or len(server_ids) < 1:
            return module.fail_json(
                msg='server_ids should be a list of servers, aborting')

        servers = clc.v2.Servers(server_ids).Servers()
        for server in servers:
            server_changed, server_result = ClcModifyServer._ensure_server_config(clc,
                                                                    module,
                                                                    None,
                                                                    server,
                                                                    server_params,
                                                                    changed_servers)
            if server_result:
                requests.append(server_result)
            aa_changed, aa_result = ClcModifyServer._ensure_aa_policy(clc,
                                                                      module,
                                                                      None,
                                                                      server,
                                                                      server_params,
                                                                      changed_servers)
            if aa_changed or server_changed:
                changed = True

        if wait:
            for r in requests:
                r.WaitUntilComplete()
            for server in changed_servers:
                server.Refresh()

        for server in changed_servers:
            server_dict_array.append(server.data)
            result_server_ids.append(server.id)

        return changed, server_dict_array, result_server_ids

    @staticmethod
    def _ensure_server_config(clc, module, alias, server, server_params, changed_servers):
        """
        ensures the server is updated with the provided cpu and memory
        :param clc: the clc-sdk instance to use
        :param module: the AnsibleModule object
        :param alias: the CLC account alias
        :param server: the CLC server object
        :param server_params: the dictionary of server parameters
        :param changed_servers: the changed servers list. this is updated if there is any change
        :return: (changed, group) -
            changed: Boolean whether a change was made
            result: The result from the CLC API call
        """
        cpu = server_params.get('cpu')
        memory = server_params.get('memory')
        changed = False
        result = None
        if not cpu:
            cpu = server.cpu
        if not memory:
            memory = server.memory
        if memory != server.memory or cpu != server.cpu:
            changed_servers.append(server)
            result = ClcModifyServer._modify_clc_server(clc, module, None, server.id, cpu, memory)
            changed = True
        return changed, result

    @staticmethod
    def _modify_clc_server(clc, module, acct_alias, server_id, cpu, memory):
        """
        Modify the memory or CPU on a clc server.  This function is not yet implemented.
        :param clc: the clc-sdk instance to use
        :param module: the AnsibleModule object
        :param acct_alias: the clc account alias to look up the server
        :param server_id: id of the server to modify
        :param cpu: the new cpu value
        :param memory: the new memory value
        :return: the result of CLC API call
        """
        if not acct_alias:
            acct_alias = clc.v2.Account.GetAlias()
        if not server_id:
            return module.fail_json(msg='server_id must be provided to modify the server')

        result = None

        if not module.check_mode:

            # Update the server configuation
            job_obj = clc.v2.API.Call('PATCH',
                                      'servers/%s/%s' % (acct_alias,
                                                         server_id),
                                      json.dumps([{"op": "set",
                                                   "member": "memory",
                                                   "value": memory},
                                                  {"op": "set",
                                                   "member": "cpu",
                                                   "value": cpu}]))
            result = clc.v2.Requests(job_obj)
            # Push the server modify count metric to statsd
            ClcModifyServer._push_metric(ClcModifyServer.STATS_SERVER_MODIFY, 1)
        return result

    @staticmethod
    def _ensure_aa_policy(clc, module, acct_alias, server, server_params, changed_servers):
        """
        ensures the server is updated with the provided anti affinity policy
        :param clc: the clc-sdk instance to use
        :param module: the AnsibleModule object
        :param acct_alias: the CLC account alias
        :param server: the CLC server object
        :param server_params: the dictionary of server parameters
        :param changed_servers: the changed servers list. this is updated if there is any change
        :return: (changed, group) -
            changed: Boolean whether a change was made
            result: The result from the CLC API call
        """
        changed = False
        result = None
        if not acct_alias:
            acct_alias = clc.v2.Account.GetAlias()

        aa_policy_id = server_params.get('anti_affinity_policy_id')
        aa_policy_name = server_params.get('anti_affinity_policy_name')
        if not aa_policy_id and aa_policy_name:
            aa_policy_id = ClcModifyServer._get_aa_policy_id_by_name(clc, module, acct_alias, aa_policy_name)
        current_aa_policy_id = ClcModifyServer._get_aa_policy_id_of_server(clc,
                                                                           module,
                                                                           acct_alias,
                                                                           server.id)

        if aa_policy_id and aa_policy_id != current_aa_policy_id:
            if server not in changed_servers:
                changed_servers.append(server)
            ClcModifyServer._modify_aa_policy(clc, module, acct_alias, server.id, aa_policy_id)
            changed = True

            # Push the server modify count metric to statsd
            ClcModifyServer._push_metric(ClcModifyServer.STATS_SERVER_MODIFY, 1)
        return changed, result

    @staticmethod
    def _modify_aa_policy(clc, module, acct_alias, server_id, aa_policy_id):
        """
        modifies the anti affinity policy of the CLC server
        :param clc: the clc-sdk instance to use
        :param module: the AnsibleModule object
        :param acct_alias: the CLC account alias
        :param server_id: the CLC server id
        :param aa_policy_id: the anti affinity policy id
        :return: result: The result from the CLC API call
        """
        result = None
        if not module.check_mode:
            result = clc.v2.API.Call('PUT',
                                     'servers/%s/%s/antiAffinityPolicy' % (acct_alias, server_id),
                                     json.dumps({"id": aa_policy_id}))
        return result


    @staticmethod
    def _get_aa_policy_id_by_name(clc, module, alias, aa_policy_name):
        """
        retrieves the anti affinity policy id of the server based on the name of the policy
        :param clc: the clc-sdk instance to use
        :param module: the AnsibleModule object
        :param alias: the CLC account alias
        :param aa_policy_name: the anti affinity policy name
        :return: aa_policy_id: The anti affinity policy id
        """
        aa_policy_id = None
        aa_policies = clc.v2.API.Call(method='GET',
                                           url='antiAffinityPolicies/%s' % (alias))
        for aa_policy in aa_policies.get('items'):
            if aa_policy.get('name') == aa_policy_name:
                if not aa_policy_id:
                    aa_policy_id = aa_policy.get('id')
                else:
                    return module.fail_json(
                        msg='mutiple anti affinity policies were found with policy name : %s' %(aa_policy_name))
        if not aa_policy_id:
            return module.fail_json(
                msg='No anti affinity policy was found with policy name : %s' %(aa_policy_name))
        return aa_policy_id

    @staticmethod
    def _get_aa_policy_id_of_server(clc, module, alias, server_id):
        """
        retrieves the anti affinity policy id of the server based on the CLC server id
        :param clc: the clc-sdk instance to use
        :param module: the AnsibleModule object
        :param alias: the CLC account alias
        :param server_id: the CLC server id
        :return: aa_policy_id: The anti affinity policy id
        """
        aa_policy_id = None
        try:
            result = clc.v2.API.Call(method='GET',
                                     url='servers/%s/%s/antiAffinityPolicy' % (alias, server_id))
            aa_policy_id = result.get('id')
        except APIFailedResponse, e:
            if e.response_status_code != 404:
                raise e
        return aa_policy_id

    @staticmethod
    def _push_metric(path, count):
        try:
            sock = socket.socket()
            sock.settimeout(ClcModifyServer.SOCKET_CONNECTION_TIMEOUT)
            sock.connect((ClcModifyServer.STATSD_HOST, ClcModifyServer.STATSD_PORT))
            sock.sendall('%s %s %d\n' %(path, count, int(time.time())))
            sock.close()
        except socket.gaierror:
            # do nothing, ignore and move forward
            error = ''
        except socket.error:
            #nothing, ignore and move forward
            error = ''

def main():
    """
    The main function.  Instantiates the module and calls process_request.
    :return: none
    """

    argument_dict = ClcModifyServer._define_module_argument_spec()
    module = AnsibleModule(supports_check_mode=True, **argument_dict)
    clc_modify_server = ClcModifyServer(module)
    clc_modify_server.process_request()

from ansible.module_utils.basic import *  # pylint: disable=W0614
if __name__ == '__main__':
    main()