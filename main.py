import os
import streamlit as st
import pandas as pd
import logging
import sys
from pathlib import Path

# Configure logging to show all levels
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def main():
    try:
        # Page config
        st.set_page_config(
            page_title="Schema Analysis Tool",
            page_icon="🔍",
            layout="wide",
            initial_sidebar_state="expanded"
        )
        logger.info("Page config set successfully")

        # Load custom CSS if it exists
        css_path = Path('assets/styles.css')
        if css_path.exists():
            try:
                with open(css_path) as f:
                    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
                logger.info("Custom CSS loaded successfully")
            except Exception as e:
                logger.warning(f"Error loading custom CSS: {str(e)}")
                st.warning("Custom styles could not be loaded")
        else:
            logger.warning("CSS file not found at assets/styles.css")

        # Load schema types
        try:
            logger.info("Loading schema types from CSV...")
            schema_types_df = pd.read_csv('supported_schema.csv')
            logger.info(f"Successfully loaded {len(schema_types_df)} schema types")
        except Exception as e:
            logger.error(f"Error loading schema types: {str(e)}")
            st.error("Error loading schema types. Using empty DataFrame.")
            schema_types_df = pd.DataFrame({
                'Name': [],
                'Description': [],
                'Schema URL': [],
                'Google Doc URL': []
            })

        # Main UI
        st.title("Schema Markup Analysis Tool")
        st.markdown("""
        This tool analyzes schema markup implementation and provides recommendations based on:
        - Current implementation analysis
        - Competitor comparisons
        - Schema.org specifications
        - Google's rich results guidelines
        """)

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
                # Analysis logic will be implemented in the next iteration
        else:
            st.info("Enter a URL and keyword to begin analysis")

    except Exception as e:
        logger.error(f"Critical error in main application: {str(e)}")
        st.error(f"An error occurred while running the application: {str(e)}")

if __name__ == "__main__":
    main()
