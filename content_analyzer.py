import os
from typing import Dict
from dotenv import load_dotenv

load_dotenv()

class ContentAnalyzer:
    def __init__(self, content_focus=None, mode='test'):
        """
        Initialize ContentAnalyzer with specified mode.

        Args:
            content_focus: Custom content focus string
            mode: 'test' (uses Gemini 1.5 Flash) or 'production' (uses GPT-4o). Default: 'test'
        """
        # Mode-based configuration
        if mode == 'production':
            self.provider = 'openai'
            self.model = 'gpt-4o'
        elif mode == 'test':
            self.provider = 'google'
            self.model = 'gemini-1.5-flash'
        else:
            # Fallback to environment variables if mode is invalid
            self.provider = os.getenv('AI_PROVIDER', 'google').lower()

            # Default models for each provider
            default_models = {
                'anthropic': 'claude-3-5-haiku-20241022',
                'openai': 'gpt-4o-mini',
                'google': 'gemini-1.5-flash'
            }

            self.model = os.getenv('AI_MODEL', default_models.get(self.provider, 'gemini-1.5-flash'))

        # Initialize the appropriate client
        self._init_client()

        # Load filter settings
        self.excluded_people = self._parse_csv_env('EXCLUDE_PEOPLE')
        self.excluded_subjects = self._parse_csv_env('EXCLUDE_SUBJECTS')

        # Set content focus (default: AI strategy for business leaders)
        if content_focus:
            self.content_focus = content_focus
        else:
            self.content_focus = os.getenv('CONTENT_FOCUS', '').strip() or \
                               'AI strategy and innovation for business leaders'

    def _init_client(self):
        """Initialize the appropriate AI client based on provider"""
        if self.provider == 'anthropic':
            from anthropic import Anthropic
            api_key = os.getenv('ANTHROPIC_API_KEY')
            if not api_key:
                raise ValueError("ANTHROPIC_API_KEY not found. Please set it in your .env file.")
            self.client = Anthropic(api_key=api_key)

        elif self.provider == 'openai':
            from openai import OpenAI
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY not found. Please set it in your .env file.")
            self.client = OpenAI(api_key=api_key)

        elif self.provider == 'google':
            import google.generativeai as genai
            api_key = os.getenv('GOOGLE_API_KEY')
            if not api_key:
                raise ValueError("GOOGLE_API_KEY not found. Please set it in your .env file.")
            genai.configure(api_key=api_key)
            self.client = genai.GenerativeModel(self.model)

        else:
            raise ValueError(f"Unsupported AI provider: {self.provider}. Use 'anthropic', 'openai', or 'google'.")

    def _parse_csv_env(self, env_var: str) -> list:
        """Parse comma-separated environment variable into list"""
        value = os.getenv(env_var, '').strip()
        if not value:
            return []
        return [item.strip() for item in value.split(',') if item.strip()]

    def should_exclude_transcript(self, transcript: Dict) -> bool:
        """Check if transcript should be excluded based on filters"""
        # Check subject line filters
        subject = transcript.get('subject', '').lower()
        for keyword in self.excluded_subjects:
            if keyword.lower() in subject:
                return True

        # Check people filters (in transcript body)
        body = transcript.get('body', '').lower()
        for person in self.excluded_people:
            if person.lower() in body:
                return True

        return False

    def _create_prompt(self, transcript: Dict) -> str:
        """Create the analysis prompt"""
        return f"""You are analyzing a conversation transcript for content focused on {self.content_focus}.

Conversation Topic: {transcript['topic']}
Date: {transcript['date']}

Transcript:
{transcript['body']}

Please analyze this transcript and provide 2-4 recommended topics. For EACH topic, include:
- A compelling topic title
- 1-2 sentence description of why this would make a good article
- 2-3 KEY INSIGHTS specifically related to this topic
- 1-2 NOTABLE QUOTES that support this topic (with speaker name if identifiable)

IMPORTANT INSTRUCTIONS:
- Extract ACTUAL verbatim quotes from the transcript text
- Include the speaker's name next to each quote in the format: **[Name]:**
- Make insights actionable and specific
- Focus on content relevant to {self.content_focus}

Format your response EXACTLY as follows:

## TOPIC 1: [Topic Title]

**Description:** [1-2 sentence description of why this would make a good article]

**Key Insights:**
• [Insight 1 related to this topic]
• [Insight 2 related to this topic]
• [Insight 3 related to this topic]

**Notable Quotes:**
> **[Speaker Name]:** "[Exact quote extracted verbatim from the transcript]"

> **[Speaker Name]:** "[Exact quote extracted verbatim from the transcript]"

---

## TOPIC 2: [Topic Title]

**Description:** [1-2 sentence description]

**Key Insights:**
• [Insight 1 related to this topic]
• [Insight 2 related to this topic]

**Notable Quotes:**
> **[Speaker Name]:** "[Exact quote extracted verbatim from the transcript]"

---

Continue this format for all topics (2-4 total)."""

    def _call_anthropic(self, prompt: str) -> str:
        """Call Anthropic API"""
        message = self.client.messages.create(
            model=self.model,
            max_tokens=4000,
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text

    def _call_openai(self, prompt: str) -> str:
        """Call OpenAI API"""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=4000,
            temperature=0.7
        )
        return response.choices[0].message.content

    def _call_google(self, prompt: str) -> str:
        """Call Google Gemini API"""
        response = self.client.generate_content(prompt)
        return response.text

    def analyze_transcript(self, transcript: Dict) -> Dict:
        """
        Analyze a transcript and generate newsletter content suggestions

        Returns:
            Dict with keys: recommended_topics, key_insights, quotes
        """
        prompt = self._create_prompt(transcript)

        try:
            # Call the appropriate provider
            if self.provider == 'anthropic':
                analysis = self._call_anthropic(prompt)
            elif self.provider == 'openai':
                analysis = self._call_openai(prompt)
            elif self.provider == 'google':
                analysis = self._call_google(prompt)
            else:
                raise ValueError(f"Unsupported provider: {self.provider}")

            # Add source information to the analysis
            analysis_with_source = f"**Source:** {transcript['subject']}\n\n{analysis}"

            return {
                'topic': transcript['topic'],
                'date': transcript['date'],
                'subject': transcript['subject'],
                'analysis': analysis_with_source
            }

        except Exception as e:
            return {
                'topic': transcript['topic'],
                'date': transcript['date'],
                'error': f"Error analyzing transcript with {self.provider}/{self.model}: {str(e)}"
            }

    def batch_analyze(self, transcripts: list) -> list:
        """Analyze multiple transcripts"""
        results = []
        for transcript in transcripts:
            result = self.analyze_transcript(transcript)
            results.append(result)
        return results
