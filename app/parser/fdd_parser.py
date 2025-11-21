import json
import re
import logging
from typing import Dict, Any

logger = logging.getLogger("fdd_parser")
logging.basicConfig(level=logging.INFO)

class FDDParser:

    # Match: SECTION: 1.
    SECTION_REGEX = r"SECTION:\s*(\d+)\."

    def __init__(self, mapping_path: str):
        with open(mapping_path, "r", encoding="utf-8") as f:
            self.mapping = json.load(f)

    def extract_fsd_payloads(self, payload: dict) -> Dict[str, Dict[str, Any]]:
        udd_text = payload.get("FDD", "")
        udd_sections = self._split_numbers_only(udd_text)

        logger.info("📚 Total parsed UDD sections = %d", len(udd_sections))
        logger.info("🔢 Sections found: %s", list(udd_sections.keys()))

        final_output = {}

        for fsd_section, config in self.mapping.items():
            src_nums = config.get("from_udd_sections", [])
            logger.info(f"\n===== 📝 Mapping for FSD Section: {fsd_section} =====")
            logger.info(f"➡️  Source section numbers: {src_nums}")

            merged = ""

            for num in src_nums:
                if num in udd_sections:
                    logger.info(f"   ✓ Adding UDD Section {num} (len={len(udd_sections[num])})")
                    merged += udd_sections[num] + "\n\n"
                else:
                    logger.info(f"   ⚠️ Section {num} not found in UDD")

            logger.info(f"   📦 Final merged content length = {len(merged.strip())}")

            final_output[fsd_section] = {"content": merged.strip()}

        return final_output


    def _split_numbers_only(self, text: str) -> Dict[str, str]:
        """
        Split purely on SECTION: <num>. and ignore title text.
        This handles cases where title merges with content.
        Example:
        SECTION: 1. PurposeThis doc...
        SECTION: 2. ScopeText...
        """
        sections = {}

        matches = list(re.finditer(self.SECTION_REGEX, text))

        logger.info(f"Found {len(matches)} SECTION headers")

        for i, match in enumerate(matches):
            sec_num = match.group(1).strip()
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            content = text[start:end].strip()

            logger.info(f"   ➕ Parsed SECTION {sec_num}: (content_len={len(content)})")

            sections[sec_num] = content

        logger.info("📚 Finished parsing UDD into numbered sections.\n")

        return sections
