import streamlit as st
import sqlite3
import pandas as pd
from reportlab.lib.pagesizes import A6
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, PageBreak
from reportlab.lib import colors
import io

# Initialize SQLite database
conn = sqlite3.connect('survey_responses.db')
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS responses
             (id INTEGER PRIMARY KEY AUTOINCREMENT,
              question1 TEXT,
              question2 TEXT,
              question3 TEXT)''')
conn.commit()

def main():
    st.set_page_config(page_title="BEAR's North Star", page_icon="🐻", layout="wide")
    
    if 'page' not in st.session_state:
        st.session_state.page = 'home'

    if st.session_state.page == 'home':
        show_home()
    elif st.session_state.page == 'problem':
        show_problem_survey()
    elif st.session_state.page == 'scientist':
        show_scientist_dashboard()

def show_home():
    st.title("BEAR's North Star")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("I have a behavioural problem"):
            st.session_state.page = 'problem'
            st.experimental_rerun()
    
    with col2:
        if st.button("I am a behavioural scientist"):
            st.session_state.page = 'scientist'
            st.experimental_rerun()

def show_problem_survey():
    st.title("Behavioural Problem Survey")
    
    with st.form("survey_form"):
        q1 = st.text_input("Question 1: What is your main behavioural concern?")
        q2 = st.text_input("Question 2: How long have you been experiencing this issue?")
        q3 = st.text_area("Question 3: Describe a specific situation where this behavior occurs.")
        
        submitted = st.form_submit_button("Submit Survey")
        
        if submitted:
            c.execute("INSERT INTO responses (question1, question2, question3) VALUES (?, ?, ?)",
                      (q1, q2, q3))
            conn.commit()
            st.success("Survey submitted successfully!")
    
    if st.button("Back to Home"):
        st.session_state.page = 'home'
        st.experimental_rerun()

def show_scientist_dashboard():
    st.title("Behavioural Scientist Dashboard")
    
    # Load data
    df = pd.read_sql_query("SELECT * FROM responses", conn)
    
    # Keyword filter
    keyword = st.text_input("Filter responses by keyword:")
    if keyword:
        df = df[df.apply(lambda row: row.astype(str).str.contains(keyword, case=False).any(), axis=1)]
    
    # Display results in a table format
    st.write("Responses:")
    
    # Create a display dataframe without the ID column
    display_df = df.copy()
    display_df = display_df.drop(columns=['id'])
    display_df = display_df.reset_index(drop=True)
    display_df.index += 1  # Start index from 1 instead of 0
    
    # Rename columns for better readability
    display_df.columns = ['Main behavioural concern', 'Duration of issue', 'Specific situation']
    
    # Display the table
    st.dataframe(display_df, height=400)
    
    # Input field for response numbers
    response_numbers = st.text_input("Enter response numbers to download (comma-separated, e.g., 1,3,5):")
    
    # Download selected responses
    if st.button("Download Selected Responses"):
        if response_numbers:
            try:
                selected_indices = [int(idx.strip()) for idx in response_numbers.split(',')]
                selected_df = df.iloc[pd.Index(selected_indices) - 1]  # Adjust for 0-based indexing
                if not selected_df.empty:
                    pdf = create_index_cards_pdf(selected_df)
                    st.download_button(
                        label="Download PDF",
                        data=pdf,
                        file_name="selected_responses.pdf",
                        mime="application/pdf"
                    )
                else:
                    st.warning("No valid response numbers found. Please check your input.")
            except (ValueError, IndexError):
                st.warning("Invalid input. Please enter valid comma-separated numbers within the range of responses.")
        else:
            st.warning("No response numbers entered. Please enter at least one response number.")
    
    if st.button("Back to Home"):
        st.session_state.page = 'home'
        st.experimental_rerun()

def create_index_cards_pdf(df):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A6)
    elements = []
    
    for index, row in df.iterrows():
        data = [
            ["Question", "Response"],
            ["Q1: Main behavioural concern", row['question1']],
            ["Q2: Duration of issue", row['question2']],
            ["Q3: Specific situation", row['question3']]
        ]
        
        t = Table(data)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('TOPPADDING', (0, 1), (-1, -1), 6),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        
        elements.append(t)
        elements.append(PageBreak())
    
    doc.build(elements)
    
    buffer.seek(0)
    return buffer

if __name__ == "__main__":
    main()