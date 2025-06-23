import streamlit as st
import tempfile
import os
import io
from pathlib import Path
import PyPDF2
import docx
import zipfile
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import re
import torchaudio

# Note: You'll need to install dependencies from requirements.txt
# pip install -r requirements.txt

# Global variables to track availability of components
CHATTERBOX_AVAILABLE = False
CHATTERBOX_IMPORT_ERROR = None
SOUNDFILE_AVAILABLE = False
SOUNDFILE_IMPORT_ERROR = None

# Try to import ChatterboxTTS with better error handling
try:
    from chatterbox import ChatterboxTTS
    CHATTERBOX_AVAILABLE = True
except ImportError as e:
    CHATTERBOX_IMPORT_ERROR = f"ImportError: {str(e)}"
except Exception as e:
    CHATTERBOX_IMPORT_ERROR = f"Error loading ChatterboxTTS: {str(e)}"

# Try to import SoundFile
try:
    import soundfile as sf
    SOUNDFILE_AVAILABLE = True
except ImportError as e:
    SOUNDFILE_IMPORT_ERROR = f"ImportError: {str(e)}"
except Exception as e:
    SOUNDFILE_IMPORT_ERROR = f"Error loading SoundFile: {str(e)}"

def extract_text_from_pdf(file):
    """Extract text from PDF file"""
    pdf_reader = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text() + "\n"
    return text

def extract_text_from_docx(file):
    """Extract text from DOCX file"""
    doc = docx.Document(file)
    text = ""
    for paragraph in doc.paragraphs:
        text += paragraph.text + "\n"
    return text

def extract_text_from_epub(file):
    """Extract text from EPUB file"""
    book = epub.read_epub(file)
    text = ""
    
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_content(), 'html.parser')
            text += soup.get_text() + "\n"
    
    return text

def extract_text_from_txt(file):
    """Extract text from TXT file"""
    return file.read().decode('utf-8')

def clean_text(text):
    """Clean and prepare text for TTS"""
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove special characters that might cause issues
    text = re.sub(r'[^\w\s.,!?;:\'"-]', '', text)
    return text.strip()

def split_text_into_chunks(text, max_length=500):
    """Split text into smaller chunks for better TTS processing"""
    sentences = re.split(r'[.!?]+', text)
    chunks = []
    current_chunk = ""
    
    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence:
            continue
            
        if len(current_chunk) + len(sentence) < max_length:
            current_chunk += sentence + ". "
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            current_chunk = sentence + ". "
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks

def main():
    st.set_page_config(
        page_title="Personalized Book Reader",
        page_icon="📚",
        layout="wide"
    )
    
    st.title("📚 Personalized Book Reader with Chatterbox TTS")
    st.markdown("Upload your voice sample and a book to create personalized audiobook narration!")
      # Display an info message about the requirements file
    st.info("""
    📋 **Note**: This app requires specific dependencies.
    If you encounter any issues, install all dependencies from the requirements.txt file:
    ```bash
    pip install -r requirements.txt
    ```
    """)
    
    # Check if Chatterbox is available
    if not CHATTERBOX_AVAILABLE:
        st.error(f"""
        ⚠️ **Chatterbox TTS is not available!**
        
        Error: {CHATTERBOX_IMPORT_ERROR or "Unknown import error"}
        
        Please install Chatterbox TTS and its dependencies using:
        ```bash
        pip install chatterbox-tts torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2
        ```
        
        Note: The specific versions of torch, torchvision, and torchaudio are important as they need to be compatible with each other.
        
        This app requires Chatterbox TTS for voice synthesis.
        """)
        
        # Add a button to try installing the required packages
        if st.button("🔄 Try installing required packages"):
            st.info("Installing required packages... This may take a few minutes.")
            st.code("pip install chatterbox-tts torch==2.0.1 torchvision==0.15.2 torchaudio==2.0.2 soundfile")
            st.warning("After installation, please restart the application.")
        
        st.stop()
    
    # Check if SoundFile is available
    if not SOUNDFILE_AVAILABLE:
        st.error(f"""
        ⚠️ **SoundFile package is not available!**
        
        Error: {SOUNDFILE_IMPORT_ERROR or "Unknown import error"}
        
        Please install it using:
        ```bash
        pip install soundfile
        ```
        
        This app requires SoundFile for audio processing.
        """)
        
        # Add a button to try installing the required package
        if st.button("🔄 Try installing SoundFile"):
            st.info("Installing SoundFile package...")
            st.code("pip install soundfile")
            st.warning("After installation, please restart the application.")
            
        st.stop()
    
    # Initialize session state
    if 'tts_model' not in st.session_state:
        st.session_state.tts_model = None
    if 'book_text' not in st.session_state:
        st.session_state.book_text = ""
    if 'audio_files' not in st.session_state:
        st.session_state.audio_files = []
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Voice personalization section
        st.subheader("🎤 Voice Personalization")
        voice_file = st.file_uploader(
            "Upload your voice sample (5+ seconds recommended)",
            type=['wav', 'mp3', 'flac', 'm4a'],
            help="Upload a clear audio sample of your voice for personalization. 5+ seconds work best."
        )
        
        # TTS parameters
        st.subheader("🎛️ TTS Settings")
        emotion_intensity = st.slider(
            "Emotion Intensity",
            min_value=0.0,
            max_value=1.0,
            value=0.5,
            step=0.1,
            help="Control the emotional expressiveness of the voice"
        )
        
        cfg_scale = st.slider(
            "CFG Scale",
            min_value=0.1,
            max_value=1.0,
            value=0.5,
            step=0.1,
            help="Control the adherence to the reference voice (lower = more similar to reference)"
        )
        
        chunk_size = st.slider(
            "Text Chunk Size",
            min_value=100,
            max_value=1000,
            value=500,
            step=50,
            help="Size of text chunks for processing (smaller = more responsive)"
        )
    
    # Main content area
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.header("📖 Book Upload")
        book_file = st.file_uploader(
            "Upload your book",
            type=['pdf', 'docx', 'epub', 'txt'],
            help="Supported formats: PDF, DOCX, EPUB, TXT"
        )
        
        if book_file is not None:
            with st.spinner("Extracting text from book..."):
                try:
                    # Extract text based on file type
                    file_extension = Path(book_file.name).suffix.lower()
                    
                    if file_extension == '.pdf':
                        text = extract_text_from_pdf(book_file)
                    elif file_extension == '.docx':
                        text = extract_text_from_docx(book_file)
                    elif file_extension == '.epub':
                        text = extract_text_from_epub(book_file)
                    elif file_extension == '.txt':
                        text = extract_text_from_txt(book_file)
                    else:
                        st.error("Unsupported file format!")
                        return
                    
                    # Clean and store text
                    st.session_state.book_text = clean_text(text)
                    
                    st.success(f"✅ Book loaded! ({len(st.session_state.book_text)} characters)")
                    
                    # Show preview
                    with st.expander("📄 Text Preview"):
                        st.text_area(
                            "First 500 characters:",
                            st.session_state.book_text[:500] + "..." if len(st.session_state.book_text) > 500 else st.session_state.book_text,
                            height=200,
                            disabled=True
                        )
                        
                except Exception as e:
                    st.error(f"Error extracting text: {str(e)}")
    
    with col2:
        st.header("🎵 Audio Generation")
        
        if st.session_state.book_text and voice_file:            # Initialize TTS model if not already done
            if st.session_state.tts_model is None:
                with st.spinner("Initializing Chatterbox TTS..."):
                    try:
                        st.session_state.tts_model = ChatterboxTTS.from_pretrained(device="cpu")
                        st.success("✅ TTS Model loaded!")
                    except Exception as e:
                        st.error(f"Error loading TTS model: {str(e)}")
                        return
            
            # Text selection for generation
            st.subheader("📝 Select Text to Convert")
            
            # Split text into chunks
            text_chunks = split_text_into_chunks(st.session_state.book_text, chunk_size)
            
            st.info(f"Book split into {len(text_chunks)} chunks")
            
            # Chunk selection
            chunk_selection = st.selectbox(
                "Select chunk to convert:",
                range(len(text_chunks)),
                format_func=lambda x: f"Chunk {x+1}: {text_chunks[x][:50]}..."
            )
            
            # Show selected chunk
            with st.expander("📄 Selected Text"):
                st.text_area(
                    "Text to convert:",
                    text_chunks[chunk_selection],
                    height=150,
                    disabled=True
                )
            
            # Generation controls
            col_gen1, col_gen2 = st.columns(2)
            
            with col_gen1:
                if st.button("🎤 Generate Audio", type="primary"):
                    generate_audio_chunk(
                        st.session_state.tts_model,
                        text_chunks[chunk_selection],
                        voice_file,
                        emotion_intensity,
                        cfg_scale,
                        chunk_selection
                    )
            
            with col_gen2:
                if st.button("🎵 Generate All Chunks"):
                    generate_all_chunks(
                        st.session_state.tts_model,
                        text_chunks,
                        voice_file,
                        emotion_intensity,
                        cfg_scale
                    )
            
            # Display generated audio files
            if st.session_state.audio_files:
                st.subheader("🎧 Generated Audio")
                for i, audio_data in enumerate(st.session_state.audio_files):
                    if audio_data:
                        st.write(f"**Chunk {i+1}:**")
                        st.audio(audio_data, format='audio/wav')
        
        elif not st.session_state.book_text:
            st.info("👆 Please upload a book first")
        elif not voice_file:
            st.info("👆 Please upload a voice sample first")

def generate_audio_chunk(tts_model, text, voice_file, emotion_intensity, cfg_scale, chunk_index):
    """Generate audio for a single text chunk"""
    # First verify SoundFile is available
    if not SOUNDFILE_AVAILABLE:
        st.error("SoundFile package is required but not installed. Please install with: pip install soundfile")
        return
        
    with st.spinner(f"Generating audio for chunk {chunk_index + 1}..."):
        voice_path = None
        try:
            # Save voice file temporarily
            with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_voice:
                tmp_voice.write(voice_file.read())
                voice_path = tmp_voice.name
              # Generate audio
            audio_data = tts_model.generate(
                text,
                audio_prompt_path=voice_path
            )
            
            # Convert to bytes for Streamlit
            audio_bytes = io.BytesIO()
            import torchaudio
            # Save as WAV using torchaudio (same as in example.py)
            torchaudio.save(audio_bytes, audio_data, tts_model.sr, format='wav')
            audio_bytes.seek(0)
            
            # Store in session state
            while len(st.session_state.audio_files) <= chunk_index:
                st.session_state.audio_files.append(None)
            st.session_state.audio_files[chunk_index] = audio_bytes.getvalue()
            
            st.success(f"✅ Audio generated for chunk {chunk_index + 1}!")
            
        except Exception as e:
            st.error(f"Error generating audio: {str(e)}")
        
        finally:
            # Cleanup in a finally block to ensure it always runs
            if voice_path and os.path.exists(voice_path):
                try:
                    os.unlink(voice_path)
                except:
                    pass

def generate_all_chunks(tts_model, text_chunks, voice_file, emotion_intensity, cfg_scale):
    """Generate audio for all text chunks"""
    # First verify SoundFile is available
    if not SOUNDFILE_AVAILABLE:
        st.error("SoundFile package is required but not installed. Please install with: pip install soundfile")
        return
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # Initialize audio files list
    st.session_state.audio_files = [None] * len(text_chunks)
    
    voice_path = None
    try:
        # Save voice file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmp_voice:
            tmp_voice.write(voice_file.read())
            voice_path = tmp_voice.name
        
        for i, text_chunk in enumerate(text_chunks):
            status_text.text(f"Generating audio for chunk {i+1}/{len(text_chunks)}...")
            
            try:                # Generate audio
                audio_data = tts_model.generate(
                    text_chunk,
                    audio_prompt_path=voice_path
                )
                
                # Convert to bytes
                audio_bytes = io.BytesIO()
                import torchaudio
                # Save as WAV using torchaudio (same as in example.py)
                torchaudio.save(audio_bytes, audio_data, tts_model.sr, format='wav')
                audio_bytes.seek(0)
                
                st.session_state.audio_files[i] = audio_bytes.getvalue()
                
            except Exception as e:
                st.warning(f"Error generating chunk {i+1}: {str(e)}")
                st.session_state.audio_files[i] = None
            
            # Update progress
            progress_bar.progress((i + 1) / len(text_chunks))
        
        status_text.text("✅ All audio chunks generated!")
        st.success(f"Generated audio for {len([a for a in st.session_state.audio_files if a])} out of {len(text_chunks)} chunks")
        
    except Exception as e:
        st.error(f"Error in batch generation: {str(e)}")
        
    finally:
        # Cleanup in a finally block to ensure it always runs
        if voice_path and os.path.exists(voice_path):
            try:
                os.unlink(voice_path)
            except:
                pass

if __name__ == "__main__":
    main()