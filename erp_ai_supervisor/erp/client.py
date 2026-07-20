# erp/client.py
"""
ERP API client - communicates with ERP server.
Handles XML template loading, parameter substitution, and request transmission.
"""

import os
import re
from pathlib import Path
from typing import Optional, Dict, Any
import requests
from dotenv import load_dotenv

load_dotenv()

# Configuration
ERP_ENDPOINT = os.getenv("ERP_ENDPOINT", "http://localhost:9000")
ERP_REQUEST_PORT = os.getenv("ERP_REQUEST_PORT", "9000")
TEMPLATE_DIR = os.getenv("ERP_TEMPLATE_DIR", "erp/xml_templates")


class ERPClient:
    """
    ERP API client for fetching dashboard data.
    
    Usage:
        client = ERPClient()
        response = client.send_request("periodic_trend.xml", {
            "company_name": "MyCompany",
            "voucher_type": "Sales",
            "from_date": "1-Apr-25",
            "to_date": "31-Mar-26",
            "current_date": "1-Jan-26",
            "periodicity": "Month"
        })
    """
    
    def __init__(self, endpoint: Optional[str] = None):
        """
        Initialize ERP client.
        
        Args:
            endpoint: ERP server endpoint (defaults to env var ERP_ENDPOINT)
        """
        self.endpoint = endpoint or ERP_ENDPOINT
        self.template_dir = Path(TEMPLATE_DIR)
    
    def load_template(self, template_name: str) -> str:
        """
        Load XML template from file.
        
        Args:
            template_name: Name of template file (e.g. "periodic_trend.xml")
        
        Returns:
            XML template as string
        
        Raises:
            FileNotFoundError: If template not found
        """
        template_path = self.template_dir / template_name
        
        if not template_path.exists():
            raise FileNotFoundError(
                f"Template not found: {template_path}\n"
                f"Expected templates in: {self.template_dir}"
            )
        
        with open(template_path, "r", encoding="utf-8") as f:
            return f.read()
    
    def substitute_params(self, template: str, params: Dict[str, Any]) -> str:
        """
        Substitute parameters into XML template.
        
        Replaces {key} with value for all key-value pairs in params.
        
        Args:
            template: XML template string
            params: Dictionary of {placeholder: value}
        
        Returns:
            XML with substituted parameters
        """
        result = template
        for key, value in params.items():
            placeholder = "{" + key + "}"
            result = result.replace(placeholder, str(value))
        
        return result
    
    def send_request(self, template_name: str, params: Dict[str, Any]) -> str:
        """
        Send request to ERP API.
        
        Process:
        1. Load XML template
        2. Substitute parameters
        3. Send POST request to ERP endpoint
        4. Return response XML
        
        Args:
            template_name: Name of XML template file
            params: Parameters to substitute in template
        
        Returns:
            Response XML from ERP server
        
        Raises:
            FileNotFoundError: If template not found
            requests.RequestException: If API call fails
        """
        # Load and substitute
        template = self.load_template(template_name)
        request_xml = self.substitute_params(template, params)
        
        # Send to ERP
        try:
            response = requests.post(
                self.endpoint,
                data=request_xml,
                headers={"Content-Type": "application/xml"},
                timeout=30
            )
            response.raise_for_status()
            return response.text
        
        except requests.RequestException as e:
            raise requests.RequestException(
                f"ERP API call failed: {str(e)}\n"
                f"Endpoint: {self.endpoint}\n"
                f"Make sure ERP is running and endpoint is correct."
            )


# Singleton instance for convenience
_client = None


def get_erp_client() -> ERPClient:
    """Get or create singleton ERP client instance."""
    global _client
    if _client is None:
        _client = ERPClient()
    return _client


def send_to_erp(template_name: str, params: Dict[str, Any]) -> str:
    """
    Convenience function to send request to ERP.
    
    Args:
        template_name: Name of XML template (e.g. "periodic_trend.xml")
        params: Parameters to substitute
    
    Returns:
        Response XML from ERP
    """
    client = get_erp_client()
    return client.send_request(template_name, params)
