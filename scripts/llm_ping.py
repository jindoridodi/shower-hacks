from apps.api.config import get_settings
from apps.api.services.openai_compatible_text_model import OpenAICompatibleTextModel


def main() -> int:
    model = OpenAICompatibleTextModel(get_settings())
    try:
        response = model.generate("Reply with exactly: LLM_OK").strip()
    finally:
        model.close()

    if response != "LLM_OK":
        print(f"LLM ping failed: received {response!r}")
        return 1

    print("LLM ping succeeded: LLM_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
