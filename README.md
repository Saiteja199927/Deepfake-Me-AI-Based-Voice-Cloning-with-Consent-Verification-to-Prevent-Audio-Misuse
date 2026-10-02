# 🎙️ Voice TTS Application

A Text-to-Speech application built with Streamlit and multiple TTS engines.

## 📁 Project Structure

```
voice/
├── app.py                 # Main Streamlit application
├── requirements.txt       # Python dependencies
├── .env.example          # Environment variables template
├── .gitignore            # Git ignore rules
├── config/
│   ├── __init__.py
│   └── settings.py       # Application settings
├── src/
│   ├── __init__.py
│   ├── tts/
│   │   ├── __init__.py
│   │   └── tts_engine.py # TTS engine implementations
│   ├── audio/
│   │   ├── __init__.py
│   │   └── processor.py  # Audio processing utilities
│   └── utils/
│       ├── __init__.py
│       └── helpers.py    # Helper functions
├── output/               # Generated audio files
└── temp/                 # Temporary files
```

## 🚀 Getting Started

### 1. Create Virtual Environment

```bash
python -m venv venv
venv\Scripts\activate  # Windows
# or
source venv/bin/activate  # Linux/Mac
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Setup Environment Variables

```bash
copy .env.example .env  # Windows
# or
cp .env.example .env    # Linux/Mac
```

### 4. Run the Application

```bash
streamlit run app.py
```

## 🛠️ Features (Coming Soon)

- **Multiple TTS Engines**: gTTS, pyttsx3, Edge-TTS
- **Audio Processing**: Format conversion, speed/pitch adjustment
- **Voice Customization**: Language, voice, speed controls
- **Export Options**: MP3, WAV, and more

## 📄 License

MIT License
