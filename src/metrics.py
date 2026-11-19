import socket
import struct

# Linux struct tcp_info layout (first 32 fields cover RTT, retrans, segments, bytes)
TCP_INFO_FMT = "BBBBBBBBIIIIIIIIIIIIIIIIIIIIIIII"
TCP_INFO_SIZE = struct.calcsize(TCP_INFO_FMT)

def get_tcp_info(sock: socket.socket) -> dict:
    raw = sock.getsockopt(socket.IPPROTO_TCP, socket.TCP_INFO, TCP_INFO_SIZE)
    fields = struct.unpack(TCP_INFO_FMT, raw)
    return {
        "rtt_us": fields[17],            # tcpi_rtt (microseconds)
        "rttvar_us": fields[18],         # tcpi_rttvar
        "pmtu": fields[21],              # tcpi_pmtu
        "total_retrans": fields[26],     # tcpi_total_retrans
        "segs_out": fields[29],          # tcpi_segs_out
        "segs_in": fields[30],           # tcpi_segs_in
    }