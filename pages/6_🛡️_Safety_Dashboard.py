"""
Safety Dashboard Page
Monitor content filtering, rate limiting, and usage statistics
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.safety import (
    SafetyManager, ContentFilter, RateLimiter, UsageTracker,
    RateLimitTier, FilterCategory
)

st.set_page_config(
    page_title="Safety Dashboard - Voice TTS",
    page_icon="🛡️",
    layout="wide"
)

# Custom CSS
st.markdown("""
<style>
    .safety-header {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        border-radius: 20px;
        padding: 40px;
        text-align: center;
        margin-bottom: 30px;
    }
    .safety-header h1 {
        color: white;
        font-size: 2.5em;
        margin: 0;
    }
    .metric-card {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
        border: 1px solid rgba(102, 126, 234, 0.3);
        border-radius: 15px;
        padding: 25px;
        text-align: center;
    }
    .metric-value {
        font-size: 2.5em;
        font-weight: 700;
        color: #667eea;
    }
    .metric-label {
        color: #888;
        font-size: 0.9em;
        margin-top: 5px;
    }
    .status-good { color: #4CAF50; }
    .status-warning { color: #FF9800; }
    .status-bad { color: #f44336; }
    .category-bar {
        display: flex;
        align-items: center;
        margin: 10px 0;
        gap: 15px;
    }
    .category-name {
        width: 150px;
        color: #aaa;
    }
    .category-count {
        width: 50px;
        text-align: right;
        font-weight: 600;
    }
    .bar-container {
        flex-grow: 1;
        height: 8px;
        background: rgba(255,255,255,0.1);
        border-radius: 4px;
        overflow: hidden;
    }
    .bar-fill {
        height: 100%;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        border-radius: 4px;
    }
    .user-card {
        background: rgba(102, 126, 234, 0.1);
        border-radius: 10px;
        padding: 15px;
        margin: 10px 0;
    }
    .tier-badge {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 0.8em;
        font-weight: 600;
    }
    .tier-free { background: #607d8b; color: white; }
    .tier-basic { background: #2196f3; color: white; }
    .tier-premium { background: #9c27b0; color: white; }
    .tier-enterprise { background: #ff9800; color: white; }
    .filter-log {
        background: rgba(0,0,0,0.3);
        border-radius: 8px;
        padding: 10px 15px;
        margin: 5px 0;
        font-family: monospace;
        font-size: 0.85em;
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

@st.cache_resource
def get_content_filter():
    return ContentFilter(sensitivity="medium")

@st.cache_resource
def get_rate_limiter():
    return RateLimiter(storage_dir="data/rate_limits")

safety_manager = get_safety_manager()
content_filter = get_content_filter()
rate_limiter = get_rate_limiter()

# Sidebar - Admin controls
with st.sidebar:
    st.header("🔐 Admin Controls")
    
    admin_mode = st.checkbox("Enable Admin Mode")
    
    if admin_mode:
        st.success("Admin mode active")
        
        st.markdown("---")
        st.subheader("👤 User Management")
        
        # Set user tier
        user_to_modify = st.text_input("User ID")
        new_tier = st.selectbox(
            "New Tier",
            options=[t.value for t in RateLimitTier],
            format_func=lambda x: x.upper()
        )
        
        if st.button("Update Tier"):
            if user_to_modify:
                rate_limiter.set_user_tier(user_to_modify, RateLimitTier(new_tier))
                st.success(f"Updated {user_to_modify} to {new_tier.upper()}")
        
        st.markdown("---")
        st.subheader("🛡️ Filter Settings")
        
        sensitivity = st.select_slider(
            "Sensitivity",
            options=["low", "medium", "high"],
            value="medium"
        )
    
    st.markdown("---")
    st.subheader("📊 Quick Stats")
    
    filter_stats = content_filter.get_statistics()
    st.metric("Texts Checked", filter_stats['total_checked'])
    st.metric("Blocked", filter_stats['total_blocked'])
    st.metric("Sanitized", filter_stats['total_sanitized'])

# Header
st.markdown("""
<div class="safety-header">
    <h1>🛡️ Safety Dashboard</h1>
    <p>Monitor content filtering, rate limiting, and usage metrics</p>
</div>
""", unsafe_allow_html=True)

# Main metrics
col1, col2, col3, col4 = st.columns(4)

filter_stats = content_filter.get_statistics()
usage_summary = safety_manager.usage_tracker.get_usage_summary(days=7)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{filter_stats['total_checked']}</div>
        <div class="metric-label">Texts Analyzed</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    block_rate = (filter_stats['total_blocked'] / max(filter_stats['total_checked'], 1)) * 100
    status_class = "status-good" if block_rate < 5 else ("status-warning" if block_rate < 15 else "status-bad")
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value {status_class}">{block_rate:.1f}%</div>
        <div class="metric-label">Block Rate</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{usage_summary['total_requests']}</div>
        <div class="metric-label">Requests (7 days)</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{usage_summary['unique_users']}</div>
        <div class="metric-label">Active Users</div>
    </div>
    """, unsafe_allow_html=True)

# Tabs for different sections
tab1, tab2, tab3, tab4 = st.tabs(["📊 Content Filter", "⏱️ Rate Limits", "📈 Usage Analytics", "🧪 Test Filter"])

with tab1:
    st.markdown("## Content Filter Statistics")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.markdown("### 🏷️ Categories Detected")
        
        categories = filter_stats['categories']
        max_count = max(categories.values()) if categories.values() else 1
        
        for cat, count in sorted(categories.items(), key=lambda x: x[1], reverse=True):
            width = (count / max(max_count, 1)) * 100
            cat_display = cat.replace('_', ' ').title()
            
            st.markdown(f"""
            <div class="category-bar">
                <span class="category-name">{cat_display}</span>
                <div class="bar-container">
                    <div class="bar-fill" style="width: {width}%"></div>
                </div>
                <span class="category-count">{count}</span>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### ⚙️ Filter Config")
        
        st.write(f"**Sensitivity:** {filter_stats['sensitivity'].upper()}")
        st.write(f"**Blocklist Size:** {filter_stats['blocklist_size']}")
        st.write(f"**Allowlist Size:** {filter_stats['allowlist_size']}")
        
        st.markdown("---")
        
        st.markdown("### 📋 Active Categories")
        for cat in FilterCategory:
            st.write(f"✅ {cat.value.replace('_', ' ').title()}")

with tab2:
    st.markdown("## Rate Limiting")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📋 Tier Configurations")
        
        for tier in RateLimitTier:
            config = rate_limiter.get_tier_config(tier)
            tier_class = f"tier-{tier.value}"
            
            st.markdown(f"""
            <div class="user-card">
                <span class="tier-badge {tier_class}">{tier.value.upper()}</span>
                <div style="margin-top: 10px;">
                    <strong>Per Minute:</strong> {config.requests_per_minute}<br>
                    <strong>Per Hour:</strong> {config.requests_per_hour}<br>
                    <strong>Per Day:</strong> {config.requests_per_day}<br>
                    <strong>Max Characters:</strong> {config.max_characters_per_request:,}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("### 👥 User Check")
        
        check_user = st.text_input("Enter User ID to check", key="rate_check_user")
        
        if check_user:
            result = rate_limiter.check_rate_limit(check_user)
            tier = rate_limiter.get_user_tier(check_user)
            
            st.markdown(f"**Tier:** `{tier.value.upper()}`")
            
            if result.allowed:
                st.success("✅ User can make requests")
            else:
                st.error(f"❌ Rate limited: {result.reason}")
            
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                st.metric("Remaining/min", result.remaining_minute)
            with col_b:
                st.metric("Remaining/hr", result.remaining_hour)
            with col_c:
                st.metric("Remaining/day", result.remaining_day)

with tab3:
    st.markdown("## Usage Analytics")
    
    # Time period selector
    period = st.selectbox("Time Period", ["7 Days", "30 Days", "90 Days"])
    days = int(period.split()[0])
    
    summary = safety_manager.usage_tracker.get_usage_summary(days=days)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Requests", summary['total_requests'])
    with col2:
        st.metric("Characters Processed", f"{summary['total_characters']:,}")
    with col3:
        audio_mins = summary['total_audio_seconds'] / 60
        st.metric("Audio Generated", f"{audio_mins:.1f} min")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### 📅 Requests by Day")
        
        if summary['requests_by_day']:
            import pandas as pd
            df = pd.DataFrame([
                {'Date': k, 'Requests': v}
                for k, v in summary['requests_by_day'].items()
            ])
            st.line_chart(df.set_index('Date'))
        else:
            st.info("No data for this period")
    
    with col2:
        st.markdown("### 📊 Requests by Type")
        
        if summary['requests_by_type']:
            import pandas as pd
            df = pd.DataFrame([
                {'Type': k, 'Count': v}
                for k, v in summary['requests_by_type'].items()
            ])
            st.bar_chart(df.set_index('Type'))
        else:
            st.info("No data for this period")
    
    st.markdown("---")
    
    st.markdown("### 🏆 Top Users")
    
    top_users = safety_manager.usage_tracker.get_top_users(10)
    
    if top_users:
        cols = st.columns(5)
        for i, user in enumerate(top_users):
            with cols[i % 5]:
                medal = "🥇" if i == 0 else ("🥈" if i == 1 else ("🥉" if i == 2 else f"#{i+1}"))
                st.markdown(f"""
                <div class="user-card" style="text-align: center;">
                    <div style="font-size: 1.5em;">{medal}</div>
                    <div style="font-weight: 600; color: #fff;">{user['user_id'][:15]}</div>
                    <div style="color: #888;">{user['total_requests']} requests</div>
                </div>
                """, unsafe_allow_html=True)
    else:
        st.info("No users yet")

with tab4:
    st.markdown("## 🧪 Test Content Filter")
    st.markdown("Try the content filter with sample text to see how it works.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        test_text = st.text_area(
            "Enter text to test",
            height=150,
            placeholder="Enter any text to test the content filter..."
        )
        
        if st.button("🔍 Analyze Text", type="primary"):
            if test_text:
                result = content_filter.filter(test_text)
                
                if result.is_safe:
                    st.success("✅ Content is safe!")
                elif result.blocked:
                    st.error(f"⛔ Content blocked!")
                else:
                    st.warning("⚠️ Content was modified")
                
                st.markdown("---")
                
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.markdown("**Original:**")
                    st.code(result.original_text[:500])
                
                with col_b:
                    st.markdown("**Filtered:**")
                    st.code(result.filtered_text[:500])
                
                if result.flags:
                    st.markdown("### 🚩 Flags Detected")
                    for flag in result.flags:
                        st.markdown(f"""
                        <div class="filter-log">
                            <strong>Type:</strong> {flag.get('type', 'unknown')}<br>
                            <strong>Severity:</strong> {flag.get('severity', 'unknown')}<br>
                            <strong>Matches:</strong> {flag.get('matches', flag.get('count', 'N/A'))}
                        </div>
                        """, unsafe_allow_html=True)
                
                # Show detailed results
                with st.expander("📋 Full Analysis"):
                    st.json(result.to_dict())
            else:
                st.warning("Please enter some text to test")
    
    with col2:
        st.markdown("### 🧪 Test Examples")
        st.caption("Click to test these examples:")
        
        examples = [
            ("Clean text", "Hello, welcome to our text-to-speech service!"),
            ("Phone number", "Call me at 555-123-4567"),
            ("Email", "Contact info@example.com"),
            ("Profanity", "This is a damn good test"),
            ("Violence hint", "I want to kill this bug in my code"),
        ]
        
        for label, text in examples:
            if st.button(f"📝 {label}", key=f"example_{label}", use_container_width=True):
                st.session_state.test_example = text
                st.rerun()

# Footer
st.markdown("---")
st.markdown("""
<div style="text-align: center; color: #666; padding: 20px;">
    <p>🛡️ Safety Dashboard • Voice TTS Studio</p>
    <p style="font-size: 0.8em;">All content filtering and rate limiting is logged for security purposes.</p>
</div>
""", unsafe_allow_html=True)
