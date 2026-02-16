import os
import requests
import json
import random
from enum import Enum
from typing import Optional, Dict, Any

class LLMProvider(str, Enum):
    LOCAL = "local"       # Ollama (free)
    OPENAI = "openai"     # GPT-4o
    ANTHROPIC = "anthropic"  # Claude

class TaskType(str, Enum):
    # Local-Friendly (Low Creativity, High Logic/Constraint)
    HOOK_REWRITE = "hook_rewrite"
    CLASSIFY_ARCHETYPE = "classify_archetype"
    QA_CHECK = "qa_check"
    CAPTION_GEN = "caption_gen"

    # Premium-Only (High Creativity/Nuance)
    SCRIPT_WRITING = "script_writing"
    POETRY_WRITING = "poetry_writing"
    PSYCHOLOGY_FACT = "psychology_fact"
    FINAL_POLISH = "final_polish"


def _is_real_key(key: str) -> bool:
    """Reject placeholder keys like 'sk-...', '...', 'your-key-here', etc."""
    if not key or len(key) < 10:
        return False
    placeholders = ["sk-...", "...", "your-key", "xxx", "placeholder", "CHANGE_ME"]
    return not any(p in key for p in placeholders)


# Mode-aware system prompts that produce better LLM output
SYSTEM_PROMPTS = {
    TaskType.HOOK_REWRITE: (
        "You are a viral content writer for dark motivational short-form videos. "
        "You write brutal, emotionally charged single-line hooks that stop the scroll. "
        "Output ONLY the hook text. No quotes, no explanations, no labels. One line only."
    ),
    TaskType.SCRIPT_WRITING: (
        "You write short, confrontational truths for motivational video captions. "
        "Every sentence must hit hard in under 10 words. "
        "Output ONLY the sentence. No quotes, no labels, no explanations."
    ),
    TaskType.POETRY_WRITING: (
        "You write dark, stoic micro-poetry. Raw and visceral. No cliches. "
        "Each line under 6 words. Output ONLY the poem lines, one per line. Nothing else."
    ),
    TaskType.PSYCHOLOGY_FACT: (
        "You write concise psychological insights in 3 parts separated by | characters. "
        "Part 1: the problem (under 10 words). Part 2: the psychology (name a real concept, under 12 words). "
        "Part 3: the fix (actionable, under 8 words). Output ONLY the three parts separated by pipes."
    ),
}


class LLMGateway:
    """
    Central Router for all Text Generation.
    V5.2: Validates API keys, supports Anthropic/Claude, proper system prompts,
    cleans LLM output to ensure single-line captions.
    """

    def __init__(self):
        # Local LLM config
        self.use_local = os.getenv("USE_LOCAL_LLM", "false").lower() == "true"
        self.local_url = os.getenv("OLLAMA_URL", "http://ollama:11434/api/generate")
        self.local_model = os.getenv("OLLAMA_MODEL", "qwen2.5:7b")

        # OpenAI config
        raw_openai = os.getenv("OPENAI_API_KEY", "").strip()
        self.openai_key = raw_openai if _is_real_key(raw_openai) else ""
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o")

        # Anthropic/Claude config
        raw_anthropic = os.getenv("ANTHROPIC_API_KEY", "").strip()
        self.anthropic_key = raw_anthropic if _is_real_key(raw_anthropic) else ""
        self.anthropic_model = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

        # Log what's available
        providers = []
        if self.use_local:
            providers.append("Ollama (local)")
        if self.anthropic_key:
            providers.append(f"Anthropic (...{self.anthropic_key[-4:]})")
        if self.openai_key:
            providers.append(f"OpenAI (...{self.openai_key[-4:]})")
        if providers:
            print(f"[LLMGateway] Available providers: {', '.join(providers)}")
        else:
            print("[LLMGateway] WARNING: No API keys configured. Using mock library only.")

    def generate(self, task_type: TaskType, prompt: str, system_prompt: str = "") -> str:
        """
        Generate text with automatic provider routing, fallback chain, and output cleaning.
        """
        # Use task-specific system prompt if none provided
        if not system_prompt:
            system_prompt = SYSTEM_PROMPTS.get(task_type, "")

        provider = self._decide_provider(task_type)

        # Try the chain: selected provider -> fallback providers -> mock
        result = None

        if provider == LLMProvider.LOCAL:
            result = self._try_local(prompt, system_prompt)
            if result:
                return self._clean_output(result, task_type)

        if provider == LLMProvider.ANTHROPIC or (result is None and self.anthropic_key):
            result = self._try_anthropic(prompt, system_prompt)
            if result:
                return self._clean_output(result, task_type)

        if provider == LLMProvider.OPENAI or (result is None and self.openai_key):
            result = self._try_openai(prompt, system_prompt)
            if result:
                return self._clean_output(result, task_type)

        # Mock fallback
        return self._mock_generate(prompt, task_type)

    def _decide_provider(self, task_type: TaskType) -> LLMProvider:
        """Route tasks to the best available provider."""
        # Local tasks (cheap, fast) -> Ollama if available
        local_tasks = [TaskType.HOOK_REWRITE, TaskType.CLASSIFY_ARCHETYPE, TaskType.QA_CHECK]
        if self.use_local and task_type in local_tasks:
            return LLMProvider.LOCAL

        # Premium tasks -> prefer Anthropic (better creative writing), fallback to OpenAI
        if self.anthropic_key:
            return LLMProvider.ANTHROPIC
        if self.openai_key:
            return LLMProvider.OPENAI

        # No keys: will fall through to mock
        return LLMProvider.OPENAI

    def _try_local(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Try Ollama local LLM."""
        if not self.use_local:
            return None
        try:
            print(f"[LLMGateway] -> Ollama ({self.local_model})...")
            payload = {
                "model": self.local_model,
                "prompt": f"System: {system_prompt}\nUser: {prompt}" if system_prompt else prompt,
                "stream": False,
                "options": {"temperature": 0.7}
            }
            resp = requests.post(self.local_url, json=payload, timeout=15)
            resp.raise_for_status()
            return resp.json().get("response", "")
        except Exception as e:
            print(f"[LLMGateway] Ollama failed: {e}")
            return None

    def _try_anthropic(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Try Anthropic Claude API."""
        if not self.anthropic_key:
            return None
        try:
            print(f"[LLMGateway] -> Anthropic ({self.anthropic_model})...")
            headers = {
                "x-api-key": self.anthropic_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            }
            payload = {
                "model": self.anthropic_model,
                "max_tokens": 256,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.8,
            }
            if system_prompt:
                payload["system"] = system_prompt

            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers, json=payload, timeout=20
            )
            resp.raise_for_status()
            data = resp.json()
            # Extract text from content blocks
            content = data.get("content", [])
            if content and isinstance(content, list):
                return content[0].get("text", "")
            return ""
        except Exception as e:
            print(f"[LLMGateway] Anthropic failed: {e}")
            return None

    def _try_openai(self, prompt: str, system_prompt: str) -> Optional[str]:
        """Try OpenAI API."""
        if not self.openai_key:
            return None
        try:
            print(f"[LLMGateway] -> OpenAI ({self.openai_model})...")
            headers = {
                "Authorization": f"Bearer {self.openai_key}",
                "Content-Type": "application/json"
            }
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": self.openai_model,
                "messages": messages,
                "temperature": 0.8,
                "max_tokens": 256,
            }
            resp = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers, json=payload, timeout=20
            )
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"[LLMGateway] OpenAI failed: {e}")
            return None

    def _clean_output(self, text: str, task_type: TaskType) -> str:
        """
        Clean LLM output: strip quotes, labels, extra whitespace.
        For non-poetry tasks, collapse to single line.
        """
        text = text.strip()

        # Remove common LLM prefixes
        prefixes = [
            "Generated Hook:", "Hook:", "Here's", "Here is",
            "Sure,", "Sure!", "Output:", "Result:",
        ]
        for prefix in prefixes:
            if text.lower().startswith(prefix.lower()):
                text = text[len(prefix):].strip()

        # Strip surrounding quotes
        if (text.startswith('"') and text.endswith('"')) or \
           (text.startswith("'") and text.endswith("'")):
            text = text[1:-1].strip()

        # For poetry, preserve newlines between lines but clean each line
        if task_type == TaskType.POETRY_WRITING:
            lines = [line.strip().strip('"').strip("'").strip('-').strip('*').strip()
                     for line in text.split('\n') if line.strip()]
            return '\n'.join(lines)

        # For everything else: collapse to single line
        text = ' '.join(text.split())
        return text

    def _mock_generate(self, prompt: str, task_type: TaskType) -> str:
        """High-quality mock library for when no API keys are available."""
        print(f"[LLMGateway] Using mock library (no API keys available)")

        if task_type == TaskType.HOOK_REWRITE or "hook" in prompt.lower():
            return random.choice([
                "Pain is the only honest teacher left.",
                "Your comfort zone has a body count.",
                "Discipline is silent. Regret is loud.",
                "The truth you dodge will find you.",
                "Fear dressed up as logic stopped you.",
                "Loneliness built what crowds never could.",
                "Silence taught me more than people did.",
                "The dark showed me who I was.",
                "You burned out chasing someone else's fire.",
                "Your struggle is not a weakness. It is data.",
            ])

        if task_type == TaskType.SCRIPT_WRITING or "harsh" in prompt.lower() or "brutal" in prompt.lower():
            return random.choice([
                "Nobody is coming. Build it yourself.",
                "You are not stuck. You are scared.",
                "Your excuses sound just like everyone else.",
                "Stop performing discipline. Start practicing it.",
                "Motivation lied. Routine delivered.",
                "The gap between you and them is reps.",
                "You do not need more time. You need focus.",
                "Comfort cost you three years. Count them.",
            ])

        if task_type == TaskType.POETRY_WRITING or "poem" in prompt.lower():
            return random.choice([
                "Silence was my first language.\nPain was the second.\nI unlearned both.\nNow I only speak in scars.",
                "The dark is not your enemy.\nIt is the classroom.\nSit down.\nThe lesson already started.",
                "I stopped chasing light.\nI became it.\nNot for them.\nFor the version who almost quit.",
                "Alone is not lonely.\nAlone is clarity.\nCrowds are noise.\nNoise is where truth dies.",
                "The storm taught patience.\nThe cold taught presence.\nThe dark taught vision.\nI stopped running from teachers.",
            ])

        if task_type == TaskType.PSYCHOLOGY_FACT or "psych" in prompt.lower() or "insight" in prompt.lower():
            return random.choice([
                "Your brain treats change as a threat|It is called status quo bias|Make the first step impossibly small",
                "You confuse being busy with progress|It is called action bias|Sit with the problem before reacting",
                "You remember failures louder than wins|It is called negativity bias|Write down three wins every night",
                "You wait for motivation to start|Motivation follows action not the reverse|Start before you are ready",
                "You overvalue what you might lose|It is called loss aversion|Reframe loss as tuition not punishment",
            ])

        return "Your comfort zone is where growth goes to die."
