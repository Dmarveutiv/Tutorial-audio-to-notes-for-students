from google import genai

class NoteGenerator:
    def __init__(self, api_key):
        """
        api_key: your Gemini API key, loaded securely from .env in main.py
        """
        self.client = genai.Client(api_key=api_key)
        self.model_name = "gemini-2.5-flash"

    def generate_notes(self, transcript, video_title="Tutorial"):
        """
        Takes a raw transcript and returns structured study notes.
        """
        if not transcript or len(transcript.strip()) == 0:
            return "No transcript available to generate notes from."

        prompt = f"""You are an expert note-taker helping a student study from a tutorial video transcript.

Video title: {video_title}

Below is the raw, unstructured transcript from the tutorial. Convert it into clean, well-organized study notes following these rules:

1. Add a clear title and section headings based on the topics covered
2. Summarize key concepts in your own words — don't just copy the transcript verbatim
3. Use bullet points for lists, steps, or key facts
4. Include any code snippets, commands, or technical terms mentioned, formatted clearly
5. Add a short "Summary" section at the end with the 3-5 most important takeaways
6. Fix any transcription errors or filler words (um, uh, like, you know) — clean it up into proper written English
7. Keep technical accuracy — do not invent information that wasn't in the transcript

Raw transcript:
{transcript}

Return only the structured notes, formatted in Markdown.
"""

        try:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        except Exception as e:
            print(f"Gemini API error: {e}")
            return f"Error generating notes: {e}"