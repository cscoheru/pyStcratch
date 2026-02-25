"""
Prompt templates for AI content creation.
"""
from typing import List, Dict, Optional


class PromptTemplates:
    """Templates for building AI prompts."""

    # Style instructions
    STYLE_INSTRUCTIONS = {
        "professional": """
You are writing in a professional, authoritative tone suitable for business or academic contexts.
Use formal language, precise terminology, and avoid slang.
Include data, statistics, or research findings where appropriate.
Maintain an objective, analytical perspective.
""",
        "casual": """
You are writing in a casual, conversational tone suitable for blogs or social media.
Use everyday language, relatable examples, and a friendly voice.
You can use personal anecdotes and lighter language.
Make the content engaging and easy to read.
""",
        "humorous": """
You are writing with humor and wit while maintaining informative value.
Use clever wordplay, light jokes, and funny observations.
Keep the humor appropriate and don't let it overshadow the main message.
Make the reader smile while they learn.
"""
    }

    # Length instructions
    LENGTH_INSTRUCTIONS = {
        "short": """
Target length: 300-500 words.
Be concise and to the point.
Focus on the most important information.
Avoid unnecessary elaboration.
""",
        "medium": """
Target length: 800-1200 words.
Provide balanced coverage of the topic.
Include main points with some elaboration.
Use examples to illustrate key concepts.
""",
        "long": """
Target length: 1500-2500 words.
Provide comprehensive coverage of the topic.
Include detailed explanations and multiple examples.
Explore nuances and various perspectives.
Add depth to each section.
"""
    }

    # Title type instructions
    TITLE_INSTRUCTIONS = {
        "catchy": """
Create attention-grabbing titles that spark curiosity.
Use power words, numbers, or provocative statements.
Make the reader want to click and read more.
Examples: "7 Secrets You Never Knew...", "The Shocking Truth About..."
""",
        "descriptive": """
Create clear, descriptive titles that accurately reflect content.
Use straightforward language that tells readers what to expect.
Include key topics or benefits.
Examples: "A Guide to Understanding...", "How to Improve Your..."
""",
        "question": """
Frame titles as questions that engage the reader.
Address common concerns or curiosities.
Make the reader feel the question is for them.
Examples: "Are You Making This Mistake?", "What if You Could...?"
"""
    }

    @staticmethod
    def build_creation_prompt(
        topic: str,
        reference_articles: Optional[List[Dict]] = None,
        style: str = "professional",
        length: str = "medium",
        title_type: str = "catchy",
        target_audience: Optional[str] = None,
        tips: Optional[List[str]] = None
    ) -> str:
        """
        Build a comprehensive prompt for article creation.

        Args:
            topic: Article topic
            reference_articles: Reference articles for context
            style: Writing style
            length: Article length
            title_type: Title style
            target_audience: Target audience description
            tips: Additional tips or requirements

        Returns:
            Complete prompt string
        """
        prompt_parts = [
            "# Article Creation Task",
            "",
            "You are an expert content creator. Write an article based on the following specifications:",
            "",
        ]

        # Topic
        prompt_parts.extend([
            "## Topic",
            topic,
            ""
        ])

        # Style
        style_instruction = PromptTemplates.STYLE_INSTRUCTIONS.get(style, PromptTemplates.STYLE_INSTRUCTIONS["professional"])
        prompt_parts.extend([
            "## Writing Style",
            style_instruction.strip(),
            ""
        ])

        # Length
        length_instruction = PromptTemplates.LENGTH_INSTRUCTIONS.get(length, PromptTemplates.LENGTH_INSTRUCTIONS["medium"])
        prompt_parts.extend([
            "## Length",
            length_instruction.strip(),
            ""
        ])

        # Title
        title_instruction = PromptTemplates.TITLE_INSTRUCTIONS.get(title_type, PromptTemplates.TITLE_INSTRUCTIONS["catchy"])
        prompt_parts.extend([
            "## Title Requirements",
            title_instruction.strip(),
            ""
        ])

        # Target audience
        if target_audience:
            prompt_parts.extend([
                "## Target Audience",
                target_audience,
                ""
            ])

        # Reference articles
        if reference_articles:
            prompt_parts.extend([
                "## Reference Material",
                "Use the following articles as reference for tone, structure, and content inspiration:",
                ""
            ])
            for i, article in enumerate(reference_articles[:3], 1):  # Max 3 references
                prompt_parts.extend([
                    f"### Reference {i}",
                    f"Title: {article.get('title', 'N/A')}",
                    f"Content: {article.get('content', 'N/A')[:500]}...",
                    ""
                ])

        # Tips
        if tips:
            prompt_parts.extend([
                "## Additional Requirements",
                "\n".join(f"- {tip}" for tip in tips),
                ""
            ])

        # Output format
        prompt_parts.extend([
            "## Output Format",
            "Please provide your response in the following format:",
            "",
            "TITLE: [Your title here]",
            "",
            "[Your article content here]",
            "",
            "---",
            "",
            "Write the article now:"
        ])

        return "\n".join(prompt_parts)

    @staticmethod
    def get_style_instructions(style: str) -> str:
        """Get style-specific instructions."""
        return PromptTemplates.STYLE_INSTRUCTIONS.get(style, PromptTemplates.STYLE_INSTRUCTIONS["professional"])

    @staticmethod
    def get_length_instructions(length: str) -> str:
        """Get length-specific instructions."""
        return PromptTemplates.LENGTH_INSTRUCTIONS.get(length, PromptTemplates.LENGTH_INSTRUCTIONS["medium"])

    @staticmethod
    def get_title_instructions(title_type: str) -> str:
        """Get title-specific instructions."""
        return PromptTemplates.TITLE_INSTRUCTIONS.get(title_type, PromptTemplates.TITLE_INSTRUCTIONS["catchy"])
