"""
Consent Management Page
Multi-step consent workflow UI for Streamlit
"""

import streamlit as st
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.consent import (
    ConsentManager, ConsentWorkflow, ConsentLogger,
    ConsentStatus, ConsentType, WorkflowStatus,
    LogLevel, LogCategory
)

st.set_page_config(page_title="Consent - Voice TTS", page_icon="📋", layout="wide")

# Custom CSS
st.markdown("""
<style>
    .consent-card {
        background: linear-gradient(135deg, #1e1e3f 0%, #2d2d5a 100%);
        border: 1px solid rgba(102, 126, 234, 0.3);
        border-radius: 15px;
        padding: 25px;
        margin: 15px 0;
    }
    .step-indicator {
        display: flex;
        justify-content: center;
        gap: 10px;
        margin: 20px 0;
    }
    .step-dot {
        width: 12px;
        height: 12px;
        border-radius: 50%;
        background: #444;
    }
    .step-dot.active { background: #667eea; }
    .step-dot.completed { background: #4CAF50; }
    .consent-text {
        background: rgba(0,0,0,0.3);
        border-radius: 10px;
        padding: 20px;
        margin: 15px 0;
        max-height: 300px;
        overflow-y: auto;
    }
    .status-granted { color: #4CAF50; }
    .status-denied { color: #f44336; }
    .status-pending { color: #FFC107; }
</style>
""", unsafe_allow_html=True)

# Initialize components
@st.cache_resource
def get_consent_manager():
    return ConsentManager(storage_dir="data/consents")

@st.cache_resource
def get_workflow_manager():
    return ConsentWorkflow(get_consent_manager(), storage_dir="data/workflows")

@st.cache_resource
def get_logger():
    return ConsentLogger(log_dir="data/logs", enable_console=False)

consent_manager = get_consent_manager()
workflow_manager = get_workflow_manager()
logger = get_logger()

# Session state
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'active_workflow' not in st.session_state:
    st.session_state.active_workflow = None

# Header
st.title("📋 Consent Management")
st.markdown("Manage your consent preferences and authorizations.")
st.markdown("---")

# User identification
with st.sidebar:
    st.header("👤 User Session")
    
    user_id_input = st.text_input("Enter User ID", value=st.session_state.user_id or "", 
                                   placeholder="e.g., user@example.com")
    
    if st.button("Set User", use_container_width=True):
        if user_id_input:
            st.session_state.user_id = user_id_input
            st.success(f"User set: {user_id_input}")
            st.rerun()
    
    if st.session_state.user_id:
        st.success(f"Active: {st.session_state.user_id}")
        
        # Show user's existing consents
        user_consents = consent_manager.get_user_consents(st.session_state.user_id)
        if user_consents:
            st.markdown("---")
            st.subheader("Your Consents")
            for consent in user_consents:
                status_class = f"status-{consent.status.value}"
                st.markdown(f"""
                <div style="padding: 8px; border-radius: 5px; margin: 5px 0; background: rgba(0,0,0,0.2);">
                    <small>{consent.consent_type.value.replace('_', ' ').title()}</small><br>
                    <span class="{status_class}">{consent.status.value.upper()}</span>
                </div>
                """, unsafe_allow_html=True)

# Main content
if not st.session_state.user_id:
    st.warning("👈 Please enter a User ID in the sidebar to continue.")
    st.stop()

# Tabs for different views
tab1, tab2, tab3 = st.tabs(["🚀 Start Workflow", "📊 My Consents", "📜 Audit Log"])

with tab1:
    st.subheader("Available Consent Workflows")
    
    workflows = workflow_manager.get_available_workflows()
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="consent-card">
            <h3>🗣️ Basic TTS</h3>
            <p>Standard consent for text-to-speech features</p>
            <small>3 steps required</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Start Basic TTS", key="basic", use_container_width=True):
            workflow = workflow_manager.start_workflow(st.session_state.user_id, "basic_tts")
            st.session_state.active_workflow = workflow.workflow_id
            logger.log_workflow_started(workflow.workflow_id, st.session_state.user_id, "basic_tts")
            st.rerun()
    
    with col2:
        st.markdown("""
        <div class="consent-card">
            <h3>🎙️ Voice Recording</h3>
            <p>Consent for recording voice samples</p>
            <small>4 steps required</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Start Voice Recording", key="recording", use_container_width=True):
            workflow = workflow_manager.start_workflow(st.session_state.user_id, "voice_recording")
            st.session_state.active_workflow = workflow.workflow_id
            logger.log_workflow_started(workflow.workflow_id, st.session_state.user_id, "voice_recording")
            st.rerun()
    
    with col3:
        st.markdown("""
        <div class="consent-card">
            <h3>🧬 Voice Cloning</h3>
            <p>Full consent for voice cloning features</p>
            <small>6 steps (5 required)</small>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Start Voice Cloning", key="cloning", use_container_width=True):
            workflow = workflow_manager.start_workflow(st.session_state.user_id, "voice_cloning")
            st.session_state.active_workflow = workflow.workflow_id
            logger.log_workflow_started(workflow.workflow_id, st.session_state.user_id, "voice_cloning")
            st.rerun()
    
    # Active Workflow UI
    if st.session_state.active_workflow:
        workflow = workflow_manager.get_workflow(st.session_state.active_workflow)
        
        if workflow and workflow.status == WorkflowStatus.IN_PROGRESS:
            st.markdown("---")
            st.subheader(f"📝 Active Workflow: {workflow.workflow_type.replace('_', ' ').title()}")
            
            # Progress indicator
            progress = (workflow.current_step - 1) / workflow.total_steps
            st.progress(progress)
            st.caption(f"Step {workflow.current_step} of {workflow.total_steps}")
            
            # Current step content
            step_info = workflow_manager.get_step_consent_text(workflow.workflow_id, workflow.current_step)
            
            if step_info:
                st.markdown(f"### {step_info['title']}")
                st.write(step_info['description'])
                
                if not step_info['required']:
                    st.info("ℹ️ This step is optional")
                
                # Consent text
                st.markdown("#### Consent Agreement")
                st.markdown(f"""
                <div class="consent-text">
                    {step_info['consent_text'].replace(chr(10), '<br>')}
                </div>
                """, unsafe_allow_html=True)
                
                st.caption(f"Version: {step_info['version']}")
                
                # Action buttons
                col1, col2, col3 = st.columns([1, 1, 1])
                
                with col1:
                    if st.button("✅ I Agree", type="primary", use_container_width=True):
                        result = workflow_manager.process_step(
                            workflow.workflow_id,
                            workflow.current_step,
                            accepted=True,
                            ip_address="127.0.0.1"
                        )
                        
                        if result.get('workflow_completed'):
                            st.session_state.active_workflow = None
                            logger.log_workflow_completed(workflow.workflow_id, 
                                                         st.session_state.user_id, 
                                                         workflow.workflow_type)
                            st.success("✅ Workflow completed! All consents recorded.")
                        st.rerun()
                
                with col2:
                    if st.button("❌ I Decline", use_container_width=True):
                        result = workflow_manager.process_step(
                            workflow.workflow_id,
                            workflow.current_step,
                            accepted=False
                        )
                        
                        if result.get('workflow_cancelled'):
                            st.session_state.active_workflow = None
                            st.error(f"Workflow cancelled: {result.get('reason')}")
                        st.rerun()
                
                with col3:
                    if not step_info['required']:
                        if st.button("⏭️ Skip", use_container_width=True):
                            workflow_manager.skip_optional_step(workflow.workflow_id, workflow.current_step)
                            st.rerun()
        
        elif workflow and workflow.status == WorkflowStatus.COMPLETED:
            st.success("✅ This workflow is complete!")
            summary = workflow_manager.get_workflow_summary(workflow.workflow_id)
            st.json(summary)
            
            if st.button("Start New Workflow"):
                st.session_state.active_workflow = None
                st.rerun()

with tab2:
    st.subheader("Your Consent Records")
    
    user_consents = consent_manager.get_user_consents(st.session_state.user_id)
    
    if not user_consents:
        st.info("No consent records found. Complete a workflow to create consents.")
    else:
        for consent in user_consents:
            with st.expander(f"{consent.consent_type.value.replace('_', ' ').title()} - {consent.status.value.upper()}"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write(f"**Consent ID:** `{consent.consent_id[:8]}...`")
                    st.write(f"**Version:** {consent.version}")
                    st.write(f"**Status:** {consent.status.value}")
                
                with col2:
                    st.write(f"**Granted:** {consent.granted_at or 'N/A'}")
                    st.write(f"**Expires:** {consent.expires_at or 'Never'}")
                
                if consent.status == ConsentStatus.GRANTED:
                    # Verify proof
                    is_valid = consent_manager.verify_proof(consent)
                    if is_valid:
                        st.success("✅ Cryptographic proof verified")
                    else:
                        st.warning("⚠️ Unable to verify proof")
                    
                    if st.button(f"Revoke", key=f"revoke_{consent.consent_id}"):
                        consent_manager.revoke_consent(consent.consent_id, "User requested")
                        logger.log(
                            LogLevel.WARNING,
                            LogCategory.CONSENT_REVOKED,
                            f"Consent revoked by user: {consent.consent_type.value}",
                            user_id=st.session_state.user_id,
                            consent_id=consent.consent_id
                        )
                        st.rerun()

with tab3:
    st.subheader("Audit Log")
    
    logs = logger.get_recent_logs(50)
    
    if not logs:
        st.info("No log entries yet.")
    else:
        for log in reversed(logs[-20:]):
            ts = log.timestamp[:19].replace('T', ' ')
            level_color = {"info": "🔵", "warning": "🟡", "error": "🔴"}.get(log.level.value, "⚪")
            st.markdown(f"{level_color} **[{ts}]** {log.category.value}: {log.message}")

# Footer
st.markdown("---")
st.caption("📋 Voice TTS - Consent Management System")
