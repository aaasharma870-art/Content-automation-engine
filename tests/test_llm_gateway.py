import unittest
from unittest.mock import patch, MagicMock
import os
from shared.llm_gateway import LLMGateway, TaskType, LLMProvider

class TestLLMGateway(unittest.TestCase):
    
    def setUp(self):
        # Force Local LLM enabled for testing
        os.environ["USE_LOCAL_LLM"] = "true"
        self.gateway = LLMGateway()

    def tearDown(self):
        if "USE_LOCAL_LLM" in os.environ:
            del os.environ["USE_LOCAL_LLM"]

    def test_routing_rewrite_to_local(self):
        """Test that cheap tasks function route to LOCAL"""
        provider = self.gateway._decide_provider(TaskType.HOOK_REWRITE)
        self.assertEqual(provider, LLMProvider.LOCAL)

    def test_routing_script_to_premium(self):
        """Test that creative tasks route to OPENAI"""
        provider = self.gateway._decide_provider(TaskType.SCRIPT_WRITING)
        self.assertEqual(provider, LLMProvider.OPENAI)

    @patch('shared.llm_gateway.requests.post')
    def test_local_call_success(self, mock_post):
        """Test successful local call"""
        mock_resp = MagicMock()
        mock_resp.json.return_value = {"response": "Local Response"}
        mock_resp.status_code = 200
        mock_post.return_value = mock_resp

        res = self.gateway.generate(TaskType.HOOK_REWRITE, "Test Prompt")
        self.assertEqual(res, "Local Response")
        # Verify it called the OLLAMA URL
        self.assertIn("11434", mock_post.call_args[0][0])

    @patch('shared.llm_gateway.requests.post')
    def test_fallback_to_premium(self, mock_post):
        """Test fallback when local fails"""
        # Simulate Local Failure
        mock_post.side_effect = Exception("Ollama Down")
        
        # Patch internal _call_openai to avoid real API call
        with patch.object(self.gateway, '_call_openai', return_value="Fallback Response") as mock_openai:
            res = self.gateway.generate(TaskType.HOOK_REWRITE, "Test Prompt")
            
            # Should receive fallback response
            self.assertEqual(res, "Fallback Response")
            # Should have attempted local first
            mock_post.assert_called()
            # Should have called openai second
            mock_openai.assert_called()

if __name__ == '__main__':
    unittest.main()
