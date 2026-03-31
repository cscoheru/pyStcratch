"""
AI-powered article creation engine.
"""
import os
from typing import Dict, List, Optional
from loguru import logger

try:
    from zhipuai import ZhipuAI
except ImportError:
    logger.warning("zhipuai package not installed. Run: pip install zhipuai")
    ZhipuAI = None

from creator.prompt_templates import PromptTemplates


class ArticleCreator:
    """AI-powered article creation using Zhipu GLM."""

    def __init__(self):
        self.api_key = os.getenv("ZHIPUAI_API_KEY")
        self.model = os.getenv("ZHIPU_MODEL", "glm-4")
        self.client = None

        if self.api_key and ZhipuAI:
            self.client = ZhipuAI(api_key=self.api_key)
            logger.info(f"ZhipuAI client initialized: model={self.model}")
        else:
            logger.warning("ZHIPUAI_API_KEY not set or package not installed")

    async def create_article(self, request: Dict) -> Dict:
        """
        Create an article based on the request parameters.

        Args:
            request: Dict with topic, reference_ids, style, length, title_type, etc.

        Returns:
            Dict with created article data
        """
        if not self.client:
            return self._mock_article(request)

        try:
            # Get reference articles if provided
            reference_articles = []
            if request.get("reference_ids"):
                from storage.supabase_client import SupabaseClient
                supabase = SupabaseClient()
                reference_articles = await supabase.get_articles_by_ids(request["reference_ids"])

            # Build prompt
            prompt = PromptTemplates.build_creation_prompt(
                topic=request.get("topic", ""),
                reference_articles=reference_articles,
                style=request.get("style", "professional"),
                length=request.get("length", "medium"),
                title_type=request.get("title_type", "catchy"),
                target_audience=request.get("target_audience"),
                tips=request.get("tips")
            )

            # Call Zhipu GLM API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )

            # Extract generated content
            content = response.choices[0].message.content

            # Parse title and content
            title = self._extract_title(content)
            article_content = self._extract_content(content)

            return {
                "topic": request.get("topic", ""),
                "title": title,
                "content": article_content,
                "style": request.get("style", "professional"),
                "length": request.get("length", "medium"),
                "word_count": self._calculate_word_count(article_content),
                "reference_count": len(reference_articles)
            }

        except Exception as e:
            logger.error(f"Failed to create article: {e}")
            return self._mock_article(request)

    def _extract_title(self, content: str) -> str:
        """Extract title from generated content."""
        lines = content.strip().split("\n")

        # Look for TITLE: prefix
        for line in lines:
            line = line.strip()
            if line.upper().startswith("TITLE:"):
                return line.replace("TITLE:", "").replace("Title:", "").strip()

        # First non-empty line as fallback
        for line in lines:
            if line.strip():
                return line.strip()[:100]

        return "Untitled"

    def _extract_content(self, content: str) -> str:
        """Extract article content without title."""
        lines = content.strip().split("\n")

        # Skip title line if present
        start_idx = 0
        for i, line in enumerate(lines):
            if line.strip().upper().startswith("TITLE:"):
                start_idx = i + 1
                break

        # Join remaining lines
        article_content = "\n".join(lines[start_idx:]).strip()

        # Remove separator lines
        article_content = article_content.split("---")[0].strip()

        return article_content

    def _calculate_word_count(self, content: str) -> int:
        """Calculate word count for content."""
        if not content:
            return 0

        # Simple word count (split by whitespace)
        words = content.split()
        return len(words)

    def _mock_article(self, request: Dict) -> Dict:
        """Generate a mock article when AI is unavailable."""
        topic = request.get("topic", "Unknown Topic")
        style = request.get("style", "professional")

        mock_content = f"""
# {topic}

This is a placeholder article about "{topic}".

## Introduction

{topic} is an important subject that deserves attention. In this article, we will explore various aspects and considerations.

## Main Points

1. First, it's important to understand the fundamentals.
2. Second, we should consider practical applications.
3. Finally, we must think about future implications.

## Conclusion

In summary, {topic} offers many opportunities for exploration and growth.

---

*Note: This is a placeholder article. To enable AI-generated content, configure ZHIPUAI_API_KEY.*
        """.strip()

        return {
            "topic": topic,
            "title": f"Understanding {topic}",
            "content": mock_content,
            "style": style,
            "length": request.get("length", "medium"),
            "word_count": self._calculate_word_count(mock_content),
            "reference_count": 0,
            "is_mock": True
        }
