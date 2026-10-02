"""
Voice TTS Application
Main Streamlit application entry point
"""

import streamlit as st
from pathlib import Path

# Page configuration
st.set_page_config(
    page_title="Voice TTS App",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for stunning design
st.markdown("""
<style>
    /* Main container styling */
    .main {
        background: linear-gradient(180deg, #0f0f23 0%, #1a1a2e 100%);
    }
    
    /* Header styling */
    .header-title {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 50%, #f093fb 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3.5em;
        font-weight: 800;
        text-align: center;
        margin-bottom: 0;
    }
    
    .header-subtitle {
        color: #888;
        text-align: center;
        font-size: 1.2em;
        margin-top: 5px;
    }
    
    /* Feature cards */
    .feature-card {
        background: linear-gradient(135deg, #1e1e3f 0%, #2d2d5a 100%);
        border: 1px solid rgba(102, 126, 234, 0.3);
        border-radius: 20px;
        padding: 30px;
        margin: 10px 0;
        transition: all 0.3s ease;
        box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
    }
    
    .feature-card:hover {
        transform: translateY(-5px);
        border-color: rgba(102, 126, 234, 0.8);
        box-shadow: 0 12px 40px rgba(102, 126, 234, 0.2);
    }
    
    .feature-icon {
        font-size: 3em;
        margin-bottom: 15px;
    }
    
    .feature-title {
        color: #fff;
        font-size: 1.5em;
        font-weight: 600;
        margin-bottom: 10px;
    }
    
    .feature-desc {
        color: #aaa;
        font-size: 1em;
        line-height: 1.6;
    }
    
    /* Stats section */
    .stats-container {
        display: flex;
        justify-content: center;
        gap: 40px;
        margin: 40px 0;
    }
    
    .stat-item {
        text-align: center;
        background: rgba(102, 126, 234, 0.1);
        padding: 20px 40px;
        border-radius: 15px;
        border: 1px solid rgba(102, 126, 234, 0.2);
    }
    
    .stat-number {
        font-size: 2.5em;
        font-weight: 800;
        background: linear-gradient(90deg, #667eea, #764ba2);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .stat-label {
        color: #888;
        font-size: 0.9em;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    
    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 12px 30px;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: scale(1.05);
        box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4);
    }
    
    /* Sidebar */
    .css-1d391kg {
        background: linear-gradient(180deg, #1a1a2e 0%, #16213e 100%);
    }
    
    /* Progress bar */
    .stProgress > div > div > div > div {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    }
    
    /* Info boxes */
    .info-box {
        background: rgba(102, 126, 234, 0.1);
        border-left: 4px solid #667eea;
        padding: 15px 20px;
        border-radius: 0 10px 10px 0;
        margin: 10px 0;
    }
    
    /* Animation keyframes */
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
    
    .animate-in {
        animation: fadeInUp 0.6s ease-out;
    }
</style>
""", unsafe_allow_html=True)


def main():
    """Main application entry point"""
    
    # Header
    st.markdown('<h1 class="header-title">🎙️ Voice TTS Studio</h1>', unsafe_allow_html=True)
    st.markdown('<p class="header-subtitle">Professional Text-to-Speech & Audio Processing Suite</p>', unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Quick Stats
    st.markdown("""
    <div class="stats-container">
        <div class="stat-item">
            <div class="stat-number">7+</div>
            <div class="stat-label">Audio Formats</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">3</div>
            <div class="stat-label">TTS Engines</div>
        </div>
        <div class="stat-item">
            <div class="stat-number">10+</div>
            <div class="stat-label">Quality Metrics</div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # Feature Cards
    st.markdown("## 🚀 Features")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("""
        <div class="feature-card animate-in">
            <div class="feature-icon">🎵</div>
            <div class="feature-title">Audio Upload & Analysis</div>
            <div class="feature-desc">
                Upload audio files for comprehensive analysis. Check quality metrics,
                detect noise levels, validate formats, and get actionable insights.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="feature-card animate-in">
            <div class="feature-icon">🧬</div>
            <div class="feature-title">Voice Cloning</div>
            <div class="feature-desc">
                Clone any voice using XTTS v2. Upload a reference audio sample
                and create custom voice models for realistic speech synthesis.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="feature-card animate-in">
            <div class="feature-icon">🛡️</div>
            <div class="feature-title">Safety & Security</div>
            <div class="feature-desc">
                Content filtering, audio watermarking, and rate limiting.
                Keep your usage secure with comprehensive safety features.
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="feature-card animate-in">
            <div class="feature-icon">🗣️</div>
            <div class="feature-title">Text-to-Speech</div>
            <div class="feature-desc">
                Convert text to natural-sounding speech using multiple TTS engines.
                Choose from Edge TTS, gTTS, or XTTS v2 with voice cloning.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="feature-card animate-in">
            <div class="feature-icon">📋</div>
            <div class="feature-title">Consent Management</div>
            <div class="feature-desc">
                GDPR-compliant consent workflows with cryptographic proofs.
                Manage privacy settings and data processing agreements.
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown("""
        <div class="feature-card animate-in">
            <div class="feature-icon">📥</div>
            <div class="feature-title">Downloads & History</div>
            <div class="feature-desc">
                Browse, play, and download all your generated audio files.
                Track usage statistics and export reports.
            </div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Getting Started Section
    st.markdown("## 🎯 Getting Started")
    
    st.markdown("""
    <div class="info-box">
        <strong>👋 Welcome!</strong> Use the sidebar navigation or the buttons below to access different features:
        <ul>
            <li><strong>Audio Upload</strong> - Upload and analyze audio files</li>
            <li><strong>Consent</strong> - Complete required consent workflows</li>
            <li><strong>Text-to-Speech</strong> - Convert text to speech with multiple engines</li>
            <li><strong>Voice Cloning</strong> - Clone voices with XTTS v2</li>
            <li><strong>Downloads</strong> - View and download your generated files</li>
            <li><strong>Safety Dashboard</strong> - Monitor usage and content filtering</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick Action Buttons - Two rows of 3
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("🎵 Upload Audio", use_container_width=True):
            st.switch_page("pages/1_🎵_Audio_Upload.py")
    
    with col2:
        if st.button("📋 Consent", use_container_width=True):
            st.switch_page("pages/2_📋_Consent.py")
    
    with col3:
        if st.button("🗣️ Text to Speech", use_container_width=True):
            st.switch_page("pages/3_🗣️_Text_to_Speech.py")
    
    col4, col5, col6 = st.columns(3)
    
    with col4:
        if st.button("🧬 Voice Cloning", use_container_width=True):
            st.switch_page("pages/4_🧬_Voice_Cloning.py")
    
    with col5:
        if st.button("📥 Downloads", use_container_width=True):
            st.switch_page("pages/5_📥_Downloads.py")
    
    with col6:
        if st.button("🛡️ Safety Dashboard", use_container_width=True):
            st.switch_page("pages/6_🛡️_Safety_Dashboard.py")
    
    # System Status
    st.markdown("---")
    st.markdown("## 📊 System Status")
    
    status_col1, status_col2, status_col3 = st.columns(3)
    
    with status_col1:
        try:
            from pydub import AudioSegment
            st.success("✅ PyDub: Available")
        except:
            st.error("❌ PyDub: Not Available")
    
    with status_col2:
        try:
            import librosa
            st.success("✅ Librosa: Available")
        except:
            st.warning("⚠️ Librosa: Not Available")
    
    with status_col3:
        try:
            import edge_tts
            st.success("✅ Edge-TTS: Available")
        except:
            st.warning("⚠️ Edge-TTS: Not Available")
    
    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; color: #666; padding: 20px;">
        <p>🎙️ <strong>Voice TTS Studio</strong> v1.0.0</p>
        <p style="font-size: 0.9em;">Built with ❤️ using Streamlit</p>
    </div>
    """, unsafe_allow_html=True)


# Sidebar content
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/microphone.png", width=80)
    st.markdown("### 🎙️ Voice TTS Studio")
    st.markdown("---")
    
    st.markdown("#### 📂 Navigation")
    st.page_link("app.py", label="🏠 Home", icon="🏠")
    st.page_link("pages/1_🎵_Audio_Upload.py", label="🎵 Audio Upload", icon="🎵")
    st.page_link("pages/2_📋_Consent.py", label="📋 Consent", icon="📋")
    st.page_link("pages/3_🗣️_Text_to_Speech.py", label="🗣️ Text to Speech", icon="🗣️")
    
    st.markdown("---")
    st.markdown("#### 📈 Quick Stats")
    
    # Check output directory for files
    output_dir = Path("output")
    if output_dir.exists():
        output_files = list(output_dir.glob("*.*"))
        st.metric("Output Files", len(output_files))
    else:
        st.metric("Output Files", 0)
    
    temp_dir = Path("temp")
    if temp_dir.exists():
        temp_files = list(temp_dir.rglob("*.*"))
        st.metric("Temp Files", len(temp_files))
    else:
        st.metric("Temp Files", 0)


if __name__ == "__main__":
    main()
