import os
import streamlit as st
import pandas as pd
import logging
import sys

# Configure logging to show all levels
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# Page config
try:
    st.set_page_config(
        page_title="Schema Analysis Tool",
        page_icon="🔍",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    logger.info("Page config set successfully")
except Exception as e:
    logger.error(f"Error setting page config: {str(e)}")
    st.error(f"Error setting page config: {str(e)}")

# Load schema types
@st.cache_data
def load_schema_types():
    try:
        logger.info("Attempting to load schema types from CSV...")
        df = pd.read_csv('supported_schema.csv')
        logger.info(f"Successfully loaded {len(df)} schema types")
        return df
    except Exception as e:
        logger.error(f"Error loading schema types: {str(e)}")
        st.error(f"Error loading schema types: {str(e)}")
        return pd.DataFrame({
            'Name': [],
            'Description': [],
            'Schema URL': [],
            'Google Doc URL': []
        })

# Main application UI
try:
    st.title("Schema Markup Analysis Tool")
    st.markdown("""
    This tool analyzes schema markup implementation and provides recommendations based on:
    - Current implementation analysis
    - Competitor comparisons
    - Schema.org specifications
    - Google's rich results guidelines
    """)
    logger.info("Main UI elements rendered successfully")

    # Load schema types
    schema_types_df = load_schema_types()
    
    # Input form
    with st.form("url_input"):
        col1, col2 = st.columns(2)
        with col1:
            url = st.text_input(
                "Enter URL to analyze",
                placeholder="https://example.com",
                help="Enter the full URL including https://"
            )
        with col2:
            keyword = st.text_input(
                "Enter target keyword",
                placeholder="digital marketing",
                help="Enter the main keyword for competitor analysis"
            )
        
        submitted = st.form_submit_button("Analyze Schema")

    if submitted:
        if not url:
            st.error("Please enter a URL to analyze")
        elif not url.startswith(('http://', 'https://')):
            st.error("Please enter a valid URL starting with http:// or https://")
        elif not keyword:
            st.error("Please enter a keyword for competitor analysis")
        else:
            st.info("Analysis will start here...")
    else:
        st.info("Enter a URL and keyword to begin analysis")

except Exception as e:
    logger.error(f"Critical error in main application: {str(e)}")
    st.error(f"An error occurred: {str(e)}")