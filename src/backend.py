import asyncio
import ssl

async def handle_client(reader: asyncio.StreamReader, writer: asyncio.StreamWriter):
    try:
        data = await reader.read(4096)
        if data:
            body = b"OK_PQC_RELAY_VERIFIED\n"
            resp = (
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/plain\r\n"
                b"Content-Length: " + str(len(body)).encode() + b"\r\n"
                b"Connection: close\r\n\r\n" + body
            )
            writer.write(resp)
            await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()

async def main():
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.minimum_version = ssl.TLSVersion.TLSv1_3
    ctx.load_cert_chain("certs/server.crt", "certs/server.key")

    server = await asyncio.start_server(handle_client, "10.0.2.2", 8443, ssl=ctx)
    print("Backend TLS 1.3 server listening on 10.0.2.2:8443")
    async with server:
        await server.serve_forever()

if __name__ == "__main__":
    asyncio.run(main())