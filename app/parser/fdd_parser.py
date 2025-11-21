import json
import re
from typing import Dict, Any

class FDDParser:

    # Matches:
    # SECTION: 1. PurposeThis is content ...
    SECTION_SPLIT_REGEX = r"SECTION:\s*\d+\.\s*"

    # Matches the title portion:
    SECTION_HEADER_REGEX = r"SECTION:\s*(\d+)\.\s*([A-Za-z ]+)"

    def __init__(self, mapping_path: str):
        with open(mapping_path, "r", encoding="utf-8") as f:
            self.mapping = json.load(f)

    # Main method
    def extract_fsd_payloads(self, payload: dict) -> Dict[str, Dict[str, Any]]:
        udd_text = payload.get("FDD", "")
        udd_sections = self._split_sections(udd_text)

        final_result = {}
        for fsd_section, config in self.mapping.items():
            source_sections = config.get("from_udd_sections", [])

            merged_text = ""

            for s in source_sections:
                if s in udd_sections:
                    merged_text += udd_sections[s] + "\n\n"

            final_result[fsd_section] = {
                "content": merged_text.strip()
            }

        return final_result

    # FIXED parser
    def _split_sections(self, text: str) -> Dict[str, str]:
        sections = {}
        
        # Find all SECTION headers with title
        headers = list(re.finditer(self.SECTION_HEADER_REGEX, text))

        for i, match in enumerate(headers):
            sec_number = match.group(1)
            sec_title = match.group(2).strip()

            start = match.end()  # content starts after header
            end = headers[i + 1].start() if i + 1 < len(headers) else len(text)

            content = text[start:end].strip()
            sections[sec_title] = content

        return sections
