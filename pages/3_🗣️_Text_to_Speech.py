"""
Text-to-Speech Page
Voice synthesis with XTTS v2, Edge TTS, and gTTS
"""

import streamlit as st
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.tts import XTTSEngine, EdgeTTSEngine, GTTSEngine, TTSManager, TTSEngineType
from src.consent import (
    ConsentManager, ConsentChecker, ConsentType,
    render_consent_check, get_required_consents
)

st.set_page_config(page_title="TTS - Voice Studio", page_icon="🗣️", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .engine-card {
        background: linear-gradient(135deg, #1e1e3f 0%, #2d2d5a 100%);
        border: 1px solid rgba(102, 126, 234, 0.3);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        text-align: center;
    }
    .engine-card.selected {
        border-color: #667eea;
        box-shadow: 0 0 20px rgba(102, 126, 234, 0.3);
    }
    .voice-preview {
        background: rgba(0,0,0,0.3);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .consent-badge {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 15px;
        font-size: 0.8em;
        margin: 2px;
    }
    .consent-granted { background: rgba(76, 175, 80, 0.2); color: #4CAF50; }
    .consent-pending { background: rgba(255, 152, 0, 0.2); color: #FF9800; }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'selected_engine' not in st.session_state:
    st.session_state.selected_engine = 'edge_tts'
if 'speaker_audio_path' not in st.session_state:
    st.session_state.speaker_audio_path = None
if 'last_synthesis' not in st.session_state:
    st.session_state.last_synthesis = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# Initialize engines
@st.cache_resource
def get_xtts_engine():
    return XTTSEngine(output_dir="output/tts")

@st.cache_resource
def get_edge_engine():
    return EdgeTTSEngine(output_dir="output/tts")

@st.cache_resource
def get_gtts_engine():
    return GTTSEngine(output_dir="output/tts")

@st.cache_resource
def get_consent_manager():
    return ConsentManager(storage_dir="data/consents")

@st.cache_resource
def get_consent_checker():
    return ConsentChecker(get_consent_manager())

consent_checker = get_consent_checker()

# Header
st.title("🗣️ Text-to-Speech Studio")
st.markdown("Convert text to natural-sounding speech")
st.markdown("---")

# Sidebar - Engine Selection
with st.sidebar:
    # User session info
    st.header("👤 User Session")
    if st.session_state.user_id:
        st.success(f"✅ {st.session_state.user_id}")
    else:
        st.warning("No user session")
        st.caption("Set your user ID on the Consent page")
    
    st.markdown("---")
    st.header("⚙️ Engine Selection")
    
    engine = st.radio(
        "Choose TTS Engine",
        options=['edge_tts', 'gtts', 'xtts_v2'],
        format_func=lambda x: {
            'edge_tts': '🎙️ Edge TTS (Recommended)',
            'gtts': '🌐 Google TTS',
            'xtts_v2': '🧬 XTTS v2 (Voice Cloning)'
        }[x],
        index=0
    )
    st.session_state.selected_engine = engine
    
    # Show required consents for selected engine
    st.markdown("---")
    st.subheader("📋 Required Consents")
    
    if engine == 'xtts_v2':
        required = get_required_consents('voice_cloning')
        st.caption("Voice cloning requires additional consents")
    else:
        required = get_required_consents('tts_basic')
    
    if st.session_state.user_id:
        for ct in required:
            has = consent_checker.has_consent(st.session_state.user_id, ct)
            badge_class = "consent-granted" if has else "consent-pending"
            icon = "✅" if has else "⏳"
            st.markdown(f'<span class="consent-badge {badge_class}">{icon} {ct.value.replace("_", " ").title()}</span>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Engine status
    st.subheader("📊 Engine Status")
    
    edge_engine = get_edge_engine()
    gtts_engine = get_gtts_engine()
    
    st.write(f"Edge TTS: {'✅' if edge_engine.available else '❌'}")
    st.write(f"gTTS: {'✅' if gtts_engine.available else '❌'}")
    
    try:
        xtts_engine = get_xtts_engine()
        status = xtts_engine.get_status()
        st.write(f"XTTS v2: {'✅' if status['tts_available'] else '❌'}")
        if status.get('gpu_available'):
            st.write(f"GPU: {status.get('gpu_name', 'Available')}")
    except Exception as e:
        st.write(f"XTTS v2: ❌ {str(e)[:30]}")

# Check consent before allowing TTS
if st.session_state.selected_engine == 'xtts_v2':
    required_consents = get_required_consents('voice_cloning')
    feature_name = "Voice Cloning (XTTS v2)"
else:
    required_consents = get_required_consents('tts_basic')
    feature_name = "Text-to-Speech"

has_consent = render_consent_check(
    consent_checker,
    st.session_state.user_id,
    required_consents,
    feature_name
)

if not has_consent:
    st.stop()

# Main content
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("📝 Text Input")
    
    text_input = st.text_area(
        "Enter text to synthesize",
        height=200,
        placeholder="Type or paste your text here...",
        value="Hello! Welcome to the Voice TTS Studio. This is a demonstration of text-to-speech synthesis."
    )
    
    char_count = len(text_input)
    word_count = len(text_input.split())
    st.caption(f"📊 {char_count} characters | {word_count} words")

with col2:
    st.subheader("🎛️ Settings")
    
    if st.session_state.selected_engine == 'edge_tts':
        # Voice source selection
        voice_source = st.radio(
            "Voice Source",
            options=["preset", "custom"],
            format_func=lambda x: "🎤 Preset Voices" if x == "preset" else "📁 Upload Custom Voice",
            horizontal=True,
            key="edge_voice_source"
        )
        
        if voice_source == "custom":
            st.info("🧬 **Custom Voice** requires XTTS v2 engine for voice cloning")
            
            # Voice upload
            custom_voice = st.file_uploader(
                "Upload your voice (10-30 sec)",
                type=['wav', 'mp3', 'ogg', 'm4a'],
                key="edge_custom_voice"
            )
            
            if custom_voice:
                from datetime import datetime
                voice_dir = Path("temp/voices")
                voice_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                voice_path = voice_dir / f"custom_{ts}_{custom_voice.name}"
                
                with open(voice_path, 'wb') as f:
                    f.write(custom_voice.getvalue())
                
                st.session_state.speaker_audio_path = str(voice_path)
                st.audio(custom_voice)
                st.success("✅ Voice uploaded!")
                
                # Auto-switch to XTTS v2
                if st.button("🧬 Switch to XTTS v2 & Use This Voice", type="primary", use_container_width=True):
                    st.session_state.selected_engine = 'xtts_v2'
                    st.rerun()
            
            language = st.selectbox(
                "Language",
                options=['en', 'es', 'fr', 'de', 'hi'],
                format_func=lambda x: {'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German', 'hi': 'Hindi'}.get(x, x),
                key="edge_custom_lang"
            )
            rate_str = "+0%"
            voice = None
        else:
            # Edge TTS preset settings
            language = st.selectbox(
                "Language",
                options=['en-US', 'en-GB', 'es-ES', 'fr-FR', 'de-DE', 'hi-IN'],
                index=0
            )
            
            voice_options = {
                'en-US': [('en-US-JennyNeural', 'Jenny (Female)'), 
                          ('en-US-GuyNeural', 'Guy (Male)'),
                          ('en-US-AriaNeural', 'Aria (Female)')],
                'en-GB': [('en-GB-SoniaNeural', 'Sonia (Female)'),
                          ('en-GB-RyanNeural', 'Ryan (Male)')],
                'es-ES': [('es-ES-ElviraNeural', 'Elvira (Female)')],
                'fr-FR': [('fr-FR-DeniseNeural', 'Denise (Female)')],
                'de-DE': [('de-DE-KatjaNeural', 'Katja (Female)')],
                'hi-IN': [('hi-IN-SwaraNeural', 'Swara (Female)')]
            }
            
            voices = voice_options.get(language, [('en-US-JennyNeural', 'Jenny')])
            voice = st.selectbox(
                "Voice",
                options=[v[0] for v in voices],
                format_func=lambda x: dict(voices).get(x, x)
            )
            
            rate = st.slider("Speed", -50, 50, 0, format="%d%%")
            rate_str = f"+{rate}%" if rate >= 0 else f"{rate}%"
        
    elif st.session_state.selected_engine == 'gtts':
        # Voice source selection
        voice_source = st.radio(
            "Voice Source",
            options=["preset", "custom"],
            format_func=lambda x: "🌐 Standard Voice" if x == "preset" else "📁 Upload Custom Voice",
            horizontal=True,
            key="gtts_voice_source"
        )
        
        if voice_source == "custom":
            st.info("🧬 **Custom Voice** requires XTTS v2 engine for voice cloning")
            
            custom_voice = st.file_uploader(
                "Upload your voice (10-30 sec)",
                type=['wav', 'mp3', 'ogg', 'm4a'],
                key="gtts_custom_voice"
            )
            
            if custom_voice:
                from datetime import datetime
                voice_dir = Path("temp/voices")
                voice_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime('%Y%m%d_%H%M%S')
                voice_path = voice_dir / f"custom_{ts}_{custom_voice.name}"
                
                with open(voice_path, 'wb') as f:
                    f.write(custom_voice.getvalue())
                
                st.session_state.speaker_audio_path = str(voice_path)
                st.audio(custom_voice)
                st.success("✅ Voice uploaded!")
                
                if st.button("🧬 Switch to XTTS v2 & Use This Voice", type="primary", use_container_width=True):
                    st.session_state.selected_engine = 'xtts_v2'
                    st.rerun()
            
            language = st.selectbox(
                "Language",
                options=['en', 'es', 'fr', 'de', 'hi'],
                format_func=lambda x: {'en': 'English', 'es': 'Spanish', 'fr': 'French', 'de': 'German', 'hi': 'Hindi'}.get(x, x),
                key="gtts_custom_lang"
            )
            slow = False
        else:
            # gTTS preset settings
            language = st.selectbox(
                "Language",
                options=['en', 'es', 'fr', 'de', 'it', 'pt', 'hi', 'ja', 'ko'],
                format_func=lambda x: {
                    'en': 'English', 'es': 'Spanish', 'fr': 'French',
                    'de': 'German', 'it': 'Italian', 'pt': 'Portuguese',
                    'hi': 'Hindi', 'ja': 'Japanese', 'ko': 'Korean'
                }.get(x, x)
            )
            
            slow = st.checkbox("Slow speech")
        
    else:  # XTTS v2
        st.info("🧬 Voice Cloning Mode - Upload or record a voice sample")
        
        language = st.selectbox(
            "Language",
            options=['en', 'es', 'fr', 'de', 'it', 'pt', 'pl', 'tr', 'ru', 'hi'],
            format_func=lambda x: {
                'en': 'English', 'es': 'Spanish', 'fr': 'French',
                'de': 'German', 'it': 'Italian', 'pt': 'Portuguese',
                'pl': 'Polish', 'tr': 'Turkish', 'ru': 'Russian', 'hi': 'Hindi'
            }.get(x, x)
        )
        
        speed = st.slider("Speech Speed", 0.5, 2.0, 1.0, 0.1)
        
        st.markdown("---")
        st.markdown("### 🎤 Reference Voice")
        
        # Tabs for upload/record
        voice_tab1, voice_tab2 = st.tabs(["📁 Upload", "🎙️ Record"])
        
        with voice_tab1:
            uploaded_voice = st.file_uploader(
                "Upload voice sample (10-30 sec)",
                type=['wav', 'mp3', 'ogg', 'm4a', 'flac'],
                help="Upload a clear voice sample for cloning"
            )
            
            if uploaded_voice:
                from datetime import datetime
                voice_dir = Path("temp/voices")
                voice_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                voice_path = voice_dir / f"ref_{timestamp}_{uploaded_voice.name}"
                
                with open(voice_path, 'wb') as f:
                    f.write(uploaded_voice.getvalue())
                
                st.session_state.speaker_audio_path = str(voice_path)
                st.session_state.voice_source = "upload"
                st.audio(uploaded_voice)
                st.success(f"✅ Voice ready: {uploaded_voice.name}")
                
                # Download and delete buttons
                col_dl, col_del = st.columns(2)
                with col_dl:
                    st.download_button(
                        "📥 Download",
                        uploaded_voice.getvalue(),
                        file_name=uploaded_voice.name,
                        mime="audio/wav",
                        key="dl_voice_upload",
                        use_container_width=True
                    )
                with col_del:
                    if st.button("🗑️ Clear", key="del_voice_upload", use_container_width=True):
                        if voice_path.exists():
                            voice_path.unlink()
                        st.session_state.speaker_audio_path = None
                        st.rerun()
        
        with voice_tab2:
            st.caption("🎤 Click to record your voice")
            
            recorded_voice = st.audio_input(
                "Record voice sample",
                label_visibility="collapsed",
                key="tts_voice_recorder"
            )
            
            if recorded_voice:
                from datetime import datetime
                voice_dir = Path("temp/voices")
                voice_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                record_path = voice_dir / f"recorded_{timestamp}.wav"
                
                audio_bytes = recorded_voice.read()
                with open(record_path, 'wb') as f:
                    f.write(audio_bytes)
                
                st.session_state.speaker_audio_path = str(record_path)
                st.session_state.voice_source = "recording"
                
                st.audio(audio_bytes, format="audio/wav")
                st.success("✅ Recording ready!")
                
                file_size = len(audio_bytes) / 1024
                st.caption(f"Size: {file_size:.1f} KB")
                
                col_dl, col_del = st.columns(2)
                with col_dl:
                    st.download_button(
                        "📥 Download",
                        audio_bytes,
                        file_name=f"voice_{timestamp}.wav",
                        mime="audio/wav",
                        key="dl_voice_rec",
                        use_container_width=True
                    )
                with col_del:
                    if st.button("🗑️ Delete", key="del_voice_rec", use_container_width=True):
                        if record_path.exists():
                            record_path.unlink()
                        st.session_state.speaker_audio_path = None
                        st.rerun()
        
        # Voice status indicator
        if st.session_state.speaker_audio_path:
            source = st.session_state.get('voice_source', 'upload')
            icon = "📁" if source == "upload" else "🎙️"
            st.success(f"{icon} Voice loaded and ready for cloning!")

# Synthesis button
st.markdown("---")

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    synthesize_clicked = st.button(
        "🎙️ Synthesize Speech",
        type="primary",
        use_container_width=True,
        disabled=len(text_input.strip()) == 0
    )

if synthesize_clicked:
    with st.spinner("🔊 Generating speech..."):
        try:
            # Check if custom voice is selected but not using XTTS v2
            if st.session_state.selected_engine == 'edge_tts' and voice is None:
                if st.session_state.speaker_audio_path:
                    # Auto-switch to XTTS v2 for custom voice
                    st.session_state.selected_engine = 'xtts_v2'
                    st.info("🧬 Switching to XTTS v2 for custom voice...")
                    st.rerun()
                else:
                    st.error("❌ Please upload a voice file or select a preset voice")
                    st.stop()
            
            if st.session_state.selected_engine == 'edge_tts':
                engine = get_edge_engine()
                result = engine.synthesize(
                    text=text_input,
                    voice=voice,
                    rate=rate_str
                )
                
            elif st.session_state.selected_engine == 'gtts':
                # Check if custom voice selected
                if 'gtts_voice_source' in st.session_state and st.session_state.gtts_voice_source == 'custom':
                    if st.session_state.speaker_audio_path:
                        st.session_state.selected_engine = 'xtts_v2'
                        st.info("🧬 Switching to XTTS v2 for custom voice...")
                        st.rerun()
                    else:
                        st.error("❌ Please upload a voice file or select a preset voice")
                        st.stop()
                
                engine = get_gtts_engine()
                result = engine.synthesize(
                    text=text_input,
                    language=language,
                    slow=slow
                )
                
            else:  # XTTS v2
                if not st.session_state.speaker_audio_path:
                    st.error("❌ Please upload or record a reference voice for voice cloning")
                    st.stop()
                
                engine = get_xtts_engine()
                
                # Check if model is loaded
                if not engine._model_loaded:
                    st.info("⏳ Loading XTTS v2 model (first time only, may take a few minutes)...")
                    engine.load_model()
                
                result = engine.synthesize(
                    text=text_input,
                    speaker_audio=st.session_state.speaker_audio_path,
                    language=language,
                    speed=speed
                )
            
            if result.success:
                st.session_state.last_synthesis = result
                st.success("✅ This is generated by Deepfake Me")
            else:
                st.error(f"❌ Synthesis failed: {result.error}")
                
        except Exception as e:
            st.error(f"❌ Error: {str(e)}")

# Audio output
if st.session_state.last_synthesis and st.session_state.last_synthesis.success:
    st.markdown("---")
    st.subheader("🎧 Generated Audio")
    
    result = st.session_state.last_synthesis
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        with open(result.audio_path, 'rb') as f:
            st.audio(f.read())
    
    with col2:
        st.markdown("**Details**")
        if hasattr(result, 'duration_seconds') and result.duration_seconds:
            st.write(f"Duration: {result.duration_seconds}s")
        if hasattr(result, 'inference_time_seconds') and result.inference_time_seconds:
            st.write(f"Generation: {result.inference_time_seconds}s")
        
        # Download button
        with open(result.audio_path, 'rb') as f:
            st.download_button(
                "📥 Download Audio",
                data=f.read(),
                file_name=Path(result.audio_path).name,
                mime="audio/wav"
            )

# Engine comparison
st.markdown("---")
st.subheader("🔄 Engine Comparison")

comp_col1, comp_col2, comp_col3 = st.columns(3)

with comp_col1:
    st.markdown("""
    <div class="engine-card">
        <h3>🎙️ Edge TTS</h3>
        <p><strong>Best for:</strong> General use</p>
        <p>• Free & unlimited</p>
        <p>• High quality voices</p>
        <p>• 100+ languages</p>
        <p>• No GPU required</p>
    </div>
    """, unsafe_allow_html=True)

with comp_col2:
    st.markdown("""
    <div class="engine-card">
        <h3>🌐 Google TTS</h3>
        <p><strong>Best for:</strong> Simple tasks</p>
        <p>• Free to use</p>
        <p>• Easy integration</p>
        <p>• Multiple languages</p>
        <p>• Internet required</p>
    </div>
    """, unsafe_allow_html=True)

with comp_col3:
    st.markdown("""
    <div class="engine-card">
        <h3>🧬 XTTS v2</h3>
        <p><strong>Best for:</strong> Voice cloning</p>
        <p>• Clone any voice</p>
        <p>• High fidelity</p>
        <p>• 17 languages</p>
        <p>• GPU recommended</p>
    </div>
    """, unsafe_allow_html=True)

# Footer
st.markdown("---")
st.caption("🗣️ Voice TTS Studio - Text-to-Speech Module")
