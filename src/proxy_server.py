import asyncio
from urllib.parse import urlparse
from interactive_prompt import ask_user
from audit_logger import AuditLogger
import config

class AsyncProxyServer:
    def __init__(self, host='127.0.0.1', port=8080):
        self.host = host
        self.port = port
        self.logger = AuditLogger()
        self.config = config.load_config()
        self.trusted_domains = set(self.config.get("trusted_domains", []))
        self.domain_locks = {}
        self.global_lock = asyncio.Lock()

    async def get_domain_lock(self, domain):
        async with self.global_lock:
            if domain not in self.domain_locks:
                self.domain_locks[domain] = asyncio.Lock()
            return self.domain_locks[domain]

    async def handle_client(self, reader, writer):
        try:
            # Read initial request
            request = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=5.0)
            if not request:
                return

            headers = request.split(b"\r\n")
            first_line = headers[0].decode('utf-8', 'ignore')
            parts = first_line.split()
            
            if len(parts) < 3:
                return
                
            method, url, _ = parts
            target_host = ""
            target_port = 80
            
            if method == "CONNECT":
                host_port = url.split(":")
                target_host = host_port[0]
                target_port = int(host_port[1]) if len(host_port) > 1 else 443
            else:
                parsed_url = urlparse(url)
                target_host = parsed_url.hostname
                target_port = parsed_url.port or 80
                if not target_host:
                    for h in headers[1:]:
                        h_str = h.decode('utf-8', 'ignore')
                        if h_str.lower().startswith("host:"):
                            target_host = h_str.split(":", 1)[1].strip()
                            break

            if not target_host:
                return

            # Check config trusted domains
            if target_host in self.trusted_domains or target_host in ("127.0.0.1", "localhost"):
                decision = "Allowed"
            else:
                domain_lock = await self.get_domain_lock(target_host)
                async with domain_lock:
                    decision = self.logger.get_cached_decision(target_host)
                    if not decision:
                        print(f"Intercepted request to {target_host}:{target_port}. Prompting user...")
                        # Run blocking ask_user in a thread so it doesn't freeze the asyncio event loop
                        is_allowed = await asyncio.to_thread(ask_user, target_host)
                        decision = "Allowed" if is_allowed else "Denied"
                        self.logger.log_request(target_host, target_port, decision)
                        print(f"User decided: {decision}")

            if decision != "Allowed":
                print(f"Blocking connection to {target_host}")
                if method == "CONNECT":
                    # Silently drop for SSL protocol error avoidance
                    pass
                else:
                    error_resp = b"HTTP/1.1 403 Forbidden\r\nContent-Type: text/plain\r\nConnection: close\r\n\r\nSandboxed: Access Denied by User."
                    writer.write(error_resp)
                    await writer.drain()
                return

            # Connect to target
            target_reader, target_writer = await asyncio.wait_for(
                asyncio.open_connection(target_host, target_port), timeout=5.0)

            if method == "CONNECT":
                writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
                await writer.drain()
            else:
                target_writer.write(request)
                await target_writer.drain()

            # Forward traffic bidirectionally
            async def forward(src, dst):
                try:
                    while True:
                        data = await src.read(8192)
                        if not data:
                            break
                        dst.write(data)
                        await dst.drain()
                except Exception:
                    pass

            await asyncio.gather(
                forward(reader, target_writer),
                forward(target_reader, writer)
            )

        except asyncio.TimeoutError:
            pass
        except Exception as e:
            pass
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def start(self):
        server = await asyncio.start_server(self.handle_client, self.host, self.port)
        print(f"AsyncProxy server listening on {self.host}:{self.port}")
        async with server:
            await server.serve_forever()

if __name__ == "__main__":
    proxy = AsyncProxyServer()
    try:
        asyncio.run(proxy.start())
    except KeyboardInterrupt:
        print("Proxy server shutting down.")
