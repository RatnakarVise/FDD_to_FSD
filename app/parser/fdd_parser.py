import json
import os
import re
from typing import Dict, Any

class FDDParser:

    SECTION_PATTERN = r"SECTION:\s*(\d+)\.\s*(.*)"

    def __init__(self, mapping_path: str):
        with open(mapping_path, "r", encoding="utf-8") as f:
            self.mapping = json.load(f)

    # ------------------------------------------------------------------
    # Main public function → converts payload["FDD"] to per-FSD payload
    # ------------------------------------------------------------------
    def extract_fsd_payloads(self, payload: dict) -> Dict[str, Dict[str, Any]]:

        udd_text = payload.get("FDD", "")
        udd_sections = self._split_udd_into_sections(udd_text)

        final_output = {}

        for fsd_section, config in self.mapping.items():
            source_sections = config.get("from_udd_sections", [])

            merged_text = ""

            for s in source_sections:
                if s in udd_sections:
                    merged_text += udd_sections[s].strip() + "\n\n"

            final_output[fsd_section] = {
                "content": merged_text.strip()
            }

        return final_output

    # ------------------------------------------------------------------
    # SPLITTING UDD BASED ON:
    # SECTION: <number>. <title>
    # ------------------------------------------------------------------
    def _split_udd_into_sections(self, text: str) -> Dict[str, str]:

        lines = text.splitlines()

        sections = {}
        current_title = None
        buffer = []

        for line in lines:
            # Detect section header
            match = re.match(self.SECTION_PATTERN, line.strip())
            if match:
                # Save previous section
                if current_title and buffer:
                    sections[current_title] = "\n".join(buffer).strip()

                # Reset buffer for new section
                section_number = match.group(1)
                section_title = match.group(2).strip()

                current_title = section_title
                buffer = []
            else:
                if current_title:
                    buffer.append(line)

        # Add last section
        if current_title and buffer:
            sections[current_title] = "\n".join(buffer).strip()

        return sections
