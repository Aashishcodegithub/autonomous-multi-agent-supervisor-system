#tools/get_report_tool.py
import requests
import xml.etree.ElementTree as ET
from langchain.tools import tool
from dotenv import load_dotenv
import os

load_dotenv()
ERP_URL = os.getenv("ERP_HTTP_HOST")


def build_report_envelope(report_name: str, company_name: str) -> str:
    """
    EXACT template that matches your working Postman request.
    This works for all reports in your ERP version.
    """
    def esc(s):
        if s is None:
            return ''
        return str(s).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

    rid = esc(report_name)
    cname = esc(company_name)

    return f"""
<ENVELOPE>
  <HEADER>
    <TALLYREQUEST>Export Data</TALLYREQUEST>
  </HEADER>
  <BODY>
    <EXPORTDATA>
      <REQUESTDESC>
        <REPORTNAME>{rid}</REPORTNAME>
        <STATICVARIABLES>
            <SVCurrentCompany>{cname}</SVCurrentCompany>
        </STATICVARIABLES>
      </REQUESTDESC>
    </EXPORTDATA>
  </BODY>
</ENVELOPE>
""".strip()


# ---------------------------------------------------------
# UPDATED xml_to_dict → supports repeated XML tags properly
# ---------------------------------------------------------
def xml_to_dict(elem):
    """
    Converts XML elements into Python dicts.
    Handles multiple repeated tags by converting them to lists.
    """
    d = {}

    for child in list(elem):
        # Recursively parse children OR read text
        child_value = (
            xml_to_dict(child)
            if len(list(child)) > 0
            else child.text
        )

        # If tag already present → convert to list
        if child.tag in d:
            if not isinstance(d[child.tag], list):
                d[child.tag] = [d[child.tag]]  # convert existing to list
            d[child.tag].append(child_value)
        else:
            d[child.tag] = child_value

    return d


@tool("get_report")
def get_report(company_name: str, report_name: str):
    """
    Fetch report from ERP using your working Postman XML format.
    """

    if not ERP_URL:
        return {"error": "Missing ERP_HTTP_HOST in .env"}

    xml_payload = build_report_envelope(report_name, company_name)

    try:
        response = requests.post(ERP_URL, data=xml_payload)
    except Exception as e:
        return {"error": f"HTTP connection failed: {str(e)}"}

    raw_xml = response.text.strip()

    print("\n========== RAW XML FROM ERP ==========")
    print(raw_xml)
    print("========================================\n")

    if not raw_xml:
        return {"error": "ERP returned an empty response"}

    # Try XML parsing → if fails, return raw XML
    try:
        root = ET.fromstring(raw_xml)
        parsed = xml_to_dict(root)
        return parsed
    except:
        return {"raw": raw_xml}
