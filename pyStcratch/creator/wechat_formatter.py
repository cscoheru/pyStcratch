"""
WeChat article formatter for multiple export formats.
"""
from typing import Dict


class WeChatFormatter:
    """Format articles for WeChat and other platforms."""

    @staticmethod
    def to_markdown(article: Dict) -> str:
        """
        Convert article to Markdown format.

        Args:
            article: Article dict with title and content

        Returns:
            Markdown formatted string
        """
        title = article.get("title", "Untitled")
        content = article.get("content", "")

        # If content is already in markdown format, just add title
        if "#" in content or content.startswith("#"):
            return f"# {title}\n\n{content}"

        # Otherwise, convert to markdown
        return f"# {title}\n\n{content}"

    @staticmethod
    def to_plain_text(article: Dict) -> str:
        """
        Convert article to plain text.

        Args:
            article: Article dict with title and content

        Returns:
            Plain text string
        """
        title = article.get("title", "Untitled")
        content = article.get("content", "")

        # Remove markdown symbols
        plain_content = content

        # Remove headers
        plain_content = plain_content.replace("#", "")

        # Remove bold/italic markers
        plain_content = plain_content.replace("**", "")
        plain_content = plain_content.replace("__", "")
        plain_content = plain_content.replace("*", "")
        plain_content = plain_content.replace("_", "")

        # Remove list markers
        lines = plain_content.split("\n")
        cleaned_lines = []
        for line in lines:
            line = line.lstrip("- * 1. 2. 3. 4. 5. 6. 7. 8. 9.")
            cleaned_lines.append(line)

        return f"{title}\n\n{''.join(cleaned_lines)}"

    @staticmethod
    def to_html(article: Dict) -> str:
        """
        Convert article to HTML format (for WeChat editor).

        Args:
            article: Article dict with title and content

        Returns:
            HTML formatted string
        """
        title = article.get("title", "Untitled")
        content = article.get("content", "")

        # Basic markdown to HTML conversion
        html_content = content

        # Headers
        import re
        html_content = re.sub(r'^# (.+)$', r'<h1>\1</h1>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^## (.+)$', r'<h2>\1</h2>', html_content, flags=re.MULTILINE)
        html_content = re.sub(r'^### (.+)$', r'<h3>\1</h3>', html_content, flags=re.MULTILINE)

        # Bold
        html_content = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html_content)

        # Italic
        html_content = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html_content)

        # Lists (basic)
        html_content = re.sub(r'^- (.+)$', r'<li>\1</li>', html_content, flags=re.MULTILINE)

        # Paragraphs
        lines = html_content.split("\n")
        html_lines = []
        in_list = False

        for line in lines:
            if line.strip() == "":
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                continue

            if line.strip().startswith("<li>"):
                if not in_list:
                    html_lines.append("<ul>")
                    in_list = True
                html_lines.append(line)
            elif line.strip().startswith("<h") or line.strip().startswith("<p"):
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(line)
            else:
                if in_list:
                    html_lines.append("</ul>")
                    in_list = False
                html_lines.append(f"<p>{line}</p>")

        if in_list:
            html_lines.append("</ul>")

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; line-height: 1.6; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #333; border-bottom: 2px solid #007AFF; padding-bottom: 10px; }}
        h2 {{ color: #555; margin-top: 30px; }}
        h3 {{ color: #777; }}
        p {{ color: #333; margin-bottom: 15px; }}
        strong {{ color: #007AFF; }}
        ul {{ padding-left: 20px; }}
        li {{ margin-bottom: 8px; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    {''.join(html_lines)}
</body>
</html>
        """

        return html.strip()

    @staticmethod
    def to_xiumi_format(article: Dict) -> str:
        """
        Format for Xiumi (秀米) editor - simplified HTML with inline styles.

        Args:
            article: Article dict

        Returns:
            HTML string optimized for Xiumi
        """
        # Xiumi uses specific formatting - simplified version here
        html = WeChatFormatter.to_html(article)

        # Add Xiumi-specific styles
        html = html.replace('color: #007AFF;', 'color: #576b95;')  # WeChat blue

        return html

    @staticmethod
    def to_135_format(article: Dict) -> str:
        """
        Format for 135 Editor - HTML with section wrappers.

        Args:
            article: Article dict

        Returns:
            HTML string for 135 Editor
        """
        title = article.get("title", "Untitled")
        content = article.get("content", "")

        # 135 editor uses section wrappers
        sections = []

        # Title section
        sections.append(f"""
<section style="padding: 20px; text-align: center; background: #f5f5f5;">
    <h2 style="margin: 0; color: #333; font-size: 24px;">{title}</h2>
</section>
        """)

        # Content sections (split by paragraphs)
        paragraphs = content.split("\n\n")
        for para in paragraphs:
            if para.strip():
                sections.append(f"""
<section style="padding: 15px 20px; line-height: 1.8; color: #555;">
    {para}
</section>
                """)

        return "\n".join(sections)
