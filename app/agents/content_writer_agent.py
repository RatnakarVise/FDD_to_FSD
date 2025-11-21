import os
import json
import logging
from typing import Any, Dict, List
from dotenv import load_dotenv
from openai import OpenAI

from app.parser.fdd_parser import FDDParser

# ---------------------------------------------------------
# LOGGER SETUP
# ---------------------------------------------------------
logger = logging.getLogger("content_writer_agent")
logging.basicConfig(level=logging.INFO)


# ---------------------------------------------------------
# LOAD .env (Always from project root)
# ---------------------------------------------------------
dotenv_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=dotenv_path)
langchain_api_key = os.getenv("LANGCHAIN_API_KEY")
openai_api_key = os.getenv("OPENAI_API_KEY")
if langchain_api_key:
    os.environ["LANGCHAIN_API_KEY"] = langchain_api_key
if openai_api_key:
    os.environ["OPENAI_API_KEY"] = openai_api_key
os.environ["LANGCHAIN_TRACING_V2"] = "true"

# Print API key for debugging (masked)
logger.info(f"🔐 OPENAI_API_KEY Loaded: {openai_api_key[:30] + '...' if openai_api_key else '❌ None'}")
# logger.info(f"🔐 LANGCHAIN_API_KEY Loaded: {LANGCHAIN_KEY[:6] + '...' if LANGCHAIN_KEY else '❌ None'}")

# Hard fail if missing API key
if not openai_api_key:
    raise Exception("❌ OPENAI_API_KEY is missing! Check your .env file.")


# ---------------------------------------------------------
# CONSTANTS
# ---------------------------------------------------------
OPENAI_MODEL = "gpt-4.1"
BASE_DIR = os.path.dirname(__file__)

MAPPING_PATH = os.path.join(BASE_DIR, "..", "mapping", "mapping.json")
TEMPLATE_PATH = os.path.join(BASE_DIR, "RAG_Knowledge_Base.txt")


# ---------------------------------------------------------
# TEMPLATE LOADER
# ---------------------------------------------------------
def load_sections_from_template(template_file: str) -> list:
    sections = []
    with open(template_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    current_title, current_content = None, []

    for line in lines:
        line = line.rstrip()

        if line.startswith("#"):  # Section Title
            if current_title and current_content:
                sections.append({
                    "title": current_title,
                    "content": "\n".join(current_content).strip()
                })
            current_title = line.lstrip("#").strip()
            current_content = []
        else:
            if current_title:
                current_content.append(line)

    if current_title and current_content:
        sections.append({"title": current_title, "content": "\n".join(current_content).strip()})

    return sections


# ---------------------------------------------------------
# MAIN AGENT CLASS
# ---------------------------------------------------------
class ContentWriterAgent:

    def __init__(self, model=OPENAI_MODEL, template_path=TEMPLATE_PATH):
        self.model = model

        # Correct OpenAI Client Initialization
        self.openai_client = OpenAI(api_key=openai_api_key)

        # Log model + client status
        logger.info(f"🤖 OpenAI client initialized with model: {self.model}")

        # Load template sections
        self.template_sections = load_sections_from_template(template_path)
        logger.info(f"📄 Loaded {len(self.template_sections)} template sections.")

        # Load dynamic FDD→FSD mapping parser
        self.parser = FDDParser(MAPPING_PATH)
        logger.info("🔧 FDDParser initialized.")

        self.results = []


    # -----------------------------------------------------
    # MAIN RUN FUNCTION
    # -----------------------------------------------------
    def run(self, payload: Dict[str, Any]) -> List[Dict[str, str]]:
        logger.info("🚀 Starting FSD generation...")

        parsed_payload = self.parser.extract_fsd_payloads(payload)
        logger.info("🧠 Parsed FDD into section-wise payloads.")

        self.results = []

        for sec in self.template_sections:
            section_name = sec["title"]
            bible = sec["content"]
            sec_payload = parsed_payload.get(section_name, {})

            logger.info(f"✏️ Generating content for section: {section_name}")

            content = self.generate_section_content(section_name, bible, sec_payload)

            self.results.append({"section_name": section_name, "content": content})

        logger.info("✅ All sections generated.")
        return self.results


    # -----------------------------------------------------
    # LLM CALL PER SECTION
    # -----------------------------------------------------
    def generate_section_content(self, title: str, bible: str, payload: dict) -> str:

        prompt = f"""
You are an expert SAP ABAP solution design writer.

SECTION: {title}

BIBLE (Authoritative Guidance):
{bible}

PAYLOAD:
{json.dumps(payload, indent=2)}

INSTRUCTIONS:
- Follow the BIBLE strictly.
- Use ONLY the payload fields.
- Do NOT invent details.
- Do NOT hallucinate.
- Return ONLY the section body without headings.
"""

        try:
            response = self.openai_client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.1,
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            logger.error(f"❌ LLM error for section '{title}': {e}")
            return f"[ERROR generating section '{title}': {e}]"
