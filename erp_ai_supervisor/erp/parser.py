# erp/parser.py
"""
ERP XML response parsers for different tile types.
Extracts data from ERP XML responses and normalizes to standard formats.
"""

import xml.etree.ElementTree as ET
from typing import Tuple, Dict, List, Optional


def parse_periodic_trend(xml_text: str) -> Tuple[List[str], List[float]]:
    """
    Parse periodic trend XML response.
    
    Extracts month names and net amounts from ERP XML response.
    Returns lists suitable for time-series plotting.
    
    Args:
        xml_text: XML response from ERP periodic_trend request
    
    Returns:
        Tuple of (months_list, amounts_list)
        Example: (["Jan 2025", "Feb 2025"], [10000.0, 12000.0])
    
    Notes:
        - Looks for PERIODNAME and NETTAMOUNT elements
        - Skips entries with missing or invalid data
        - Converts amounts to float
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML in periodic trend response: {str(e)}")
    
    months = []
    amounts = []
    
    # Robust parsing: iterate all elements, find PERIODNAME and NETTAMOUNT
    for item in root.findall(".//*"):
        month = item.findtext("PERIODNAME")
        amt_text = item.findtext("NETTAMOUNT")
        
        if month and amt_text:
            try:
                months.append(month.strip())
                amounts.append(float(amt_text))
            except ValueError:
                # Skip invalid numeric values
                pass
    
    if not months or not amounts:
        raise ValueError("No valid period/amount data found in XML response")
    
    return months, amounts


def parse_tiles(xml_text: str) -> Dict[str, float]:
    """
    Parse generic tile XML response (trading, cashflow, assets).
    
    Extracts name-value pairs from ERP XML.
    Handles AMOUNT elements with BV (Book Value) attributes.
    
    Args:
        xml_text: XML response from ERP tile request (trading, cashflow, assets)
    
    Returns:
        Dictionary of {tile_name: value}
        Example: {"Sales": 100000.0, "Expenses": 50000.0, "Profit": 50000.0}
    
    Notes:
        - Looks for NAME element and AMOUNT element with BV attribute
        - Strips whitespace and removes parentheses (handles negative notation)
        - Converts amounts to float
        - Skips entries with missing or invalid data
    """
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as e:
        raise ValueError(f"Invalid XML in tile response: {str(e)}")
    
    tiles = {}
    
    # Iterate all elements, find NAME and AMOUNT (with BV attribute)
    for item in root.findall(".//*"):
        name = item.findtext("NAME")
        amount_elem = item.find("AMOUNT")
        
        if name and amount_elem is not None:
            bv = amount_elem.attrib.get("BV")
            
            if bv:
                try:
                    # Clean: remove parentheses (e.g., "(1000)" → "1000")
                    clean = bv.replace("(", "").replace(")", "").strip()
                    value = float(clean)
                    
                    # Handle negative notation: if original had parentheses, make negative
                    if "(" in bv:
                        value = -abs(value)
                    
                    tiles[name.strip()] = value
                except ValueError:
                    # Skip invalid numeric values
                    pass
    
    if not tiles:
        raise ValueError("No valid tile data found in XML response")
    
    return tiles


def parse_xml_safe(xml_text: str, parser_func) -> Optional[any]:
    """
    Safely parse XML with error handling.
    
    Args:
        xml_text: XML string to parse
        parser_func: Parser function to call (parse_periodic_trend, parse_tiles, etc.)
    
    Returns:
        Parsed data or None if parsing fails
    
    Raises:
        ValueError: If parsing fails after retries
    """
    try:
        return parser_func(xml_text)
    except (ET.ParseError, ValueError) as e:
        # Log error and re-raise
        raise ValueError(f"XML parsing failed: {str(e)}")
