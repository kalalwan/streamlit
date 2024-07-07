import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore
from reportlab.pdfgen import canvas
import io
import json
from datetime import datetime

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
import textwrap

# Initialize Firebase (you'll need to replace this with your own Firebase credentials)
if not firebase_admin._apps:
    cred = credentials.Certificate("/Users/kamalalalwan/Desktop/streamlit/streamlit/first_app/config.json")
    firebase_admin.initialize_app(cred)

db = firestore.client()

def main():
    st.set_page_config(page_title="BEAR's North Star")

    if 'page' not in st.session_state:
        st.session_state.page = 'home'

    if st.session_state.page == 'home':
        home_page()
    elif st.session_state.page == 'behavioural_problem':
        behavioural_problem_page()
    elif st.session_state.page == 'behavioural_scientist':
        behavioural_scientist_page()

def home_page():
    st.title("BEAR's North Star")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("I have a behavioural problem"):
            st.session_state.page = 'behavioural_problem'
            st.experimental_rerun()
    
    with col2:
        if st.button("I am a behavioural scientist"):
            st.session_state.page = 'behavioural_scientist'
            st.experimental_rerun()

def behavioural_problem_page():
    st.title("Behavioural Problem Survey")
    
    # Placeholder questions (you can change these later)
    questions = [
        "What is your main behavioral concern?",
        "How long have you been experiencing this issue?",
        "What strategies have you tried so far?",
        "How does this behavior impact your daily life?"
    ]
    
    responses = {}
    for q in questions:
        responses[q] = st.text_input(q)
    
    if st.button("Submit Survey"):
        timestamp = datetime.now().isoformat()
        db.collection("surveys").document(timestamp).set(responses)
        st.success("Survey submitted successfully!")
    
    if st.button("Back to Home"):
        st.session_state.page = 'home'
        st.experimental_rerun()

def behavioural_scientist_page():
    st.title("Behavioural Scientist Dashboard")
    
    # Fetch all survey responses
    surveys = db.collection("surveys").get()
    
    # Filter by keyword
    keyword = st.text_input("Filter by keyword:")
    
    for survey in surveys:
        data = survey.to_dict()
        if keyword.lower() in json.dumps(data).lower():
            st.write(data)
            if st.button(f"Download Index Card for {survey.id}"):
                pdf = create_index_card_pdf(data)
                st.download_button(
                    label="Download PDF",
                    data=pdf,
                    file_name=f"survey_{survey.id}.pdf",
                    mime="application/pdf"
                )
    
    if st.button("Back to Home"):
        st.session_state.page = 'home'
        st.experimental_rerun()

def create_index_card_pdf(data):
    buffer = io.BytesIO()
    # Use a custom size approximating an index card (3x5 inches)
    pagesize = (3*inch, 5*inch)
    c = canvas.Canvas(buffer, pagesize=pagesize)
    width, height = pagesize
    
    c.setFont("Helvetica", 8)  # Smaller font size to fit more content
    y = height - 10
    
    for question, answer in data.items():
        # Wrap text to fit within the card width
        wrapped_q = textwrap.fill(f"Q: {question}", width=35)
        wrapped_a = textwrap.fill(f"A: {answer}", width=35)
        
        for line in wrapped_q.split('\n'):
            c.drawString(10, y, line)
            y -= 10
        y -= 5
        
        for line in wrapped_a.split('\n'):
            c.drawString(15, y, line)
            y -= 10
        y -= 10
        
        if y < 20:  # Check if we need a new page
            c.showPage()
            c.setFont("Helvetica", 8)
            y = height - 10
    
    c.showPage()
    c.save()
    buffer.seek(0)
    return buffer

if __name__ == "__main__":
    main()