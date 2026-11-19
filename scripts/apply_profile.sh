#!/usr/bin/env bash
set -e
PROFILE=$1

# Reset qdiscs and restore default 1500 MTU
ip netns exec ns_client tc qdisc del dev veth_c root 2>/dev/null || true
ip netns exec ns_proxy  tc qdisc del dev veth_p_a root 2>/dev/null || true
ip netns exec ns_client ip link set dev veth_c mtu 1500
ip netns exec ns_proxy  ip link set dev veth_p_a mtu 1500

if [ "$PROFILE" == "P0" ]; then
    ip netns exec ns_client tc qdisc add dev veth_c root netem delay 0.5ms rate 1000mbit
    ip netns exec ns_proxy  tc qdisc add dev veth_p_a root netem delay 0.5ms rate 1000mbit
    echo "Applied P0 (Clean LAN: MTU=1500, RTT=1ms, Loss=0%, Rate=1Gbps)"
elif [ "$PROFILE" == "P3" ]; then
    ip netns exec ns_client ip link set dev veth_c mtu 1280
    ip netns exec ns_proxy  ip link set dev veth_p_a mtu 1280
    ip netns exec ns_client tc qdisc add dev veth_c root netem delay 50ms loss 2% rate 1mbit
    ip netns exec ns_proxy  tc qdisc add dev veth_p_a root netem delay 50ms loss 2% rate 1mbit
    echo "Applied P3 (Constrained IoT: MTU=1280, RTT=100ms, Loss=2%, Rate=1Mbps)"
else
    echo "Usage: $0 [P0|P3]"
    exit 1
fi