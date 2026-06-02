"""
Activation code system — 10 lifetime codes.
Access is stored in the browser URL token (bookmark = lifetime access).
"""

import hashlib
import streamlit as st

# ── 10 unique lifetime activation codes ───────────────────────
# Keep these SECRET — share one code per person.
VALID_CODES = [
    "ALLAPP-7K3M-X9QR",   # Code 01
    "ALLAPP-2P8N-W4YZ",   # Code 02
    "ALLAPP-5T6V-B1DF",   # Code 03
    "ALLAPP-9H2L-C7KJ",   # Code 04
    "ALLAPP-4R1S-E3MN",   # Code 05
    "ALLAPP-8G5F-A6PW",   # Code 06
    "ALLAPP-3J7D-Q2VT",   # Code 07
    "ALLAPP-6B4X-H8ZL",   # Code 08
    "ALLAPP-1W9U-K5RY",   # Code 09
    "ALLAPP-0N3E-G7CS",   # Code 10
]

# Pre-compute secure token for each code (SHA-256 first 20 chars)
def _make_token(code: str) -> str:
    return hashlib.sha256(code.encode()).hexdigest()[:20]

TOKEN_TO_CODE = {_make_token(c): c for c in VALID_CODES}
CODE_TO_TOKEN = {c: _make_token(c) for c in VALID_CODES}


def is_authenticated() -> bool:
    """Check if the current browser session has a valid token in the URL."""
    token = st.query_params.get("token", "")
    return token in TOKEN_TO_CODE


def show_activation_gate():
    """Render the activation / lock screen."""
    st.markdown("""
<style>
body { background: #0a0a0a; }
.lock-box {
    max-width: 480px; margin: 80px auto 0 auto;
    background: #111; border: 2px solid #ee0a78;
    border-radius: 20px; padding: 48px 40px;
    text-align: center; box-shadow: 0 0 40px #ee0a7833;
}
</style>
""", unsafe_allow_html=True)

    st.markdown("""
<div class="lock-box">
  <div style="font-size:56px">🔐</div>
  <h1 style="color:#ee0a78;margin:12px 0 4px">ALL APP IN ONE</h1>
  <p style="color:#888;margin-bottom:28px">
    This tool is private.<br>Enter your activation code to get lifetime access.
  </p>
</div>
""", unsafe_allow_html=True)

    col = st.columns([1, 2, 1])[1]
    with col:
        code_input = st.text_input(
            "Activation Code",
            placeholder="ALLAPP-XXXX-XXXX",
            max_chars=20,
            label_visibility="collapsed",
        )
        activate_btn = st.button("🔓 Activate", use_container_width=True, type="primary")

        if activate_btn:
            code = code_input.strip().upper()
            if code in VALID_CODES:
                token = CODE_TO_TOKEN[code]
                st.query_params["token"] = token
                st.success("✅ Activated! Bookmark this page URL — it gives you lifetime access.")
                st.balloons()
                st.rerun()
            else:
                st.error("❌ Invalid code. Contact the admin to get one.")

        st.markdown(
            "<p style='color:#444;font-size:12px;margin-top:20px'>"
            "Once activated, bookmark the URL — your access is permanent.</p>",
            unsafe_allow_html=True,
        )
