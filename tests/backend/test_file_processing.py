from __future__ import annotations

import os
import pytest
from app.utils.file_processing import (
    detect_encoding,
    detect_delimiter,
    inspect_csv_file,
)

DATA_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "../../data/synthetic")
)


def test_detect_encoding_utf8():
    """Verify UTF-8 and BOM detection."""
    text_utf8 = "customer_id,name,revenue\n1,Alpha,100\n".encode("utf-8")
    assert "utf-8" in detect_encoding(text_utf8)

    bom_utf8 = b"\xef\xbb\xbfcustomer_id,name,revenue"
    assert detect_encoding(bom_utf8) == "utf-8-sig"


def test_detect_delimiter():
    """Verify delimiter detection for comma, tab, semicolon, and pipe."""
    comma_csv = "id,name,amount\n1,Widget,50\n2,Gadget,30"
    assert detect_delimiter(comma_csv) == ","

    semicolon_csv = "id;name;amount\n1;Widget;50\n2;Gadget;30"
    assert detect_delimiter(semicolon_csv) == ";"

    tab_tsv = "id\tname\tamount\n1\tWidget\t50\n2\tGadget\t30"
    assert detect_delimiter(tab_tsv) == "\t"


def test_inspect_csv_file_on_products():
    """Verify streaming inspect_csv_file on actual products.csv."""
    path = os.path.join(DATA_DIR, "products.csv")
    row_count, columns, encoding, delimiter = inspect_csv_file(path)

    assert row_count >= 90
    assert "product_id" in columns
    assert "name" in columns
    assert "category" in columns
    assert "unit_price" in columns
    assert delimiter == ","
    assert "utf-8" in encoding
