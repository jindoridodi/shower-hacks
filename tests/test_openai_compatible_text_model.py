import httpx
import unittest

from apps.api.config import Settings
from apps.api.services.openai_compatible_text_model import OpenAICompatibleTextModel
from apps.api.services.text_model import TextModelError


class OpenAICompatibleTextModelTests(unittest.TestCase):
    def setUp(self) -> None:
        self.settings = Settings(
            llm_api_key="test-key",
            llm_base_url="https://llm.test/v1",
            llm_model="test-model",
            llm_timeout_seconds=5,
        )

    def test_returns_chat_completion_content(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            self.assertEqual(str(request.url), "https://llm.test/v1/chat/completions")
            self.assertEqual(request.headers["Authorization"], "Bearer test-key")
            return httpx.Response(
                200,
                json={"choices": [{"message": {"content": "LLM_OK"}}]},
                request=request,
            )

        client = httpx.Client(transport=httpx.MockTransport(handler))
        model = OpenAICompatibleTextModel(self.settings, client=client)
        self.assertEqual(model.generate("ping"), "LLM_OK")
        client.close()

    def test_rejects_provider_errors(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, request=request)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        model = OpenAICompatibleTextModel(self.settings, client=client)
        with self.assertRaisesRegex(TextModelError, "status 401"):
            model.generate("ping")
        client.close()

    def test_rejects_missing_response_content(self) -> None:
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"choices": []}, request=request)

        client = httpx.Client(transport=httpx.MockTransport(handler))
        model = OpenAICompatibleTextModel(self.settings, client=client)
        with self.assertRaisesRegex(TextModelError, "message content"):
            model.generate("ping")
        client.close()


if __name__ == "__main__":
    unittest.main()
