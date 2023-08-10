#!/usr/bin/python3
import argparse, subprocess, json, ipaddress, os
ap = argparse.ArgumentParser()
ap.add_argument('-s', '--set', nargs='*', default=())
ap.add_argument('-d', '--deny', nargs='*', default=())
ap.add_argument('-D', '--deny6', nargs='*', default=())
ap.add_argument('-v', '--vrf', default=None)
ap.add_argument('-T', '--table', default=None)
ap.add_argument('-n', '--dry-run', action='store_true')
args = ap.parse_args()
for set_arg in args.set:
    s = set_arg.split('=', maxsplit=1)
    os.environ[s[0]] = s[1]
reason = str(os.getenv('reason', default=''))
deny_nets = [ipaddress.IPv4Network(net) for net in args.deny]
deny_nets6 = [ipaddress.IPv6Network(net) for net in args.deny6]
table_vrf = []
if not args.vrf is None:
    table_vrf = table_vrf + ['vrf', args.vrf]
if not args.table is None:
    table_vrf = table_vrf + ['table', args.table]
def get_safe_ipv4(ipa, mask='255.255.255.255'):
    net = ipaddress.IPv4Network(ipa + '/' + mask, strict=False)
    orig_ip = ipaddress.IPv4Address(ipa)
    for d in deny_nets:
        if d.overlaps(net):
            raise ArgumentError(f'IPv4 subnet {net} overlaps with {d}')
    return str(orig_ip) + '/' + str(net.prefixlen)
def get_safe_ipv6(ipa, mask=128):
    net = ipaddress.IPv6Network(ipa + '/' + str(mask), strict=False)
    orig_ip = ipaddress.IPv6Address(ipa)
    for d in deny_nets6:
        if d.overlaps(net):
            raise ArgumentError(f'IPv6 subnet {net} overlaps with {d}')
    return str(orig_ip) + '/' + str(net.prefixlen)
    
cmd_queue = []
def run_cmd(cmd, cmd_args):
    if args.dry_run:
        print(f'command: {cmd} arguments: {cmd_args}')
    else:
        cmd_queue.append(['/bin/sh', '-c', cmd, '_'] + cmd_args)

def change_ips(old=False, new=False):
    if old and 'old_routers' in os.environ:
        safe_v4 = get_safe_ipv4(str(os.environ['old_routers']).split(' ')[0])
        run_cmd('set -eu; GW="${1%%/*}"; shift 1; ip route del 0.0.0.0/0 via "$GW" proto dhcp dev "$interface" "$@"', [safe_v4] + table_vrf)
    if old and 'old_ip_address' in os.environ:
        safe_v4 = get_safe_ipv4(os.environ['old_ip_address'], mask=os.environ.get('old_subnet_mask', '255.255.255.255'))
        run_cmd('ip -4 addr del "$1" dev "$interface"', [safe_v4])
    if new and 'new_ip_address' in os.environ:
        safe_v4 = get_safe_ipv4(os.environ['new_ip_address'], mask=os.environ.get('new_subnet_mask', '255.255.255.255'))
        run_cmd('ip -4 addr add "$1" dev "$interface"', [safe_v4])
    if new and 'new_routers' in os.environ:
        safe_v4 = get_safe_ipv4(str(os.environ['new_routers']).split(' ')[0])
        run_cmd('set -eu; GW="${1%%/*}"; shift 1; ip route del 0.0.0.0/0 via "$GW" proto dhcp dev "$interface" "$@"', [safe_v4] + table_vrf)
def change_ipv6(old=False, new=False):
    if old and 'old_ip6_address' in os.environ:
        safe_v4 = get_safe_ipv6(str(os.environ['old_ip6_address']).split(' ')[0]) # ,mask=64
        run_cmd('ip -6 addr del "$1" dev "$interface"', [safe_v4])
    if new and 'new_ip6_address' in os.environ:
        safe_v4 = get_safe_ipv6(str(os.environ['new_ip6_address']).split(' ')[0])
        run_cmd('ip -6 addr add "$1" dev "$interface"', [safe_v4])
def gen_pd_offset(base, displacement, required_mask):
    base_split = str(base).split('/')
    mask = int(base_split[1])
    if mask == required_mask:
        safe_v6 = get_safe_ipv6(base_split[0], mask=mask)
        v6_network = ipaddress.IPv6Network(safe_v6)
        first_val = int(v6_network.network_address)
        return ipaddress.IPv6Address(first_val + displacement)
    raise ArgumentError(f'IPv6 prefix delegation size (e: {required_mask}, g: {mask}) not expected')
def set_dns():
    if 'new_domain_name_servers' in os.environ:
        safe_v4 = get_safe_ipv4(str(os.environ['new_domain_name_servers']).split(' ')[0])
        run_cmd('resolvectl dns "$interface" "${1%%/*}"', [safe_v4])
if reason == 'BOUND':
    change_ips(new=True)
    set_dns()
elif reason == 'TIMEOUT':
    change_ips(new=True)
    set_dns()
elif reason == 'REBOOT':
    change_ips(new=True)
    set_dns()
elif reason == 'EXPIRE':
    change_ips(old=True)
elif reason == 'FAIL':
    change_ips(old=True)
elif reason == 'RENEW':
    change_ips(old=True)
    change_ips(new=True)
    set_dns()
elif reason == 'REBIND':
    change_ips(old=True)
    run_cmd('ip -4 neigh flush dev "$interface"', [])
    change_ips(new=True)
    set_dns()
else:
    raise ArgumentError('Unknown reason ' + reason)
for c in cmd_queue:
    subprocess.run(c, check=True)
