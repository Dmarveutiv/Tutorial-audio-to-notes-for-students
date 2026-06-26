# TutorialToNotes

Captures live system audio from tutorial videos, transcribes it with Whisper, structures it into notes using Gemini AI, and exports a PDF.

## Setup

### 1. Clone the repo


### 2. Create and activate a virtual environment
```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Install ffmpeg
- Download from https://www.gyan.dev/ffmpeg/builds/ → `ffmpeg-release-essentials.zip`
- Extract to `C:\ffmpeg`
- Add `C:\ffmpeg\bin` to your System PATH (Environment Variables → Path → New)
- Open a new terminal and verify: `ffmpeg -version`

### 5. Get a Gemini API key
- Go to https://aistudio.google.com/app/apikey
- Click **Create API Key** and copy it

### 6. Create a `.env` file
In the project root, create a file named `.env`:
```
GEMINI_API_KEY=your_key_here
```

## Running the app

```bash
venv\Scripts\activate
python main.py
```

1. Click **Start**
2. Play the tutorial video/audio on your system
3. Watch the live transcript fill in
4. Click **Stop** when done
5. Wait for Gemini to generate structured notes
6. Click **Save PDF** and choose a location

## Notes

- Requires Windows (uses WASAPI loopback via `pyaudiowpatch`)
- First run downloads the Whisper `base` model 
- Gemini free tier: 1,500 requests/day 
