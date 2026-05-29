from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CapcodeEntry:
    address: str
    alias: str
    agency: str | None = None
    color: str | None = None
    icon: str | None = None


class CapcodeDB:
    def __init__(self) -> None:
        self._by_numeric: dict[str, CapcodeEntry] = {}

    @classmethod
    def load(cls, path: str | Path) -> CapcodeDB:
        path = Path(path)
        if not path.exists():
            msg = f'Capcode file not found: {path}'
            raise FileNotFoundError(msg)
        ext = path.suffix.lower()
        db = cls()
        if ext == '.json':
            db._load_json(path)
        elif ext == '.csv':
            db._load_csv(path)
        else:
            msg = f'Unsupported file extension: {ext}'
            raise ValueError(msg)
        return db

    def _load_json(self, path: Path) -> None:
        data = json.loads(path.read_text())
        entries = data.get('data', data) if isinstance(data, dict) else data
        for entry in entries:
            self._add_entry(entry)

    def _load_csv(self, path: Path) -> None:
        with path.open() as f:
            reader = csv.DictReader(f)
            for row in reader:
                self._add_entry(row)

    def _add_entry(self, entry: dict) -> None:
        addr = entry.get('address', '')
        if addr:
            normalized = self._normalize(addr)
            self._by_numeric[normalized] = CapcodeEntry(
                address=addr,
                alias=entry.get('alias', ''),
                agency=entry.get('agency'),
                color=entry.get('color'),
                icon=entry.get('icon'),
            )

    def lookup(self, address: str) -> CapcodeEntry | None:
        normalized = self._normalize(address)
        return self._by_numeric.get(normalized)

    @staticmethod
    def _normalize(address: str) -> str:
        return address.lstrip('0')

    def __len__(self) -> int:
        return len(self._by_numeric)
