import os
import streamlit as st
import pandas as pd
import logging
import sys
from pathlib import Path
from schema_analyzer import SchemaAnalyzer
from competitor_analyzer import CompetitorAnalyzer
from schema_validator import SchemaValidator
from utils import format_schema_data
import plotly.graph_objects as go
import plotly.express as px

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def display_schema_data(schema_data):
    """Display extracted schema data in a collapsible section"""
    with st.expander("📊 Extracted Schema Data", expanded=True):
        for schema_type, data in schema_data.items():
            st.subheader(f"Type: {schema_type}")
            st.json(data)

def display_validation_results(validation_results):
    """Display validation results with color coding"""
    with st.expander("✅ Validation Results", expanded=True):
        # Valid Types
        if validation_results['valid_types']:
            st.success("Valid Schema Types Found:")
            for type_name in validation_results['valid_types']:
                st.write(f"- {type_name}")

        # Invalid Types
        if validation_results['invalid_types']:
            st.error("Invalid Schema Types Found:")
            for type_name in validation_results['invalid_types']:
                st.write(f"- {type_name}")

        # Warnings
        if validation_results['warnings']:
            st.warning("Warnings:")
            for warning in validation_results['warnings']:
                st.write(f"- {warning}")

        # Errors
        if validation_results['errors']:
            st.error("Errors:")
            for error in validation_results['errors']:
                st.write(f"- {error}")

def display_competitor_insights(competitor_data):
    """Display competitor insights using charts"""
    with st.expander("🔍 Competitor Insights", expanded=True):
        if not competitor_data:
            st.warning("No competitor data available")
            return

        # Create usage statistics visualization
        schema_types = []
        usage_counts = []
        for url, schemas in competitor_data.items():
            for schema_type in schemas.keys():
                schema_types.append(schema_type)
                usage_counts.append(1)

        if schema_types:
            df = pd.DataFrame({
                'Schema Type': schema_types,
                'Count': usage_counts
            }).groupby('Schema Type').sum().reset_index()

            fig = px.bar(
                df,
                x='Schema Type',
                y='Count',
                title='Schema Usage Across Competitors'
            )
            st.plotly_chart(fig, use_container_width=True)

def display_gpt_recommendations(validation_results):
    """Display GPT-powered recommendations"""
    with st.expander("💡 GPT Recommendations", expanded=True):
        for schema_type, analysis in validation_results['gpt_analysis'].items():
            st.subheader(f"Analysis for {schema_type}")
            
            # Documentation Analysis
            st.markdown("**Documentation Analysis:**")
            st.write(analysis.get('documentation_analysis', 'No analysis available'))
            
            # Competitor Insights
            st.markdown("**Competitor Insights:**")
            st.write(analysis.get('competitor_insights', 'No insights available'))
            
            # Recommendations
            st.markdown("**Recommendations:**")
            st.write(analysis.get('recommendations', 'No recommendations available'))

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
                # Initialize analyzers
                schema_analyzer = SchemaAnalyzer(url)
                competitor_analyzer = CompetitorAnalyzer(keyword)
                schema_validator = SchemaValidator(schema_types_df)

                # Create progress bar
                progress_bar = st.progress(0)
                status_text = st.empty()

                try:
                    # Extract schema from URL
                    status_text.text("Extracting schema from URL...")
                    schema_data = schema_analyzer.extract_schema()
                    progress_bar.progress(0.25)

                    # Get competitor data
                    status_text.text("Analyzing competitors...")
                    competitor_data = competitor_analyzer.analyze_competitors(
                        progress_callback=lambda p: progress_bar.progress(0.25 + p * 0.25)
                    )
                    progress_bar.progress(0.50)

                    # Validate schema
                    status_text.text("Validating schema...")
                    validation_results = schema_validator.validate_schema(schema_data)
                    progress_bar.progress(0.75)

                    # Analysis complete
                    progress_bar.progress(1.0)
                    status_text.text("Analysis complete!")

                    # Display results
                    st.markdown("## Analysis Results")

                    # Display extracted schema
                    display_schema_data(schema_data)

                    # Display validation results
                    display_validation_results(validation_results)

                    # Display competitor insights
                    display_competitor_insights(competitor_data)

                    # Display GPT recommendations
                    display_gpt_recommendations(validation_results)

                except Exception as e:
                    logger.error(f"Error during analysis: {str(e)}")
                    st.error(f"An error occurred during analysis: {str(e)}")
                    progress_bar.empty()
                    status_text.empty()

        else:
            st.info("Enter a URL and keyword to begin analysis")

    except Exception as e:
        logger.error(f"Critical error in main application: {str(e)}")
        st.error(f"An error occurred while running the application: {str(e)}")

if __name__ == "__main__":
    main()
