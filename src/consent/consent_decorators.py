"""
Consent Decorators and Helpers Module
Utilities for checking consent before allowing actions in the UI
"""

import streamlit as st
from typing import Optional, List, Callable
from functools import wraps

from .consent_manager import ConsentManager, ConsentType, ConsentStatus


class ConsentChecker:
    """
    Helper class for checking user consent in Streamlit pages.
    """
    
    def __init__(self, consent_manager: ConsentManager):
        """
        Initialize the consent checker.
        
        Args:
            consent_manager: ConsentManager instance
        """
        self.consent_manager = consent_manager
    
    def has_consent(self, user_id: str, consent_type: ConsentType) -> bool:
        """
        Check if a user has granted a specific consent.
        
        Args:
            user_id: User identifier
            consent_type: Type of consent to check
            
        Returns:
            True if consent is granted and valid
        """
        return self.consent_manager.check_consent(user_id, consent_type)
    
    def has_any_consent(self, user_id: str, consent_types: List[ConsentType]) -> bool:
        """
        Check if a user has granted any of the specified consents.
        
        Args:
            user_id: User identifier
            consent_types: List of consent types to check
            
        Returns:
            True if any consent is granted
        """
        return any(self.has_consent(user_id, ct) for ct in consent_types)
    
    def has_all_consents(self, user_id: str, consent_types: List[ConsentType]) -> bool:
        """
        Check if a user has granted all specified consents.
        
        Args:
            user_id: User identifier
            consent_types: List of consent types to check
            
        Returns:
            True if all consents are granted
        """
        return all(self.has_consent(user_id, ct) for ct in consent_types)
    
    def get_missing_consents(self, user_id: str, consent_types: List[ConsentType]) -> List[ConsentType]:
        """
        Get list of missing consents from the required list.
        
        Args:
            user_id: User identifier
            consent_types: List of required consent types
            
        Returns:
            List of missing consent types
        """
        return [ct for ct in consent_types if not self.has_consent(user_id, ct)]
    
    def get_consent_status_display(self, user_id: str, consent_type: ConsentType) -> dict:
        """
        Get consent status for display in UI.
        
        Args:
            user_id: User identifier
            consent_type: Consent type to check
            
        Returns:
            Dictionary with status info for UI display
        """
        has_consent = self.has_consent(user_id, consent_type)
        template = self.consent_manager.get_consent_template(consent_type)
        
        return {
            'consent_type': consent_type.value,
            'title': template.get('title', consent_type.value.replace('_', ' ').title()),
            'has_consent': has_consent,
            'status': 'granted' if has_consent else 'missing',
            'icon': '✅' if has_consent else '❌',
            'color': '#4CAF50' if has_consent else '#f44336'
        }


def render_consent_check(
    consent_checker: ConsentChecker,
    user_id: str,
    required_consents: List[ConsentType],
    feature_name: str = "this feature"
) -> bool:
    """
    Render a consent check block in Streamlit UI.
    Shows warning if consents are missing and provides link to consent page.
    
    Args:
        consent_checker: ConsentChecker instance
        user_id: User identifier
        required_consents: List of required consent types
        feature_name: Name of the feature requiring consent
        
    Returns:
        True if all consents are granted, False otherwise
    """
    if not user_id:
        st.warning("👤 **No User Session**")
        st.info("Please set your user ID on the Consent page before using this feature.")
        
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            if st.button("📋 Go to Consent Page", use_container_width=True):
                st.switch_page("pages/2_📋_Consent.py")
        return False
    
    missing = consent_checker.get_missing_consents(user_id, required_consents)
    
    if not missing:
        return True
    
    # Show consent requirement block
    st.markdown("""
    <div style="
        background: linear-gradient(135deg, #ff9800 0%, #f44336 100%);
        border-radius: 15px;
        padding: 25px;
        margin: 20px 0;
        text-align: center;
    ">
        <h3 style="color: white; margin: 0;">⚠️ Consent Required</h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.warning(f"You need to provide consent before using **{feature_name}**.")
    
    st.markdown("### 📋 Required Consents")
    
    for consent_type in required_consents:
        status = consent_checker.get_consent_status_display(user_id, consent_type)
        
        st.markdown(f"""
        <div style="
            display: flex;
            align-items: center;
            padding: 10px 15px;
            margin: 5px 0;
            background: rgba(0,0,0,0.2);
            border-radius: 8px;
            border-left: 4px solid {status['color']};
        ">
            <span style="font-size: 1.5em; margin-right: 10px;">{status['icon']}</span>
            <span style="flex-grow: 1;">{status['title']}</span>
            <span style="color: {status['color']};">{status['status'].upper()}</span>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📋 Complete Consent Process", type="primary", use_container_width=True):
            st.switch_page("pages/2_📋_Consent.py")
    
    return False


def render_consent_banner(
    consent_checker: ConsentChecker,
    user_id: str,
    consent_type: ConsentType
) -> None:
    """
    Render a small consent status banner for a specific feature.
    
    Args:
        consent_checker: ConsentChecker instance
        user_id: User identifier
        consent_type: Consent type to display
    """
    if not user_id:
        return
    
    status = consent_checker.get_consent_status_display(user_id, consent_type)
    
    if status['has_consent']:
        st.success(f"{status['icon']} **{status['title']}**: Consent granted")
    else:
        st.warning(f"{status['icon']} **{status['title']}**: Consent required")


# Required consents for each feature
FEATURE_CONSENTS = {
    'audio_upload': [ConsentType.TERMS_OF_SERVICE, ConsentType.PRIVACY_POLICY],
    'audio_processing': [ConsentType.TERMS_OF_SERVICE, ConsentType.PRIVACY_POLICY, ConsentType.DATA_PROCESSING],
    'tts_basic': [ConsentType.TERMS_OF_SERVICE, ConsentType.PRIVACY_POLICY, ConsentType.DATA_PROCESSING],
    'voice_recording': [ConsentType.TERMS_OF_SERVICE, ConsentType.PRIVACY_POLICY, ConsentType.VOICE_RECORDING],
    'voice_cloning': [ConsentType.TERMS_OF_SERVICE, ConsentType.PRIVACY_POLICY, ConsentType.VOICE_RECORDING, ConsentType.VOICE_CLONING, ConsentType.DATA_PROCESSING]
}


def get_required_consents(feature: str) -> List[ConsentType]:
    """
    Get required consents for a feature.
    
    Args:
        feature: Feature name (audio_upload, tts_basic, voice_cloning, etc.)
        
    Returns:
        List of required consent types
    """
    return FEATURE_CONSENTS.get(feature, [ConsentType.TERMS_OF_SERVICE])
