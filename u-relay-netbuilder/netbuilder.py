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
            subprocess.run(['nsenter', '--net=' + netns + '-s', 'iptables', '-t', 'mangle', '-A', 'PREROUTING', '-p', 'tcp', '-d', str(s), '-j', 'TPROXY', '--on-ip', '127.0.0.20', '--on-port', '1'], check=True)
        elif isinstance(s, ipaddress.IPv6Network):
            subprocess.run(['nsenter', '--net=' + netns + '-s', 'ip6tables', '-t', 'mangle', '-A', 'PREROUTING', '-p', 'tcp', '-d', str(s), '-j', 'TPROXY', '--on-ip', '::ffff:127.0.0.20', '--on-port', '1'], check=True)
def handle_daemon_dnsmasq_inner(args):
    ag = argparse.ArgumentParser()
    ag.add_argument('--netns', default='inner-1')
    ag.add_argument('conf')
    a = ag.parse_args(args)
    netns = a.netns if '/' in a.netns else ('/run/netns/' + a.netns)
    subprocess.run(['nsenter', '--net=' + netns, 'dnsmasq', '--server=' + get_ip_offset(config['base1'], 10), '-C', a.conf], check=True)
def handle_daemon_urelay(args):
    ag = argparse.ArgumentParser()
    ag.add_argument('--netns', default='inner-1-s')
    ag.add_argument('extra_args', nargs='*', default=[])
    ag.add_argument('--gid', default='u-relay')
    ag.add_argument('--uid', default='u-relay')
    a = ag.parse_args(args)
    netns = a.netns if '/' in a.netns else ('/run/netns/' + a.netns)
    return subprocess.run(['setsid', '-f', dir_res + '/container-scripts/ctrtool/ctrtool', 'ns_open_file', '-mP', netns, '-s0,i',
                    '-ni0,n', '-dinet', '-4127.0.0.10,81,a', '-l4096',
                    '-ni0,n', '-6::ffff:127.0.0.20,1,at', '-l4096',
                    '-ni0,n', '-tdgram', f'''-6{get_ip_offset(config['base1'], 10)},123,af''',
                    'setpriv', '--reuid=' + a.uid, '--regid=' + a.gid, '--init-groups',
                    'env', 'NETBUILDER_IPV6_PREFIX_BASE=' + str((int(config['base1'].network_address) >> 64) + 2), 'NODE_ENV=production',
                    'node'] + a.extra_args)

def handle_daemon_powerdns(args):
    ag = argparse.ArgumentParser()
    ag.add_argument('--netns', default='inner-1-s')
    ag.add_argument('extra_args', nargs='*', default=[])
    ag.add_argument('--gid', default='u-relay-pdns')
    ag.add_argument('--uid', default='u-relay-pdns')
    a = ag.parse_args(args)
    netns = a.netns if '/' in a.netns else ('/run/netns/' + a.netns)
    b = ['[' + get_ip_offset(config['base1'], 10) + ']']
    if 'base1_v4' in config:
        b.append(get_ipv4_offset(config['base1_v4'], 2))
    subprocess.run(['setsid', '-f', 'nsenter', '--net=' + netns, 'pdns_server', '--setuid=' + a.uid, '--setgid=' + a.gid, '--local-address=' + ','.join(b), '--local-address-nonexist-fail=false'] + a.extra_args)
a = argparse.ArgumentParser()
a.add_argument('conf')
a.add_argument('-d', '--directory', default='')
av = a.parse_args()
conf_dirname = av.directory if av.directory else os.path.dirname(av.conf)
with open(av.conf, 'r') as conf:
    os.chdir(conf_dirname)
    for l in conf.readlines():
        ss = shlex.split(l, comments=True)
        if (len(ss) > 0) and ss[0]:
            if ss[0] == 'set':
                handle_set(ss[1:])
            elif ss[0] == 'c-inner':
                handle_config_inner(ss[1:])
            elif ss[0] == 'd-dnsmasq-inner':
                handle_daemon_dnsmasq_inner(ss[1:])
            elif ss[0] == 'd-urelay':
                handle_daemon_urelay(ss[1:])
            elif ss[0] in ['cmd', 'c-cmd', 'd-cmd']:
                subprocess.run(ss[1:], check=True)
            elif ss[0] == 'd-powerdns':
                handle_daemon_powerdns(ss[1:])
            else:
                raise Exception(f"""unrecognized command {ss[0]} in {av.conf}""")


