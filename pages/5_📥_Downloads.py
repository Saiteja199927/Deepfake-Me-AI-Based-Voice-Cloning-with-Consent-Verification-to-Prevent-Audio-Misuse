"""
Downloads & History Page
View and download generated audio files
"""

import streamlit as st
import sys
import os
from pathlib import Path
from datetime import datetime
import json

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.safety import SafetyManager, UsageTracker

st.set_page_config(
    page_title="Downloads - Voice TTS",
    page_icon="📥",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .download-header {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        border-radius: 20px;
        padding: 40px;
        text-align: center;
        margin-bottom: 30px;
    }
    .download-header h1 {
        color: white;
        font-size: 2.5em;
        margin: 0;
    }
    .file-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid rgba(102, 126, 234, 0.3);
        border-radius: 15px;
        padding: 20px;
        margin: 10px 0;
        transition: all 0.3s ease;
    }
    .file-card:hover {
        border-color: #667eea;
        transform: translateY(-2px);
    }
    .file-name {
        color: #fff;
        font-size: 1.1em;
        font-weight: 600;
    }
    .file-meta {
        color: #888;
        font-size: 0.85em;
        margin-top: 5px;
    }
    .file-actions {
        display: flex;
        gap: 10px;
        margin-top: 15px;
    }
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(4, 1fr);
        gap: 20px;
        margin: 30px 0;
    }
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 15px;
        padding: 25px;
        text-align: center;
        color: white;
    }
    .stat-value {
        font-size: 2.5em;
        font-weight: 700;
    }
    .stat-label {
        font-size: 0.9em;
        opacity: 0.9;
    }
    .filter-bar {
        background: rgba(102, 126, 234, 0.1);
        border-radius: 10px;
        padding: 15px 20px;
        margin-bottom: 20px;
    }
    .empty-state {
        text-align: center;
        padding: 60px 20px;
        color: #888;
    }
    .empty-state h3 {
        color: #aaa;
        margin-bottom: 10px;
    }
</style>
""", unsafe_allow_html=True)

# Session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = None

# Initialize components
@st.cache_resource
def get_safety_manager():
    return SafetyManager(storage_dir="data")

safety_manager = get_safety_manager()

# Helper functions
def get_output_files():
    """Get all output files with metadata."""
    files = []
    output_dirs = [
        Path("output/tts"),
        Path("output/cloned"),
        Path("output")
    ]
    
    for output_dir in output_dirs:
        if output_dir.exists():
            for file_path in output_dir.rglob("*.wav"):
                stat = file_path.stat()
                files.append({
                    'path': str(file_path),
                    'name': file_path.name,
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'created': datetime.fromtimestamp(stat.st_mtime),
                    'type': 'cloned' if 'clone' in str(file_path).lower() else 'tts',
                    'dir': file_path.parent.name
                })
            
            for file_path in output_dir.rglob("*.mp3"):
                stat = file_path.stat()
                files.append({
                    'path': str(file_path),
                    'name': file_path.name,
                    'size_mb': round(stat.st_size / (1024 * 1024), 2),
                    'created': datetime.fromtimestamp(stat.st_mtime),
                    'type': 'tts',
                    'dir': file_path.parent.name
                })
    
    # Sort by creation time (newest first)
    files.sort(key=lambda x: x['created'], reverse=True)
    return files

def format_file_size(size_mb):
    """Format file size for display."""
    if size_mb < 1:
        return f"{int(size_mb * 1024)} KB"
    return f"{size_mb:.1f} MB"

def format_time_ago(dt):
    """Format datetime as relative time."""
    now = datetime.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    elif diff.seconds > 3600:
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif diff.seconds > 60:
        mins = diff.seconds // 60
        return f"{mins} minute{'s' if mins > 1 else ''} ago"
    else:
        return "Just now"

# Sidebar
with st.sidebar:
    st.header("👤 User Session")
    if st.session_state.user_id:
        st.success(f"✅ {st.session_state.user_id}")
        
        # Usage stats
        usage = safety_manager.usage_tracker.get_user_stats(st.session_state.user_id)
        st.markdown("---")
        st.header("📊 Your Usage")
        st.metric("Total Requests", usage.total_requests)
        st.metric("Characters", f"{usage.total_characters:,}")
        audio_mins = usage.total_audio_seconds / 60
        st.metric("Audio Generated", f"{audio_mins:.1f} min")
    else:
        st.warning("No user session")
    
    st.markdown("---")
    st.header("⚙️ Actions")
    
    if st.button("🔄 Refresh Files"):
        st.cache_data.clear()
        st.rerun()
    
    if st.button("🗑️ Clear Temp Files"):
        temp_dir = Path("temp")
        if temp_dir.exists():
            import shutil
            for item in temp_dir.iterdir():
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            st.success("Temp files cleared!")

# Header
st.markdown("""
<div class="download-header">
    <h1>📥 Downloads & History</h1>
    <p>View, play, and download your generated audio files</p>
</div>
""", unsafe_allow_html=True)

# Get files
files = get_output_files()

# Statistics
total_size = sum(f['size_mb'] for f in files)
tts_count = sum(1 for f in files if f['type'] == 'tts')
cloned_count = sum(1 for f in files if f['type'] == 'cloned')

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{len(files)}</div>
        <div class="stat-label">Total Files</div>
    </div>
    """, unsafe_allow_html=True)
with col2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{tts_count}</div>
        <div class="stat-label">TTS Files</div>
    </div>
    """, unsafe_allow_html=True)
with col3:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{cloned_count}</div>
        <div class="stat-label">Cloned Voices</div>
    </div>
    """, unsafe_allow_html=True)
with col4:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-value">{total_size:.1f}</div>
        <div class="stat-label">Total Size (MB)</div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("---")

# Filters
st.markdown('<div class="filter-bar">', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns([2, 2, 2, 1])

with col1:
    search = st.text_input("🔍 Search files", placeholder="Enter filename...")

with col2:
    file_type = st.selectbox("📁 Type", ["All", "TTS", "Cloned Voice"])

with col3:
    sort_by = st.selectbox("📊 Sort by", ["Newest", "Oldest", "Largest", "Smallest"])

with col4:
    view_mode = st.radio("View", ["Grid", "List"], horizontal=True, label_visibility="collapsed")

st.markdown('</div>', unsafe_allow_html=True)

# Filter files
filtered_files = files

if search:
    filtered_files = [f for f in filtered_files if search.lower() in f['name'].lower()]

if file_type == "TTS":
    filtered_files = [f for f in filtered_files if f['type'] == 'tts']
elif file_type == "Cloned Voice":
    filtered_files = [f for f in filtered_files if f['type'] == 'cloned']

# Sort files
if sort_by == "Oldest":
    filtered_files.sort(key=lambda x: x['created'])
elif sort_by == "Largest":
    filtered_files.sort(key=lambda x: x['size_mb'], reverse=True)
elif sort_by == "Smallest":
    filtered_files.sort(key=lambda x: x['size_mb'])

# Display files
if not filtered_files:
    st.markdown("""
    <div class="empty-state">
        <h3>📭 No files found</h3>
        <p>Generate some audio using the TTS or Voice Cloning pages!</p>
    </div>
    """, unsafe_allow_html=True)
else:
    if view_mode == "Grid":
        # Grid view
        cols = st.columns(3)
        for i, file in enumerate(filtered_files):
            with cols[i % 3]:
                type_icon = "🧬" if file['type'] == 'cloned' else "🎙️"
                
                st.markdown(f"""
                <div class="file-card">
                    <div class="file-name">{type_icon} {file['name'][:30]}{'...' if len(file['name']) > 30 else ''}</div>
                    <div class="file-meta">
                        {format_file_size(file['size_mb'])} • {format_time_ago(file['created'])}
                    </div>
                </div>
                """, unsafe_allow_html=True)
                
                # Audio player
                try:
                    st.audio(file['path'])
                except:
                    st.warning("Cannot play file")
                
                # Download button
                try:
                    with open(file['path'], 'rb') as f:
                        st.download_button(
                            "📥 Download",
                            f.read(),
                            file_name=file['name'],
                            mime="audio/wav" if file['name'].endswith('.wav') else "audio/mpeg",
                            key=f"dl_{i}_{file['name']}",
                            use_container_width=True
                        )
                except Exception as e:
                    st.error(f"Error: {str(e)[:50]}")
    else:
        # List view
        for i, file in enumerate(filtered_files):
            type_icon = "🧬" if file['type'] == 'cloned' else "🎙️"
            
            with st.expander(f"{type_icon} {file['name']} • {format_file_size(file['size_mb'])} • {format_time_ago(file['created'])}"):
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.audio(file['path'])
                    st.caption(f"**Path:** {file['path']}")
                    st.caption(f"**Created:** {file['created'].strftime('%Y-%m-%d %H:%M:%S')}")
                
                with col2:
                    try:
                        with open(file['path'], 'rb') as f:
                            st.download_button(
                                "📥 Download",
                                f.read(),
                                file_name=file['name'],
                                mime="audio/wav" if file['name'].endswith('.wav') else "audio/mpeg",
                                key=f"dl_list_{i}_{file['name']}",
                                use_container_width=True
                            )
                    except:
                        pass
                    
                    if st.button("🗑️ Delete", key=f"del_{i}_{file['name']}", use_container_width=True):
                        try:
                            os.remove(file['path'])
                            st.success("File deleted!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {str(e)}")

# Usage Summary Section
st.markdown("---")
st.markdown("## 📊 Usage Summary")

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📈 Recent Activity")
    summary = safety_manager.usage_tracker.get_usage_summary(days=7)
    
    if summary['total_requests'] > 0:
        st.metric("Requests (7 days)", summary['total_requests'])
        st.metric("Characters Processed", f"{summary['total_characters']:,}")
        st.metric("Audio Generated", f"{summary['total_audio_seconds']:.1f}s")
        
        # Requests by day chart
        if summary['requests_by_day']:
            import pandas as pd
            df = pd.DataFrame([
                {'Date': k, 'Requests': v}
                for k, v in summary['requests_by_day'].items()
            ])
            st.bar_chart(df.set_index('Date'))
    else:
        st.info("No activity in the last 7 days")

with col2:
    st.markdown("### 🏆 Top Users")
    top_users = safety_manager.usage_tracker.get_top_users(5)
    
    if top_users:
        for i, user in enumerate(top_users, 1):
            medal = "🥇" if i == 1 else ("🥈" if i == 2 else ("🥉" if i == 3 else ""))
            st.markdown(f"{medal} **{user['user_id'][:20]}** - {user['total_requests']} requests")
    else:
        st.info("No users yet")

# Export section
st.markdown("---")
st.markdown("### 📤 Export Data")

col1, col2, col3 = st.columns(3)

with col1:
    if st.button("📊 Export Usage Report", use_container_width=True):
        report_path = safety_manager.usage_tracker.export_usage_report()
        st.success(f"Report exported to: {report_path}")
        
        with open(report_path, 'r') as f:
            st.download_button(
                "📥 Download Report",
                f.read(),
                file_name=f"usage_report_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )

with col2:
    if st.button("📁 Download All Files (ZIP)", use_container_width=True):
        import zipfile
        import io
        
        if files:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                for file in files:
                    try:
                        zf.write(file['path'], file['name'])
                    except:
                        pass
            
            st.download_button(
                "📥 Download ZIP",
                zip_buffer.getvalue(),
                file_name=f"voice_tts_files_{datetime.now().strftime('%Y%m%d')}.zip",
                mime="application/zip"
            )
        else:
            st.warning("No files to export")

with col3:
    if st.button("🗑️ Delete All Files", use_container_width=True):
        if st.checkbox("⚠️ Confirm deletion"):
            for file in files:
                try:
                    os.remove(file['path'])
                except:
                    pass
            st.success("All files deleted!")
            st.rerun()
