from __future__ import annotations

import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from planner.agent import OpenAIIntentInterpreter
from planner.llm_recommender import LLMRecommender


class FakeOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeTimeout:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs


class LLMConfigurationTest(unittest.TestCase):
    def _modules(self):
        return {
            "openai": SimpleNamespace(OpenAI=FakeOpenAI),
            "httpx": SimpleNamespace(Timeout=FakeTimeout),
        }

    def test_openai_compatible_proxy_uses_base_url(self):
        environment = {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "proxy-key",
            "OPENAI_BASE_URL": "https://proxy.example/v1",
        }
        with patch.dict(os.environ, environment, clear=True), patch.dict(
            sys.modules, self._modules()
        ):
            recommender = LLMRecommender()

        self.assertEqual("https://proxy.example/v1", recommender.client.kwargs["base_url"])

    def test_aihubmix_prefers_dedicated_key(self):
        environment = {
            "LLM_PROVIDER": "aihubmix",
            "OPENAI_API_KEY": "openai-key",
            "AIHUBMIX_API_KEY": "aihubmix-key",
            "OPENAI_BASE_URL": "https://aihubmix.example/v1",
        }
        with patch.dict(os.environ, environment, clear=True), patch.dict(
            sys.modules, self._modules()
        ):
            recommender = LLMRecommender()

        self.assertEqual("aihubmix-key", recommender.client.kwargs["api_key"])

    def test_conversational_agent_uses_same_aihubmix_credentials(self):
        environment = {
            "LLM_PROVIDER": "aihubmix",
            "OPENAI_API_KEY": "openai-key",
            "AIHUBMIX_API_KEY": "aihubmix-key",
            "OPENAI_BASE_URL": "https://aihubmix.example/v1",
        }
        with patch.dict(os.environ, environment, clear=True), patch.dict(
            sys.modules, {"openai": SimpleNamespace(OpenAI=FakeOpenAI)}
        ):
            interpreter = OpenAIIntentInterpreter()

        self.assertEqual("aihubmix-key", interpreter.client.kwargs["api_key"])
        self.assertEqual(
            "https://aihubmix.example/v1", interpreter.client.kwargs["base_url"]
        )

    def test_aihubmix_requires_base_url(self):
        environment = {
            "LLM_PROVIDER": "aihubmix",
            "AIHUBMIX_API_KEY": "aihubmix-key",
        }
        with patch.dict(os.environ, environment, clear=True), patch.dict(
            sys.modules, self._modules()
        ):
            with self.assertRaisesRegex(ValueError, "OPENAI_BASE_URL is required"):
                LLMRecommender()

    def test_conversational_agent_requires_aihubmix_base_url(self):
        environment = {
            "LLM_PROVIDER": "aihubmix",
            "AIHUBMIX_API_KEY": "aihubmix-key",
        }
        with patch.dict(os.environ, environment, clear=True), patch.dict(
            sys.modules, {"openai": SimpleNamespace(OpenAI=FakeOpenAI)}
        ):
            with self.assertRaisesRegex(ValueError, "OPENAI_BASE_URL is required"):
                OpenAIIntentInterpreter()

    def test_explicit_zero_temperature_is_preserved(self):
        environment = {
            "LLM_PROVIDER": "openai",
            "OPENAI_API_KEY": "openai-key",
            "LLM_TEMPERATURE": "0.7",
        }
        with patch.dict(os.environ, environment, clear=True), patch.dict(
            sys.modules, self._modules()
        ):
            recommender = LLMRecommender(temperature=0.0)

        self.assertEqual(0.0, recommender.temperature)


if __name__ == "__main__":
    unittest.main()
