"""AI-powered open response theme extraction using Claude API."""
import json
import os


def get_api_key():
    """Get Anthropic API key from environment or Streamlit secrets."""
    key = os.environ.get("ANTHROPIC_API_KEY")
    if key:
        return key
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "ANTHROPIC_API_KEY" in st.secrets:
            return st.secrets["ANTHROPIC_API_KEY"]
    except Exception:
        pass
    return None


def extract_themes(responses, question_text="", api_key=None):
    """Send open-ended responses to Claude and extract themes.

    Args:
        responses: list of response strings
        question_text: the survey question that was asked
        api_key: Anthropic API key

    Returns dict with themes list or None if API call fails.
    """
    if not api_key:
        return None

    try:
        import anthropic
    except ImportError:
        return None

    # Limit to 200 responses to keep costs down
    sample = responses[:200]
    responses_text = "\n".join(f"- {r}" for r in sample)

    prompt = f"""Analyze these {len(sample)} survey responses to the question: "{question_text}"

Identify the top themes that emerge. For each theme, provide:
1. A short theme name (2-5 words)
2. How many responses relate to this theme (approximate count)
3. The overall sentiment of responses in this theme (positive, negative, or mixed)
4. One representative quote from the responses

Return your analysis as JSON in this exact format:
{{
    "themes": [
        {{
            "name": "Theme Name",
            "count": 15,
            "sentiment": "positive",
            "quote": "exact quote from a response"
        }}
    ],
    "summary": "A 2-3 sentence overall summary of what respondents are saying."
}}

Here are the responses:
{responses_text}"""

    try:
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse the JSON from the response
        text = message.content[0].text
        # Find JSON in the response
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            result = json.loads(text[start:end])
            result["responses_analyzed"] = len(sample)
            result["total_responses"] = len(responses)
            return result
    except Exception as e:
        return {"error": str(e)}

    return None
