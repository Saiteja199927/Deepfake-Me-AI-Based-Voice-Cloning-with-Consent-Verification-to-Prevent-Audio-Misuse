"""
Audio Upload & Analysis Page
Upload audio files for processing and quality analysis
"""

import streamlit as st
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.audio import AudioProcessor, AudioValidator, UploadHandler
from src.consent import (
    ConsentManager, ConsentChecker, ConsentType,
    render_consent_check, get_required_consents
)

# Page configuration
st.set_page_config(
    page_title="Audio Upload - Voice TTS",
    page_icon="🎵",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .upload-box {
        border: 2px dashed #4CAF50;
        border-radius: 10px;
        padding: 20px;
        text-align: center;
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 15px;
        border-radius: 10px;
        color: white;
        text-align: center;
    }
    .quality-good { color: #4CAF50; }
    .quality-warning { color: #FFC107; }
    .quality-bad { color: #f44336; }
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    .consent-info {
        background: rgba(76, 175, 80, 0.1);
        border-left: 4px solid #4CAF50;
        padding: 10px 15px;
        border-radius: 0 8px 8px 0;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'uploaded_file_path' not in st.session_state:
    st.session_state.uploaded_file_path = None
if 'audio_info' not in st.session_state:
    st.session_state.audio_info = None
if 'quality_report' not in st.session_state:
    st.session_state.quality_report = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# Initialize components
@st.cache_resource
def get_processor():
    return AudioProcessor(output_dir="output")

@st.cache_resource
def get_validator():
    return AudioValidator()

@st.cache_resource
def get_upload_handler():
    return UploadHandler(upload_dir="temp/uploads", max_size_mb=100)

@st.cache_resource
def get_consent_manager():
    return ConsentManager(storage_dir="data/consents")

@st.cache_resource
def get_consent_checker():
    return ConsentChecker(get_consent_manager())

processor = get_processor()
validator = get_validator()
upload_handler = get_upload_handler()
consent_checker = get_consent_checker()

# Header
st.title("🎵 Audio Upload & Analysis")
st.markdown("Upload audio files for processing, validation, and quality analysis.")
st.markdown("---")

# Sidebar - Supported Formats
with st.sidebar:
    st.header("👤 User Session")
    
    # User ID from consent page (shared via session state)
    if st.session_state.user_id:
        st.success(f"✅ {st.session_state.user_id}")
        
        # Show consent status
        required_consents = get_required_consents('audio_processing')
        has_all = consent_checker.has_all_consents(st.session_state.user_id, required_consents)
        
        if has_all:
            st.markdown('<div class="consent-info">✅ All required consents granted</div>', unsafe_allow_html=True)
        else:
            missing = consent_checker.get_missing_consents(st.session_state.user_id, required_consents)
            st.warning(f"⚠️ {len(missing)} consent(s) pending")
    else:
        st.warning("No user session")
        st.caption("Set your user ID on the Consent page")
    
    st.markdown("---")
    st.header("📋 Supported Formats")
    formats = validator.get_supported_formats()
    for fmt in formats:
        st.write(f"• `.{fmt['extension']}` - {fmt['name']}")
    
    st.markdown("---")
    st.header("⚙️ Settings")
    max_file_size = st.slider("Max File Size (MB)", 10, 200, 100)
    auto_analyze = st.checkbox("Auto-analyze on upload", value=True)

# Consent check before main content
required_consents = get_required_consents('audio_processing')
has_consent = render_consent_check(
    consent_checker,
    st.session_state.user_id,
    required_consents,
    "Audio Upload & Processing"
)

if not has_consent:
    st.stop()

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.subheader("📤 Upload Audio File")
    
    uploaded_file = st.file_uploader(
        "Choose an audio file",
        type=['mp3', 'wav', 'ogg', 'flac', 'm4a', 'aac', 'wma'],
        help="Upload an audio file for processing and analysis"
    )
    
    if uploaded_file:
        # Validate upload
        file_bytes = uploaded_file.getvalue()
        validation = validator.validate_upload(
            file_bytes, 
            uploaded_file.name,
            max_size_mb=max_file_size
        )
        
        # Show validation results
        if validation.is_valid:
            st.success("✅ File validation passed!")
            
            # Save file
            success, result, _ = upload_handler.save_upload(
                file_bytes, 
                uploaded_file.name,
                validate=False  # Already validated
            )
            
            if success:
                st.session_state.uploaded_file_path = result
                st.info(f"📁 Saved to: `{Path(result).name}`")
                
                # Display audio player
                st.audio(file_bytes, format=f"audio/{validation.extension}")
                
                # Get audio info
                if auto_analyze:
                    with st.spinner("Analyzing audio..."):
                        st.session_state.audio_info = processor.get_audio_info(result)
                        st.session_state.quality_report = processor.analyze_quality(result)
            else:
                st.error(f"❌ Failed to save: {result}")
        else:
            st.error("❌ Validation Failed")
            for error in validation.errors:
                st.error(f"• {error}")
        
        # Show warnings
        if validation.warnings:
            for warning in validation.warnings:
                st.warning(f"⚠️ {warning}")

with col2:
    st.subheader("📊 File Information")
    
    if st.session_state.audio_info:
        info = st.session_state.audio_info
        
        # Basic info metrics
        metric_cols = st.columns(3)
        with metric_cols[0]:
            st.metric("Duration", info.get('duration_formatted', 'N/A'))
        with metric_cols[1]:
            st.metric("Sample Rate", f"{info.get('sample_rate', 0):,} Hz")
        with metric_cols[2]:
            st.metric("Channels", "Stereo" if info.get('channels', 1) == 2 else "Mono")
        
        metric_cols2 = st.columns(3)
        with metric_cols2[0]:
            st.metric("Format", info.get('format', 'N/A').upper())
        with metric_cols2[1]:
            st.metric("Bit Depth", f"{info.get('bit_depth', 'N/A')} bit")
        with metric_cols2[2]:
            st.metric("File Size", f"{info.get('file_size_mb', 0)} MB")
        
        # Bitrate
        if 'bitrate_kbps' in info:
            st.metric("Bitrate", f"{info['bitrate_kbps']} kbps")
    else:
        st.info("📤 Upload a file to see its information")

# Quality Analysis Section
st.markdown("---")
st.subheader("🔍 Quality Analysis")

if st.session_state.quality_report:
    report = st.session_state.quality_report
    metrics = report.get('metrics', {})
    
    # Quality Score
    score = report.get('quality_score', 0)
    score_color = "quality-good" if score >= 70 else "quality-warning" if score >= 40 else "quality-bad"
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"""
        <div style="text-align: center; padding: 20px;">
            <h1 class="{score_color}" style="font-size: 4em; margin: 0;">{score}</h1>
            <p style="font-size: 1.2em; color: #888;">Quality Score</p>
        </div>
        """, unsafe_allow_html=True)
        
        st.progress(score / 100)
    
    # Detailed Metrics
    st.markdown("### 📈 Detailed Metrics")
    
    metric_cols = st.columns(4)
    
    with metric_cols[0]:
        st.markdown("**🔊 Volume**")
        rms_db = metrics.get('rms_db', -100)
        st.write(f"RMS Level: {rms_db:.1f} dB")
        st.write(f"Peak: {metrics.get('peak_amplitude', 0):.3f}")
    
    with metric_cols[1]:
        st.markdown("**📊 Dynamics**")
        st.write(f"Dynamic Range: {metrics.get('dynamic_range_db', 0):.1f} dB")
        st.write(f"Silence: {metrics.get('silence_ratio', 0)*100:.1f}%")
    
    with metric_cols[2]:
        st.markdown("**🔇 Noise**")
        snr = metrics.get('estimated_snr_db', 0)
        snr_label = "Excellent" if snr > 40 else "Good" if snr > 30 else "Fair" if snr > 20 else "Poor"
        st.write(f"Est. SNR: {snr:.1f} dB")
        st.write(f"Level: {snr_label}")
    
    with metric_cols[3]:
        st.markdown("**📐 Technical**")
        st.write(f"Sample Rate: {metrics.get('sample_rate', 0):,} Hz")
        st.write(f"ZCR: {metrics.get('zero_crossing_rate', 0):.4f}")
    
    # Issues and Recommendations
    if report.get('issues'):
        st.markdown("### ⚠️ Issues Detected")
        for issue in report['issues']:
            st.warning(issue)
    
    if report.get('recommendations'):
        st.markdown("### 💡 Recommendations")
        for rec in report['recommendations']:
            st.info(rec)

elif st.session_state.uploaded_file_path:
    if st.button("🔍 Analyze Quality", type="primary"):
        with st.spinner("Analyzing audio quality..."):
            st.session_state.quality_report = processor.analyze_quality(
                st.session_state.uploaded_file_path
            )
            st.rerun()
else:
    st.info("📤 Upload a file to analyze its quality")

# Format Conversion Section
st.markdown("---")
st.subheader("🔄 Format Conversion")

if st.session_state.uploaded_file_path:
    col1, col2, col3 = st.columns(3)
    
    with col1:
        target_format = st.selectbox(
            "Target Format",
            options=['mp3', 'wav', 'ogg', 'flac'],
            index=0
        )
    
    with col2:
        target_sample_rate = st.selectbox(
            "Sample Rate",
            options=[8000, 16000, 22050, 44100, 48000],
            index=2,
            format_func=lambda x: f"{x:,} Hz"
        )
    
    with col3:
        target_channels = st.selectbox(
            "Channels",
            options=[1, 2],
            index=0,
            format_func=lambda x: "Mono" if x == 1 else "Stereo"
        )
    
    if st.button("🔄 Convert", type="primary"):
        with st.spinner("Converting audio..."):
            try:
                output_path = processor.convert_format(
                    st.session_state.uploaded_file_path,
                    target_format,
                    sample_rate=target_sample_rate,
                    channels=target_channels
                )
                st.success(f"✅ Converted successfully!")
                
                # Offer download
                with open(output_path, 'rb') as f:
                    st.download_button(
                        label="📥 Download Converted File",
                        data=f.read(),
                        file_name=Path(output_path).name,
                        mime=f"audio/{target_format}"
                    )
            except Exception as e:
                st.error(f"❌ Conversion failed: {str(e)}")
else:
    st.info("📤 Upload a file to enable format conversion")

# Quick Actions
st.markdown("---")
st.subheader("⚡ Quick Actions")

if st.session_state.uploaded_file_path:
    action_cols = st.columns(4)
    
    with action_cols[0]:
        if st.button("🔊 Normalize Audio", use_container_width=True):
            with st.spinner("Normalizing..."):
                try:
                    output_path = processor.normalize_audio(
                        st.session_state.uploaded_file_path
                    )
                    st.success("Normalized!")
                    with open(output_path, 'rb') as f:
                        st.download_button(
                            "📥 Download",
                            f.read(),
                            Path(output_path).name
                        )
                except Exception as e:
                    st.error(str(e))
    
    with action_cols[1]:
        if st.button("✂️ Trim Silence", use_container_width=True):
            with st.spinner("Trimming..."):
                try:
                    output_path = processor.trim_silence(
                        st.session_state.uploaded_file_path
                    )
                    st.success("Trimmed!")
                    with open(output_path, 'rb') as f:
                        st.download_button(
                            "📥 Download",
                            f.read(),
                            Path(output_path).name
                        )
                except Exception as e:
                    st.error(str(e))
    
    with action_cols[2]:
        if st.button("🎚️ Check Sample Rate", use_container_width=True):
            result = processor.check_sample_rate(st.session_state.uploaded_file_path)
            if result['meets_requirement']:
                st.success(f"✅ {result['current_sample_rate']:,} Hz - Good!")
            else:
                st.warning(f"⚠️ {result['current_sample_rate']:,} Hz - {result['recommendation']}")
    
    with action_cols[3]:
        if st.button("🔇 Check Noise Level", use_container_width=True):
            result = processor.detect_noise_level(st.session_state.uploaded_file_path)
            if 'error' in result:
                st.error(result['error'])
            else:
                st.info(f"{result['noise_level']}: {result['description']}")
else:
    st.info("📤 Upload a file to unlock quick actions")

# Footer
st.markdown("---")
st.caption("🎵 Voice TTS Application - Audio Processing Module")
