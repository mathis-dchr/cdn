import asyncio
import json
import os

PORT = int(os.environ.get("PORT", 8080))
VAR = os.environ.get("VAR", "0")


async def handle_client(
    reader: asyncio.StreamReader, writer: asyncio.StreamWriter
):
    try:
        raw_request = await reader.read(4096)
        if not raw_request:
            return

        request_text = raw_request.decode("utf-8", errors="replace")
        lines = request_text.splitlines()
        first_line = lines[0] if lines else "GET / HTTP/1.1"
        method, path, *_ = first_line.split(" ")

        client_ip, client_port = writer.get_extra_info("peername")[:2]
        print(f"[{method}] {path} depuis {client_ip}:{client_port}")

        # Route de santé
        if path == "/health":
            status_code = "200 OK"
            payload = {"status": "ok"}

        # Route par défaut
        else:
            status_code = "200 OK"
            payload = {
                "message": "Serveur de test acti",
                "client": {"ip": client_ip, "port": client_port},
                "env_var": VAR,
                "path": path,
                "method": method,
            }

        body = json.dumps(payload, indent=2).encode("utf-8")
        headers = [
            f"HTTP/1.1 {status_code}",
            "Content-Type: application/json; charset=utf-8",
            f"Content-Length: {len(body)}",
            "Connection: close",
            "",
            "",
        ]

        writer.write("\r\n".join(headers).encode("utf-8") + body)
        await writer.drain()

    except Exception as e:
        print(f"Erreur lors du traitement : {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def main():
    # 0.0.0.0 est obligatoire pour écouter en dehors du conteneur
    server = await asyncio.start_server(handle_client, "0.0.0.0", PORT)
    addr = server.sockets[0].getsockname()
    print(f"Serveur asynchrone démarré sur http://{addr[0]}:{addr[1]}")

    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nArrêt du serveur.")
