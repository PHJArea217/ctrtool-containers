#!/usr/bin/python3
import ipaddress, argparse, shlex, os, sys, subprocess
dir_res = os.path.dirname(__file__) + '/netbuilder-resources'
config = {'eif': 'vif', 'eif_num': 0}
def handle_set(args):
    a = argparse.ArgumentParser()
    a.add_argument('--base1', default='')
    a.add_argument('--base1-v4', default='')
    a.add_argument('--base2', default='')
    a.add_argument('--eif_base', default='')
    a.add_argument('--eif_num', default='')
    av = a.parse_args(args)
    if av.base1:
        config['base1'] = ipaddress.IPv6Network(av.base1)
    if av.base1_v4:
        config['base1_v4'] = ipaddress.IPv4Network(av.base1_v4)
    if av.base2:
        config['base2'] = ipaddress.IPv6Network(av.base2)
    if av.eif_base:
        config['eif'] = str(av.eif_base)
    if av.eif_num:
        config['eif_num'] = int(av.eif_num)
    return
def get_next_eif():
    curr_eif = config['eif'] + str(config['eif_num'])
    config['eif_num'] = config['eif_num'] + 1
    return curr_eif

def get_ip_offset(base, offset):
    if offset >= base.num_addresses:
        raise Exception('offset larger than prefix')
    return str(ipaddress.IPv6Address(int(base.network_address) + offset))
def get_ipv4_offset(base, offset):
    if offset >= base.num_addresses:
        raise Exception('offset larger than prefix')
    return str(ipaddress.IPv4Address(int(base.network_address) + offset))
def handle_config_inner(args):
    ag = argparse.ArgumentParser()
    ag.add_argument('--netns', default='inner-1')
    ag.add_argument('--extra-wg-args', default=(), nargs='*') # need bridge=, veth_up, wg_conf, wg_privkey
    ag.add_argument('--extra-tproxy', default=(), nargs='*')
    a = ag.parse_args(args)
    subprocess.run([dir_res + '/ctrtool-containers/wireguard-netns-bridge/wg-netns-bridge', 'wg_if=wg0', 'local_if=' + get_next_eif(), 'netns=' + a.netns,
                    'wg_addresses=' + ' '.join([get_ip_offset(config['base1'], 1)] + ([get_ipv4_offset(config['base1_v4'], 0)] if 'base1_v4' in config else [])),
                    'lan_addresses=' + ' '.join([get_ip_offset(config['base1'], 0x1_0300_0000_0000_0001) + '/64'] + ([get_ipv4_offset(config['base1_v4'], 17) + '/28'] if 'base1_v4' in config else [])),
                    'wg_unreach=' + ' '.join([str(config['base1'])] + ([str(config['base1_v4'])] if 'base1_v4' in config else []))]
                   + list(a.extra_wg_args), check=True)
    netns = a.netns if '/' in a.netns else ('/run/netns/' + a.netns)
    extra_tproxy = [ipaddress.ip_network(av) for av in a.extra_tproxy]
    tproxy_subnets = extra_tproxy + [ipaddress.IPv6Network(get_ip_offset(config['base1'], 0x2_0000_0000_0000_0000) + '/64')]
    subprocess.run(['nsenter', '--net=' + netns, dir_res + '/ctrtool-containers/misc/netns-tool', 'local_if=to_urelay', 'netns=' + netns + '-s',
    'routes_local=' + ' '.join(str(s) for s in tproxy_subnets),
    'address=' + ' '.join([get_ip_offset(config['base1'], 10)] + ([get_ipv4_offset(config['base1_v4'], 2)] if 'base1_v4' in config else [])),
    'local_addr=0.0.0.10', 'mode=l3_system'], check=True)
    for s in tproxy_subnets:
        if isinstance(s, ipaddress.IPv4Network):
            subprocess.run(['nsenter', '--net=' + netns, 'iptables', '-t', 'mangle', '-A', 'PREROUTING', '-p', 'tcp', '-d', str(s), '-j', 'TPROXY', '--on-ip', '127.0.0.20', '--on-port', '1'], check=True)
        elif isinstance(s, ipaddress.IPv6Network):
            subprocess.run(['nsenter', '--net=' + netns, 'ip6tables', '-t', 'mangle', '-A', 'PREROUTING', '-p', 'tcp', '-d', str(s), '-j', 'TPROXY', '--on-ip', '::ffff:127.0.0.20', '--on-port', '1'], check=True)


a = argparse.ArgumentParser()
a.add_argument('conf')
av = a.parse_args()
with open(av.conf, 'r') as conf:
    for l in conf.readlines():
        ss = shlex.split(l, comments=True)
        if (len(ss) > 0) and ss[0]:
            if ss[0] == 'set':
                handle_set(ss)
            elif ss[0] == 'c-inner':
                handle_config_inner(ss)


