#!/usr/bin/env bash
set -e

# Clean existing namespaces
ip netns del ns_client 2>/dev/null || true
ip netns del ns_proxy  2>/dev/null || true
ip netns del ns_server 2>/dev/null || true

# Create 3 isolated namespaces: Client --(Leg A)-- Proxy --(Leg B)-- Server
ip netns add ns_client
ip netns add ns_proxy
ip netns add ns_server

# Create veth pairs
ip link add veth_c type veth peer name veth_p_a
ip link add veth_p_b type veth peer name veth_s

ip link set veth_c netns ns_client
ip link set veth_p_a netns ns_proxy
ip link set veth_p_b netns ns_proxy
ip link set veth_s netns ns_server

# Assign IPs (Leg A: 10.0.1.0/24, Leg B: 10.0.2.0/24)
ip netns exec ns_client ip addr add 10.0.1.1/24 dev veth_c
ip netns exec ns_proxy  ip addr add 10.0.1.2/24 dev veth_p_a
ip netns exec ns_proxy  ip addr add 10.0.2.1/24 dev veth_p_b
ip netns exec ns_server ip addr add 10.0.2.2/24 dev veth_s

# Bring up interfaces
for ns_if in "ns_client lo" "ns_client veth_c" "ns_proxy lo" "ns_proxy veth_p_a" "ns_proxy veth_p_b" "ns_server lo" "ns_server veth_s"; do
    set -- $ns_if
    ip netns exec "$1" ip link set "$2" up
done

# CRITICAL: Disable TSO/GSO/GRO offloads on all veth interfaces
for ns_if in "ns_client veth_c" "ns_proxy veth_p_a" "ns_proxy veth_p_b" "ns_server veth_s"; do
    set -- $ns_if
    ip netns exec "$1" ethtool -K "$2" tso off gso off gro off tx off rx off 2>/dev/null || true
done

echo "Namespaces configured and NIC offloads disabled."