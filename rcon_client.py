import socket
import time

import config


class ETLegacyRcon:
    """Improved ET:Legacy RCON helper with retries and simple parsing.

    Uses UDP by default sending `rcon <password> <command>` to the game port.
    Provides a short retry loop and returns text output.
    """

    def __init__(self, host=None, port=None, password=None, timeout=2.0, retries=2):
        self.host = host or config.ET_SERVER_HOST
        self.port = port or config.ET_SERVER_PORT
        self.password = password or config.ET_RCON_PASSWORD
        self.timeout = timeout
        self.retries = retries

    def _build_payload(self, command: str) -> bytes:
        return f"rcon {self.password} {command}\n".encode("utf-8")

    def send(self, command: str) -> str:
        payload = self._build_payload(command)
        last_err = None
        for attempt in range(1, self.retries + 2):
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                    s.settimeout(self.timeout)
                    s.sendto(payload, (self.host, self.port))
                    data, _ = s.recvfrom(16384)
                    return data.decode("utf-8", errors="ignore")
            except socket.timeout as e:
                last_err = e
                time.sleep(0.1 * attempt)
                continue
            except Exception as e:
                last_err = e
                break
        # If we reach here, there was no response
        return "" if last_err is None else f"(no response) {last_err}"


if __name__ == "__main__":
    r = ETLegacyRcon()
    print(r.send("status"))
