from __future__ import annotations

from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from pdn_scanner.config import load_config
from pdn_scanner.enums import ContentStatus
from pdn_scanner.extractors.parquet import ParquetExtractor
from pdn_scanner.models import FileDescriptor


def test_parquet_extractor_reads_header_labeled_rows(tmp_path: Path) -> None:
    path = tmp_path / "physical.parquet"
    table = pa.table(
        {
            "Name": ["John Carter"],
            "Address": ["14 Green Street, Boston"],
            "Email": ["john@example.com"],
            "Phones": ['["+1 202 555 0147"]'],
            "Passport": ["John Carter M 1988-03-14, 2022-01-11, 2032-01-11 4510123456"],
        }
    )
    pq.write_table(table, path)

    extractor = ParquetExtractor()
    config = load_config("configs/default.yaml")
    descriptor = FileDescriptor(
        path=str(path),
        rel_path=path.name,
        size_bytes=path.stat().st_size,
        extension=".parquet",
    )

    extraction = extractor.extract(descriptor, config)

    assert extraction.status == ContentStatus.OK
    assert extraction.structured_rows_scanned == 1
    assert extraction.text_chunks
    assert "Name: John Carter" in extraction.text_chunks[0]
    assert "Address: 14 Green Street, Boston" in extraction.text_chunks[0]
    assert "Email: john@example.com" in extraction.text_chunks[0]
    assert 'Phones: ["+1 202 555 0147"]' in extraction.text_chunks[0]
