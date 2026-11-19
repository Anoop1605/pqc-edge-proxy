import argparse
import asyncio
import csv
import os
import socket
import ssl
import time
from metrics import get_tcp_info

class TerminatingPQCProxy:
    def __init__(self, mode: str, profile: str, log_file: str):
        self.mode = mode
        self.profile = profile
        self.log_file = log_file
        self.conn_id = 0

        # Leg A Server Context (Client-facing)
        self.leg_a_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.leg_a_ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        self.leg_a_ctx.load_cert_chain("certs/server.crt", "certs/server.key")
        
        if mode == "M0":
            self.leg_a_ctx.set_ecdh_curve("X25519")
        elif mode == "M1":
            self.leg_a_ctx.set_ecdh_curve("X25519MLKEM768")
        else:
            raise ValueError("Mode must be M0 or M1")

        # Leg B Client Context (Backend-facing)
        self.leg_b_ctx = ssl.create_default_context(cafile="certs/server.crt")
        self.leg_b_ctx.minimum_version = ssl.TLSVersion.TLSv1_3
        self.leg_b_ctx.check_hostname = False

        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        if not os.path.exists(log_file):
            with open(log_file, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow([
                    "conn_id", "mode", "profile", "outcome", "hs_time_ms",
                    "segs_out", "segs_in", "retrans_delta", "rtt_ms", "pmtu"
                ])

    async def pipe(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
        try:
            while chunk := await reader.read(8192):
                writer.write(chunk)
                await writer.drain()
        except (ConnectionResetError, BrokenPipeError):
            pass
        finally:
            try:
                writer.close()
            except Exception:
                pass

    async def handle_connection(self, raw_sock: socket.socket):
        self.conn_id += 1
        cid = self.conn_id
        loop = asyncio.get_running_loop()
        
        pre_info = get_tcp_info(raw_sock)
        t_start = time.perf_counter()
        outcome = "SUCCESS"
        tls_transport = None

        try:
            # Perform TLS 1.3 Handshake on Leg A
            protocol = asyncio.StreamReaderProtocol(asyncio.StreamReader())
            tls_transport = await loop.start_tls(
                asyncio.Transport, protocol, self.leg_a_ctx, server_side=True
            )
        except Exception:
            # Use standard asyncio stream wrapper with manual SSL wrap for clean raw socket access
            pass

        t_end = time.perf_counter()
        post_info = get_tcp_info(raw_sock)

    async def serve(self, host: str, port: int):
        # Accept raw TCP sockets first to capture pre-handshake TCP_INFO
        loop = asyncio.get_running_loop()
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((host, port))
        sock.listen(128)
        sock.setblocking(False)
        print(f"Proxy [{self.mode} | {self.profile}] listening on {host}:{port}")

        while True:
            client_sock, _ = await loop.sock_accept(sock)
            asyncio.create_task(self._process_client(client_sock))

    async def _process_client(self, client_sock: socket.socket):
        self.conn_id += 1
        cid = self.conn_id
        loop = asyncio.get_running_loop()
        pre_info = get_tcp_info(client_sock)
        t0 = time.perf_counter()
        outcome = "FAIL"
        writer_a = None
        writer_b = None

        try:
            reader_a, writer_a = await asyncio.open_connection(
                sock=client_sock, ssl=self.leg_a_ctx, server_side=True
            )
            t1 = time.perf_counter()
            post_info = get_tcp_info(client_sock)

            # Relay application data to Leg B backend
            reader_b, writer_b = await asyncio.open_connection(
                "10.0.2.2", 8443, ssl=self.leg_b_ctx
            )
            outcome = "SUCCESS"
            await asyncio.gather(
                self.pipe(reader_a, writer_b),
                self.pipe(reader_b, writer_a)
            )
        except Exception as e:
            t1 = time.perf_counter()
            try:
                post_info = get_tcp_info(client_sock)
            except Exception:
                post_info = pre_info
            outcome = f"ERR:{type(e).__name__}"
        finally:
            hs_ms = (t1 - t0) * 1000.0
            with open(self.log_file, "a", newline="") as f:
                csv.writer(f).writerow([
                    cid, self.mode, self.profile, outcome, f"{hs_ms:.3f}",
                    post_info["segs_out"] - pre_info["segs_out"],
                    post_info["segs_in"] - pre_info["segs_in"],
                    post_info["total_retrans"] - pre_info["total_retrans"],
                    f"{post_info['rtt_us'] / 1000.0:.2f}",
                    post_info["pmtu"]
                ])
            for w in (writer_a, writer_b):
                if w:
                    w.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", required=True, choices=["M0", "M1"])
    parser.add_argument("--profile", required=True, choices=["P0", "P3"])
    parser.add_argument("--log", default="results/proxy_metrics.csv")
    args = parser.parse_args()

    proxy = TerminatingPQCProxy(args.mode, args.profile, args.log)
    asyncio.run(proxy.serve("10.0.1.2", 4433))