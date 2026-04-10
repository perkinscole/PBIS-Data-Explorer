import streamlit as st
import urllib.parse
from utils.theme import apply_theme

apply_theme()

st.title("Feedback & Support")
st.markdown(
    "Found a bug or have an idea for a new feature? Let us know! "
    "Fill out the form below and it will open an email to the RAMS CARE Data Viewer team."
)

CONTACT_EMAIL = "cole.perkins@gmail.com"

st.markdown("---")

# Feedback type
feedback_type = st.radio(
    "What kind of feedback?",
    ["Bug Report", "Feature Request", "General Feedback"],
    horizontal=True,
)

# Form fields
if feedback_type == "Bug Report":
    st.markdown("### Report a Bug")
    st.markdown("Please describe what went wrong so we can fix it.")
    page = st.selectbox(
        "Which page were you on?",
        ["Upload", "Dashboard", "Trends", "Insights", "Survey Development", "Other"],
    )
    summary = st.text_input("Brief summary of the issue")
    details = st.text_area(
        "What happened? (What did you expect vs. what actually happened?)",
        height=150,
        placeholder="Example: I uploaded a staff survey and clicked on Dashboard, but the charts didn't show any data...",
    )
    steps = st.text_area(
        "Steps to reproduce (optional)",
        height=100,
        placeholder="1. Go to Upload page\n2. Upload file X\n3. Click Dashboard\n4. See error",
    )

    subject = f"[Bug Report] {summary}" if summary else "[Bug Report] RAMS CARE Data Viewer"
    body_parts = [
        f"BUG REPORT",
        f"Page: {page}",
        f"Summary: {summary}",
        f"",
        f"Details:",
        f"{details}",
    ]
    if steps.strip():
        body_parts.extend([f"", f"Steps to reproduce:", f"{steps}"])

elif feedback_type == "Feature Request":
    st.markdown("### Request a Feature")
    st.markdown("What would make this tool more useful for you?")
    summary = st.text_input("Brief summary of the feature")
    details = st.text_area(
        "Describe what you'd like to see",
        height=150,
        placeholder="Example: It would be helpful to export the dashboard charts as a PDF so I can include them in our PBIS report...",
    )
    priority = st.selectbox(
        "How important is this to you?",
        ["Nice to have", "Would use it regularly", "Really need this"],
    )

    subject = f"[Feature Request] {summary}" if summary else "[Feature Request] RAMS CARE Data Viewer"
    body_parts = [
        f"FEATURE REQUEST",
        f"Summary: {summary}",
        f"Priority: {priority}",
        f"",
        f"Description:",
        f"{details}",
    ]

else:
    st.markdown("### General Feedback")
    st.markdown("Any thoughts, questions, or suggestions are welcome!")
    summary = st.text_input("Subject")
    details = st.text_area(
        "Your feedback",
        height=150,
    )

    subject = f"[Feedback] {summary}" if summary else "[Feedback] RAMS CARE Data Viewer"
    body_parts = [
        f"GENERAL FEEDBACK",
        f"",
        f"{details}",
    ]

st.markdown("---")

# Build mailto link
body = "\n".join(body_parts)
mailto_url = (
    f"mailto:{CONTACT_EMAIL}"
    f"?subject={urllib.parse.quote(subject)}"
    f"&body={urllib.parse.quote(body)}"
)

# Send button
if summary or details:
    st.markdown(
        f'<a href="{mailto_url}" target="_blank" style="'
        f'display: inline-block; padding: 12px 28px; '
        f'background-color: #8b1a1a; color: white !important; '
        f'text-decoration: none; border-radius: 6px; font-size: 16px; '
        f'font-weight: bold;">'
        f'Open Email to Send {feedback_type}</a>',
        unsafe_allow_html=True,
    )
    st.caption("This will open your email app with the form details pre-filled. Just hit Send!")
else:
    st.info("Fill out the form above, then a Send button will appear here.")

st.markdown("---")
st.markdown(
    "**Alternatively**, you can email us directly at "
    f"[{CONTACT_EMAIL}](mailto:{CONTACT_EMAIL})"
)
