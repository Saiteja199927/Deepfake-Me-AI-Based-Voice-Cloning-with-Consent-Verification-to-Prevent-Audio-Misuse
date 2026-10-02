"""
Voice Cloning Studio Page
Advanced voice cloning with XTTS v2
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tts import XTTSEngine, SpeakerEmbedding
from src.consent import (
    ConsentManager, ConsentChecker, ConsentType,
    render_consent_check, get_required_consents
)
from src.safety import SafetyManager, render_safety_sidebar

st.set_page_config(
    page_title="Voice Cloning - Voice TTS",
    page_icon="🧬",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .clone-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        padding: 40px;
        text-align: center;
        margin-bottom: 30px;
    }
    .clone-header h1 {
        color: white;
        font-size: 2.5em;
        margin: 0;
    }
    .clone-header p {
        color: rgba(255,255,255,0.8);
        font-size: 1.2em;
        margin-top: 10px;
    }
    .voice-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid rgba(102, 126, 234, 0.3);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        transition: all 0.3s ease;
    }
    .voice-card:hover {
        border-color: #667eea;
        transform: translateY(-2px);
        box-shadow: 0 10px 30px rgba(102, 126, 234, 0.2);
    }
    .voice-name {
        color: #fff;
        font-size: 1.3em;
        font-weight: 600;
        margin-bottom: 5px;
    }
    .voice-meta {
        color: #888;
        font-size: 0.9em;
    }
    .step-indicator {
        display: flex;
        justify-content: center;
        gap: 20px;
        margin: 30px 0;
    }
    .step {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 10px 20px;
        border-radius: 25px;
        background: rgba(102, 126, 234, 0.1);
        color: #888;
    }
    .step.active {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    .step.completed {
        background: rgba(76, 175, 80, 0.2);
        color: #4CAF50;
    }
    .upload-zone {
        border: 2px dashed rgba(102, 126, 234, 0.5);
        border-radius: 15px;
        padding: 40px;
        text-align: center;
        background: rgba(102, 126, 234, 0.05);
        transition: all 0.3s ease;
    }
    .upload-zone:hover {
        border-color: #667eea;
        background: rgba(102, 126, 234, 0.1);
    }
    .quality-meter {
        height: 8px;
        background: rgba(255,255,255,0.1);
        border-radius: 4px;
        overflow: hidden;
    }
    .quality-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.3s ease;
    }
    .synthesis-panel {
        background: linear-gradient(135deg, #1e1e3f 0%, #2d2d5a 100%);
        border-radius: 20px;
        padding: 30px;
        margin-top: 20px;
    }
</style>
""", unsafe_allow_html=True)

# Session state
if 'clone_step' not in st.session_state:
    st.session_state.clone_step = 1
if 'selected_voice' not in st.session_state:
    st.session_state.selected_voice = None
if 'reference_audio_path' not in st.session_state:
    st.session_state.reference_audio_path = None
if 'voice_embedding' not in st.session_state:
    st.session_state.voice_embedding = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# Initialize components
@st.cache_resource
def get_xtts_engine():
    return XTTSEngine(output_dir="output/cloned")

@st.cache_resource
def get_consent_manager():
    return ConsentManager(storage_dir="data/consents")

@st.cache_resource
def get_consent_checker():
    return ConsentChecker(get_consent_manager())

@st.cache_resource
def get_safety_manager():
    return SafetyManager(storage_dir="data")

xtts_engine = get_xtts_engine()
consent_checker = get_consent_checker()
safety_manager = get_safety_manager()

# Sidebar
with st.sidebar:
    st.header("👤 User Session")
    if st.session_state.user_id:
        st.success(f"✅ {st.session_state.user_id}")
    else:
        st.warning("No user session")
        st.caption("Set user ID on Consent page")
    
    st.markdown("---")
    st.header("🧬 Voice Library")
    
    embeddings = xtts_engine.list_embeddings()
    st.metric("Saved Voices", len(embeddings))
    
    if embeddings:
        for emb in embeddings[:5]:
            st.markdown(f"• {emb['speaker_name']}")
    
    st.markdown("---")
    st.header("📊 Engine Status")
    status = xtts_engine.get_status()
    
    st.write(f"TTS: {'✅' if status['tts_available'] else '❌'}")
    st.write(f"GPU: {'✅' if status['gpu_available'] else '❌'}")
    if status['gpu_name']:
        st.caption(status['gpu_name'])
    
    # Safety sidebar
    render_safety_sidebar(safety_manager, st.session_state.user_id)

# Header
st.markdown("""
<div class="clone-header">
    <h1>🧬 Voice Cloning Studio</h1>
    <p>Create custom voice models from audio samples</p>
</div>
""", unsafe_allow_html=True)

# Consent check
required_consents = get_required_consents('voice_cloning')
has_consent = render_consent_check(
    consent_checker,
    st.session_state.user_id,
    required_consents,
    "Voice Cloning"
)

if not has_consent:
    st.stop()

# Step indicator
def render_step_indicator(current_step):
    steps = [
        ("1", "Upload Voice", current_step >= 1),
        ("2", "Process Audio", current_step >= 2),
        ("3", "Clone & Synthesize", current_step >= 3)
    ]
    
    html = '<div class="step-indicator">'
    for num, label, completed in steps:
        step_class = "active" if int(num) == current_step else ("completed" if completed else "")
        icon = "✓" if completed and int(num) < current_step else num
        html += f'<div class="step {step_class}"><span>{icon}</span><span>{label}</span></div>'
    html += '</div>'
    
    st.markdown(html, unsafe_allow_html=True)

render_step_indicator(st.session_state.clone_step)

# Main content based on step
if st.session_state.clone_step == 1:
    st.markdown("## Step 1: Provide Reference Voice")
    st.markdown("Upload a file or record your voice live for cloning.")
    
    # Tabs for upload vs record
    tab_upload, tab_record = st.tabs(["📁 Upload File", "🎤 Record Live"])
    
    with tab_upload:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            <div class="upload-zone">
                <h3>📁 Drop your audio here</h3>
                <p>Supported: WAV, MP3, OGG, M4A, FLAC (10-30 seconds recommended)</p>
            </div>
            """, unsafe_allow_html=True)
            
            uploaded_file = st.file_uploader(
                "Upload reference audio",
                type=['wav', 'mp3', 'ogg', 'm4a', 'flac'],
                label_visibility="collapsed",
                key="file_uploader"
            )
            
            if uploaded_file:
                # Save uploaded file
                upload_dir = Path("temp/voice_samples")
                upload_dir.mkdir(parents=True, exist_ok=True)
                
                file_path = upload_dir / f"ref_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
                with open(file_path, 'wb') as f:
                    f.write(uploaded_file.read())
                
                st.session_state.reference_audio_path = str(file_path)
                st.session_state.audio_source = "upload"
                st.success(f"✅ Uploaded: {uploaded_file.name}")
                
                # Audio preview
                st.audio(str(file_path))
                
                # Download and delete buttons for uploaded file
                col_dl, col_del = st.columns(2)
                with col_dl:
                    with open(file_path, 'rb') as f:
                        st.download_button(
                            "📥 Download",
                            f.read(),
                            file_name=uploaded_file.name,
                            mime="audio/wav",
                            key="download_uploaded",
                            use_container_width=True
                        )
                with col_del:
                    if st.button("🗑️ Delete", key="delete_uploaded", use_container_width=True, type="secondary"):
                        try:
                            if file_path.exists():
                                file_path.unlink()
                            st.session_state.reference_audio_path = None
                            st.session_state.audio_source = None
                            st.success("✅ File deleted permanently!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error deleting: {e}")
        
        with col2:
            st.markdown("### 📋 Guidelines")
            st.markdown("""
            **For best results:**
            - Use clear, high-quality audio
            - 10-30 seconds of speech
            - Minimal background noise
            - Single speaker only
            - Natural speaking pace
            
            **Audio quality tips:**
            - Use WAV format if possible
            - 16kHz+ sample rate
            - Avoid music/effects
            """)
    
    with tab_record:
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.markdown("""
            <div class="upload-zone" style="border-color: #4CAF50;">
                <h3>🎤 Record Your Voice</h3>
                <p>Click the microphone button and speak clearly for 10-30 seconds</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Recording quality settings
            st.markdown("### ⚙️ Recording Quality")
            quality_col1, quality_col2 = st.columns(2)
            
            with quality_col1:
                recording_quality = st.selectbox(
                    "Quality Preset",
                    options=["High Quality (48kHz)", "Standard (44.1kHz)", "Low Bandwidth (22kHz)"],
                    index=0,
                    help="Higher quality = larger file size"
                )
            
            with quality_col2:
                max_duration = st.slider(
                    "Max Duration (seconds)",
                    min_value=5,
                    max_value=60,
                    value=30,
                    help="Maximum recording duration"
                )
            
            st.markdown("---")
            
            # Live audio recording using st.audio_input
            st.markdown("### 🎙️ Start Recording")
            st.caption("Click the microphone button below to record. Click again to stop.")
            
            # Use st.audio_input for recording (Streamlit 1.29+)
            recorded_audio = st.audio_input(
                "Record your voice",
                label_visibility="collapsed",
                key="voice_recorder"
            )
            
            if recorded_audio:
                # Save recorded audio
                record_dir = Path("temp/recordings")
                record_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                record_path = record_dir / f"recording_{timestamp}.wav"
                
                # Read audio bytes and save
                audio_bytes = recorded_audio.read()
                
                with open(record_path, 'wb') as f:
                    f.write(audio_bytes)
                
                st.session_state.reference_audio_path = str(record_path)
                st.session_state.audio_source = "recording"
                
                st.success("✅ Recording captured successfully!")
                
                # Preview
                st.markdown("### 🎧 Recording Preview")
                st.audio(audio_bytes, format="audio/wav")
                
                # Recording details
                file_size = len(audio_bytes) / 1024  # KB
                st.caption(f"File size: {file_size:.1f} KB")
                
                # Download recorded audio
                col_dl, col_del = st.columns(2)
                with col_dl:
                    st.download_button(
                        "📥 Download",
                        audio_bytes,
                        file_name=f"voice_recording_{timestamp}.wav",
                        mime="audio/wav",
                        key="download_recording",
                        use_container_width=True
                    )
                with col_del:
                    if st.button("🗑️ Delete", key="delete_recording", use_container_width=True, type="secondary"):
                        # Delete the file permanently
                        try:
                            if Path(record_path).exists():
                                Path(record_path).unlink()
                            st.session_state.reference_audio_path = None
                            st.session_state.audio_source = None
                            st.success("✅ Recording deleted permanently!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error deleting: {e}")
                
                st.info("💡 **Tip:** Listen to your recording and re-record if needed for better quality.")
        
        with col2:
            st.markdown("### 🎤 Recording Tips")
            st.markdown("""
            **For high-quality recordings:**
            
            ✅ **Do:**
            - Find a quiet room
            - Speak at normal volume
            - Keep consistent distance from mic
            - Record 15-30 seconds
            - Use a good microphone if available
            
            ❌ **Avoid:**
            - Background noise
            - Echo/reverb
            - Speaking too fast
            - Multiple speakers
            - Music or TV sounds
            """)
            
            st.markdown("---")
            st.markdown("### 📊 Quality Info")
            
            quality_info = {
                "High Quality (48kHz)": {"rate": "48,000 Hz", "quality": "⭐⭐⭐⭐⭐", "size": "~4.6 MB/min"},
                "Standard (44.1kHz)": {"rate": "44,100 Hz", "quality": "⭐⭐⭐⭐", "size": "~4.2 MB/min"},
                "Low Bandwidth (22kHz)": {"rate": "22,050 Hz", "quality": "⭐⭐⭐", "size": "~2.1 MB/min"}
            }
            
            info = quality_info.get(recording_quality, quality_info["High Quality (48kHz)"])
            st.write(f"**Sample Rate:** {info['rate']}")
            st.write(f"**Quality:** {info['quality']}")
            st.write(f"**Est. Size:** {info['size']}")
    
    # Existing voices section
    st.markdown("---")
    st.markdown("### 📚 Or Select Existing Voice")
    
    embeddings = xtts_engine.list_embeddings()
    
    if embeddings:
        cols = st.columns(3)
        for i, emb in enumerate(embeddings):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="voice-card">
                    <div class="voice-name">🎭 {emb['speaker_name']}</div>
                    <div class="voice-meta">Created: {emb['created_at'][:10]}</div>
                </div>
                """, unsafe_allow_html=True)
                
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    if st.button(f"Use", key=f"use_{emb['embedding_id']}", use_container_width=True):
                        st.session_state.selected_voice = emb
                        st.session_state.clone_step = 3
                        st.rerun()
                with btn_col2:
                    if st.button(f"🗑️", key=f"delete_{emb['embedding_id']}", use_container_width=True, type="secondary"):
                        try:
                            # Delete the embedding
                            deleted = xtts_engine.delete_embedding(emb['embedding_id'])
                            if deleted:
                                st.success(f"✅ Deleted: {emb['speaker_name']}")
                                st.rerun()
                            else:
                                st.error("❌ Could not delete voice")
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
    else:
        st.info("No saved voices yet. Upload or record audio to create your first voice clone!")
    
    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col1:
        if st.session_state.reference_audio_path:
            source = st.session_state.get('audio_source', 'upload')
            source_icon = "📁" if source == "upload" else "🎤"
            st.success(f"{source_icon} Audio ready: {Path(st.session_state.reference_audio_path).name}")
    
    with col3:
        if st.button("Next →", type="primary", disabled=not st.session_state.reference_audio_path, use_container_width=True):
            st.session_state.clone_step = 2
            st.rerun()


elif st.session_state.clone_step == 2:
    st.markdown("## Step 2: Process Audio")
    st.markdown("We'll analyze your audio and extract the voice characteristics.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        if st.session_state.reference_audio_path:
            st.markdown("### 🎧 Reference Audio")
            st.audio(st.session_state.reference_audio_path)
            
            speaker_name = st.text_input(
                "Voice Name",
                value=f"Voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                help="Give this voice a memorable name"
            )
            
            if st.button("🧬 Extract Voice Profile", type="primary"):
                with st.spinner("Extracting voice characteristics..."):
                    try:
                        embedding = xtts_engine.extract_speaker_embedding(
                            st.session_state.reference_audio_path,
                            speaker_name
                        )
                        st.session_state.voice_embedding = embedding
                        st.session_state.selected_voice = {
                            'embedding_id': embedding.embedding_id,
                            'speaker_name': embedding.speaker_name
                        }
                        
                        st.success("✅ Voice profile extracted successfully!")
                        
                        # Auto-advance
                        st.session_state.clone_step = 3
                        st.rerun()
                        
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
        else:
            st.warning("No reference audio selected. Go back to Step 1.")
    
    with col2:
        st.markdown("### 📊 Processing Info")
        st.markdown("""
        **What happens:**
        1. Audio is analyzed for voice features
        2. Speaker embedding is extracted
        3. Voice profile is saved for reuse
        
        **Note:** This may take a moment for the first voice.
        """)
        
        if xtts_engine.get_status()['gpu_available']:
            st.success("🚀 GPU acceleration active")
        else:
            st.warning("⚠️ Using CPU (slower)")
    
    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← Back"):
            st.session_state.clone_step = 1
            st.rerun()

elif st.session_state.clone_step == 3:
    st.markdown("## Step 3: Clone & Synthesize")
    
    if st.session_state.selected_voice:
        voice = st.session_state.selected_voice
        st.success(f"🎭 Using voice: **{voice['speaker_name']}**")
    
    st.markdown("""
    <div class="synthesis-panel">
        <h3 style="color: white; margin-top: 0;">✍️ Enter Text to Synthesize</h3>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        text_input = st.text_area(
            "Text to synthesize",
            height=150,
            placeholder="Enter the text you want to convert to speech...",
            max_chars=5000
        )
        
        st.caption(f"Characters: {len(text_input)}/5000")
        
        # Language selection
        languages = xtts_engine.get_supported_languages()
        language_codes = [l['code'] for l in languages]
        
        # Default to Indian English (en-in)
        default_index = 0
        if "en-in" in language_codes:
            default_index = language_codes.index("en-in")
        
        language = st.selectbox(
            "Language",
            options=language_codes,
            format_func=lambda x: next(l['name'] for l in languages if l['code'] == x),
            index=default_index
        )
        
        # Show accent guidance for English variants
        if language == "en-in":
            st.success(
                "🇮🇳 **Indian English** selected! The cloned voice will reproduce the full Indian accent "
                "from your reference audio. For best results:\n"
                "- Use a 15-30 second reference clip of clear Indian English speech\n"
                "- Keep Accent Fidelity slider at maximum (1.0) in Settings\n"
                "- The model uses optimized parameters to preserve Indian prosody and intonation"
            )
        elif language in ("en-us", "en-gb"):
            accent_name = next(l['name'] for l in languages if l['code'] == language)
            st.info(f"🗣️ **{accent_name}** selected. Use a reference voice sample "
                    f"from a speaker with a matching accent for best results.")
    
    with col2:
        st.markdown("### ⚙️ Settings")
        
        speed = st.slider("Speed", 0.5, 2.0, 1.0, 0.1)
        
        # Accent Fidelity control
        st.markdown("---")
        st.markdown("### 🎯 Accent Fidelity")
        
        # Default to max fidelity for Indian English
        default_fidelity = 1.0 if language == "en-in" else 0.7
        accent_fidelity = st.slider(
            "Accent Strength",
            min_value=0.0,
            max_value=1.0,
            value=default_fidelity,
            step=0.1,
            help=(
                "Controls how closely the cloned voice matches the reference speaker's accent. "
                "1.0 = Maximum fidelity (exact accent reproduction). "
                "Lower values allow more variation."
            )
        )
        
        if language == "en-in":
            if accent_fidelity >= 0.8:
                st.caption("🟢 Maximum Indian accent preservation")
            elif accent_fidelity >= 0.5:
                st.caption("🟡 Moderate accent preservation")
            else:
                st.caption("🔴 Low fidelity — accent may drift")
        
        st.markdown("---")
        st.markdown("### 📊 Voice Info")
        
        if st.session_state.selected_voice:
            st.write(f"**Name:** {st.session_state.selected_voice['speaker_name']}")
            st.write(f"**ID:** {st.session_state.selected_voice['embedding_id'][:8]}...")
    
    # Synthesize button
    if st.button("🎙️ Generate Speech", type="primary", use_container_width=True):
        if not text_input.strip():
            st.warning("Please enter some text to synthesize.")
        else:
            # Safety checks
            allowed, filtered_text, error = safety_manager.pre_synthesis_check(
                st.session_state.user_id or "anonymous",
                text_input
            )
            
            if not allowed:
                st.error(f"❌ {error}")
            else:
                with st.spinner("🧬 Synthesizing with cloned voice..."):
                    try:
                        # Get reference audio path
                        if st.session_state.reference_audio_path:
                            speaker_audio = st.session_state.reference_audio_path
                        elif st.session_state.selected_voice:
                            embedding = xtts_engine.get_embedding(
                                st.session_state.selected_voice['embedding_id']
                            )
                            if embedding:
                                speaker_audio = embedding.source_audio_path
                            else:
                                st.error("Voice embedding not found!")
                                st.stop()
                        else:
                            st.error("No voice selected!")
                            st.stop()
                        
                        result = xtts_engine.synthesize(
                            text=filtered_text,
                            speaker_audio=speaker_audio,
                            language=language,
                            speed=speed,
                            accent_fidelity=accent_fidelity
                        )
                        
                        if result.success:
                            st.success("✅ Speech synthesized successfully!")
                            
                            # Audio player
                            st.audio(result.audio_path)
                            
                            # Post-processing
                            safety_manager.post_synthesis_process(
                                st.session_state.user_id or "anonymous",
                                result.audio_path,
                                filtered_text,
                                result.duration_seconds
                            )
                            
                            # Download button
                            with open(result.audio_path, 'rb') as f:
                                st.download_button(
                                    "📥 Download Audio",
                                    f.read(),
                                    file_name=f"cloned_voice_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav",
                                    mime="audio/wav"
                                )
                            
                            # Stats
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Duration", f"{result.duration_seconds}s")
                            with col2:
                                st.metric("Inference", f"{result.inference_time_seconds}s")
                            with col3:
                                st.metric("Language", language.upper())
                        else:
                            st.error(f"❌ Synthesis failed: {result.error}")
                    
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")
    
    # Navigation
    st.markdown("---")
    col1, col2, col3 = st.columns([1, 2, 1])
    with col1:
        if st.button("← New Voice"):
            st.session_state.clone_step = 1
            st.session_state.reference_audio_path = None
            st.session_state.selected_voice = None
            st.rerun()
