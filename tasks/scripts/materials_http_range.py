"""Read-only byte-range reader for explicitly selected public source archives.

Only preparation uses network access. A cache block is written with a receipt;
candidate evaluation consumes a compact JSON bundle and never calls this class.
"""
from __future__ import annotations
import hashlib
import io
import json
import urllib.request
from pathlib import Path


class HTTPRangeReader(io.RawIOBase):
    def __init__(self, url, size, cache, block_size=262144):
        self.url, self.size, self.position = url, size, 0
        self.cache = Path(cache)
        self.cache.mkdir(parents=True, exist_ok=True)
        self.block_size = block_size
        self.receipts = {}

    def readable(self): return True
    def seekable(self): return True
    def tell(self): return self.position

    def seek(self, offset, whence=0):
        self.position = offset if whence == 0 else self.position + offset if whence == 1 else self.size + offset
        if self.position < 0:
            raise ValueError("negative source offset")
        return self.position

    def read(self, size=-1):
        if size < 0:
            size = self.size - self.position
        stop = min(self.size, self.position + size)
        pieces = []
        while self.position < stop:
            block = self.position // self.block_size
            start = block * self.block_size
            end = min(self.size, start + self.block_size) - 1
            path = self.cache / f"{block:09d}.bin"
            if not path.is_file():
                request = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{end}"})
                with urllib.request.urlopen(request, timeout=90) as response:
                    if response.status != 206 or response.headers.get("Content-Range") != f"bytes {start}-{end}/{self.size}":
                        raise ValueError("source server did not honor the exact requested byte range")
                    raw = response.read()
                if len(raw) != end-start+1:
                    raise ValueError("source range was truncated")
                path.write_bytes(raw)
            raw = path.read_bytes()
            self.receipts[str(block)] = {"start": start, "end": end, "sha256": hashlib.sha256(raw).hexdigest()}
            offset = self.position-start
            take = min(stop-self.position, len(raw)-offset)
            pieces.append(raw[offset:offset+take])
            self.position += take
        return b"".join(pieces)

    def readinto(self, buffer):
        data = self.read(len(buffer))
        buffer[:len(data)] = data
        return len(data)

    def save_receipt(self):
        receipt = {"url": self.url, "source_size": self.size, "block_size": self.block_size, "blocks": self.receipts,
                   "verification": "SHA256 of retrieved ranges, not full-file SHA256 verification"}
        (self.cache / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
        return receipt
