"""
OpenAI API client for AI operations
"""
import logging
from typing import Optional, Dict, Any
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class OpenAIClient:
    """
    OpenAI API client for classification and summarization.
    """

    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)

    async def complete(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "gpt-4o-mini",
        temperature: float = 0.2,
        max_tokens: int = 1000,
        response_format: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Get completion from OpenAI.

        Args:
            system_prompt: System message
            user_prompt: User message
            model: Model to use
            temperature: Sampling temperature
            max_tokens: Maximum tokens in response
            response_format: Response format (e.g., {"type": "json_object"})

        Returns:
            Response text
        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        kwargs = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        if response_format:
            kwargs["response_format"] = response_format

        try:
            response = await self.client.chat.completions.create(**kwargs)
            return response.choices[0].message.content or ""

        except Exception as e:
            logger.error(f"OpenAI API error: {e}")
            raise

    async def classify_email(
        self,
        subject: str,
        body: str,
        short_id: str
    ) -> Dict[str, Any]:
        """
        Classify an email into a handover category.

        Returns dict with: shortId, category, summary
        """
        import json

        system_prompt = "You are a precise maritime email subject classifier."

        user_prompt = f"""
You are a maritime handover classification and summarisation assistant.

Your task:
1. Categorise the following EMAIL into ONE of the official handover categories.
2. Write a short professional summary (under 40 words) describing the main point or action.
3. Use 2nd person tone ("You need to...").
4. Output strict JSON only.

Choose only from this exact list of categories:
- Electrical
- Projects
- Financial
- Galley Laundry
- Risk
- Admin
- Fire Safety
- Tenders
- Logistics
- Deck
- General Outstanding

Rules:
- Choose exactly ONE category.
- Never invent or modify category names.
- Keep the summary factual and concise.
- Output must strictly follow the schema.

Schema:
{{
  "shortId": "{short_id}",
  "category": "one of the categories above",
  "summary": "concise professional summary under 40 words"
}}

Email subject: {subject}
Email body (first 100 words): {' '.join(body.split()[:100])}

Output (strict JSON only):
"""

        response = await self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model="gpt-4o-mini",
            temperature=0.2,
            max_tokens=300,
            response_format={"type": "json_object"}
        )

        return json.loads(response)

    async def merge_handover_notes(
        self,
        subject_group: str,
        category: str,
        notes: str
    ) -> Dict[str, Any]:
        """
        Merge multiple email summaries into a single handover entry.

        Returns dict with: handover.subject, handover.summary, handover.actions
        """
        import json

        system_prompt = "You are a precise maritime handover summarisation assistant that merges multiple notes into clear, structured JSON output."

        user_prompt = f"""
You are a maritime engineering handover assistant.

Context:
You will receive multiple email summaries about the same subject group: "{subject_group}"
within the category "{category}". Your role is to produce a **concise, professional, and action-oriented handover entry**.

Instructions:
1. **Merge notes** that are clearly duplicates or reworded versions of the same point.
2. **Preserve distinctions** when they differ by sender, attachments, or time-specific details.
3. **Summarise precisely** — avoid vague or filler language.
4. **Use second person** ("You need to...").
5. **Actions:** Extract all required work as discrete items with priority: CRITICAL, HIGH, or NORMAL.
6. **Keep subject and summary concise and professional**.
7. **Output strict JSON only**.

Schema:
{{
  "handover": {{
    "subject": "string (concise, cleaned-up title)",
    "summary": "string (2–3 sentences summarising the situation)",
    "actions": [
      {{ "priority": "CRITICAL" | "HIGH" | "NORMAL", "task": "string", "subTasks": [] }}
    ]
  }}
}}

Input Notes:
{notes}

Output (strict JSON only):
"""

        response = await self.complete(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            model="gpt-4o-mini",
            temperature=0.1,
            max_tokens=2000,
            response_format={"type": "json_object"}
        )

        return json.loads(response)
