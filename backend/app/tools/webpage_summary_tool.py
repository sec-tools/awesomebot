"""Webpage summary tool - fetches and extracts content from URLs for summarization"""
import re
from typing import Dict, Any, List
from app.tools.base import Tool, ToolResult
from app.services.code_executor import CodeExecutor


class WebpageSummaryTool(Tool):
    """Tool for fetching and summarizing webpage content"""
    
    def __init__(self):
        super().__init__()
        self.code_executor = CodeExecutor()
    
    def _get_description(self) -> str:
        return "Fetches webpage content from a URL and extracts text for summarization"
    
    def _get_patterns(self) -> List[str]:
        return [
            r'summarize\s+(this\s*:?\s*)?(https?://\S+)',
            r'summarize\s+(the\s+)?(page|website|site|article|content)\s*(at\s+)?(https?://\S+)',
            r'what\s+(is|does)\s+(this\s+)?(page|website|article)\s+(about|say)\s*:?\s*(https?://\S+)',
            r'read\s+(and\s+)?summarize\s*(https?://\S+)',
            r'get\s+(the\s+)?summary\s+(of|from)\s*(https?://\S+)',
            r'tldr\s*(of\s*)?(https?://\S+)',
            r'summarize\s+url\s*:?\s*(https?://\S+)',
        ]
    
    def _extract_url(self, message: str) -> str:
        """Extract URL from the message"""
        # Match URLs - include parentheses but handle balanced pairs
        url_pattern = r'(https?://[^\s<>"{}|\\^`\[\]]+)'
        match = re.search(url_pattern, message)
        if match:
            url = match.group(1)
            # Clean trailing punctuation but preserve balanced parentheses
            # Count open and close parens
            open_parens = url.count('(')
            close_parens = url.count(')')
            
            # If there are more closing parens than opening, strip the extras from the end
            while close_parens > open_parens and url.endswith(')'):
                url = url[:-1]
                close_parens -= 1
            
            # Clean other trailing punctuation
            url = re.sub(r'[.,;:!?\'">\]}>]+$', '', url)
            return url
        return ""
    
    def _generate_code(self, url: str) -> str:
        """Generate Python code to fetch and extract webpage content"""
        code = f'''# Webpage Content Extractor
import urllib.request
import urllib.parse
import urllib.error

url = {repr(url)}

try:
    # Create request with browser-like headers
    headers = {{
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
    }}
    
    request = urllib.request.Request(url, headers=headers)
    
    with urllib.request.urlopen(request, timeout=15) as response:
        # Read and decode content
        content = response.read()
        
        # Try to detect encoding
        encoding = 'utf-8'
        content_type = response.headers.get('Content-Type', '')
        if 'charset=' in content_type:
            encoding = content_type.split('charset=')[-1].split(';')[0].strip()
        
        try:
            html = content.decode(encoding)
        except Exception:
            html = content.decode('utf-8', errors='ignore')
        
        # Extract title
        title_match = None
        import re as regex
        title_pattern = regex.compile(r'<title[^>]*>([^<]+)</title>', regex.IGNORECASE)
        title_search = title_pattern.search(html)
        if title_search:
            title_match = title_search.group(1).strip()
        
        # Remove script and style elements
        html = regex.sub(r'<script[^>]*>.*?</script>', '', html, flags=regex.DOTALL | regex.IGNORECASE)
        html = regex.sub(r'<style[^>]*>.*?</style>', '', html, flags=regex.DOTALL | regex.IGNORECASE)
        html = regex.sub(r'<noscript[^>]*>.*?</noscript>', '', html, flags=regex.DOTALL | regex.IGNORECASE)
        html = regex.sub(r'<header[^>]*>.*?</header>', '', html, flags=regex.DOTALL | regex.IGNORECASE)
        html = regex.sub(r'<footer[^>]*>.*?</footer>', '', html, flags=regex.DOTALL | regex.IGNORECASE)
        html = regex.sub(r'<nav[^>]*>.*?</nav>', '', html, flags=regex.DOTALL | regex.IGNORECASE)
        html = regex.sub(r'<!--.*?-->', '', html, flags=regex.DOTALL)
        
        # Try to extract main content areas
        main_content = ""
        
        # Look for article or main content
        article_match = regex.search(r'<article[^>]*>(.*?)</article>', html, regex.DOTALL | regex.IGNORECASE)
        if article_match:
            main_content = article_match.group(1)
        
        if not main_content:
            main_match = regex.search(r'<main[^>]*>(.*?)</main>', html, regex.DOTALL | regex.IGNORECASE)
            if main_match:
                main_content = main_match.group(1)
        
        if not main_content:
            # Try to find content div
            content_pattern = r'<div[^>]*(?:class|id)=[^>]*(?:content|article|post|entry|text)[^>]*>(.*?)</div>'
            content_match = regex.search(content_pattern, html, regex.DOTALL | regex.IGNORECASE)
            if content_match:
                main_content = content_match.group(1)
        
        # If no main content found, use body
        if not main_content:
            body_match = regex.search(r'<body[^>]*>(.*?)</body>', html, regex.DOTALL | regex.IGNORECASE)
            if body_match:
                main_content = body_match.group(1)
            else:
                main_content = html
        
        # Extract paragraphs
        paragraphs = regex.findall(r'<p[^>]*>(.*?)</p>', main_content, regex.DOTALL | regex.IGNORECASE)
        
        # Also get headings
        headings = regex.findall(r'<h[1-6][^>]*>(.*?)</h[1-6]>', main_content, regex.DOTALL | regex.IGNORECASE)
        
        # Clean HTML tags from extracted text
        def clean_html(text):
            text = regex.sub(r'<[^>]+>', ' ', text)
            text = regex.sub(r'&nbsp;', ' ', text)
            text = regex.sub(r'&amp;', '&', text)
            text = regex.sub(r'&lt;', '<', text)
            text = regex.sub(r'&gt;', '>', text)
            text = regex.sub(r'&quot;', '"', text)
            text = regex.sub(r'&#[0-9]+;', '', text)
            text = regex.sub(r'[ \\t]+', ' ', text)
            text = regex.sub(r'\\n\\s*\\n', '\\n', text)
            return text.strip()
        
        # Build output
        output_parts = []
        
        if title_match:
            output_parts.append(f"TITLE: {{clean_html(title_match)}}")
            output_parts.append("")
        
        output_parts.append(f"URL: {{url}}")
        output_parts.append("")
        
        # Add headings
        if headings:
            output_parts.append("KEY HEADINGS:")
            for h in headings[:5]:
                cleaned = clean_html(h)
                if cleaned and len(cleaned) > 3:
                    output_parts.append(f"  - {{cleaned[:100]}}")
            output_parts.append("")
        
        # Add paragraphs
        output_parts.append("CONTENT:")
        content_added = 0
        total_chars = 0
        max_chars = 6000  # Limit content length
        
        for p in paragraphs:
            cleaned = clean_html(p)
            if cleaned and len(cleaned) > 50:  # Skip very short paragraphs
                if total_chars + len(cleaned) > max_chars:
                    remaining = max_chars - total_chars
                    if remaining > 100:
                        output_parts.append(cleaned[:remaining] + "...")
                    output_parts.append("")
                    output_parts.append(f"[Content truncated - {{len(paragraphs)}} paragraphs total]")
                    break
                output_parts.append(cleaned)
                output_parts.append("")
                total_chars += len(cleaned)
                content_added += 1
        
        if content_added == 0:
            # Fallback: extract all text
            all_text = clean_html(main_content)
            if all_text:
                output_parts.append(all_text[:max_chars])
                if len(all_text) > max_chars:
                    output_parts.append("...")
                    output_parts.append("[Content truncated]")
        
        print("\\n".join(output_parts))

except urllib.error.HTTPError as e:
    print(f"HTTP Error {{e.code}}: {{e.reason}}")
    print(f"Could not fetch: {{url}}")
except urllib.error.URLError as e:
    print(f"URL Error: {{e.reason}}")
    print(f"Could not connect to: {{url}}")
except Exception as e:
    print(f"Error fetching webpage: {{str(e)}}")
    print(f"URL: {{url}}")
'''
        return code
    
    async def execute(self, user_message: str, context: Dict[str, Any]) -> ToolResult:
        """Execute webpage summary extraction"""
        
        # Extract URL from message
        url = self._extract_url(user_message)
        
        if not url:
            return ToolResult(
                success=False,
                output="",
                error="No valid URL found in the message. Please provide a URL starting with http:// or https://",
                metadata={"tool": "webpage_summary"}
            )
        
        # Generate and execute the code
        code = self._generate_code(url)
        execution_result = await self.code_executor.execute_python(code)
        
        output = execution_result.get("output", "")
        error = execution_result.get("error", "")
        
        # Add instruction for AI to summarize
        if output and not error:
            output = f"=== WEBPAGE CONTENT EXTRACTED ===\n\n{output}\n\n=== END OF CONTENT ===\n\nPlease provide a concise summary of this webpage content."
        
        return ToolResult(
            success=execution_result.get("success", False),
            output=output,
            error=error,
            generated_code=code,
            metadata={"tool": "webpage_summary", "url": url}
        )
