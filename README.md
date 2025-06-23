# Personalized Book Reader

A Streamlit application that uses Chatterbox TTS to create personalized audiobook narration from uploaded text files.

## Features

- Upload books in various formats (PDF, DOCX, EPUB, TXT)
- Upload a voice sample to personalize the narration
- Customize the TTS parameters
- Generate audio for individual chunks or the entire book
- Preview and listen to the generated audio

## Installation

### Prerequisites

- Python 3.8+
- pip package manager

### Step 1: Clone the repository

```bash
git clone <repository-url>
cd u-voice-audio-book
```

### Step 2: Create a virtual environment (recommended)

```bash
python -m venv venv
```

Activate the virtual environment:

- On Windows:
  ```bash
  venv\Scripts\activate
  ```
- On macOS/Linux:
  ```bash
  source venv/bin/activate
  ```

### Step 3: Install dependencies

Install all required dependencies from the requirements.txt file:

```bash
pip install -r requirements.txt
```

#### Known Issues and Solutions

If you encounter issues with PyTorch installation, try installing specific versions:

```bash
pip install torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2
```

If you have issues with soundfile:

```bash
pip install soundfile
```

On Windows, you might need to install specific binaries:
- Download the appropriate wheel file from [Christoph Gohlke's website](https://www.lfd.uci.edu/~gohlke/pythonlibs/#soundfile)
- Install it with: `pip install <downloaded-wheel-file>`

## Usage

1. Run the application:
   ```bash
   streamlit run tts.py
   ```

2. Open your browser and navigate to the URL displayed in the terminal (usually http://localhost:8501)

3. Upload your voice sample and book file

4. Adjust the TTS settings as desired

5. Generate audio for individual chunks or all chunks

6. Listen to and download the generated audio

## Requirements

See the requirements.txt file for a complete list of dependencies.


