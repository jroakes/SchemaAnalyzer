import os
import streamlit as st
import pandas as pd
import logging
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional
from schema_analyzer import SchemaAnalyzer
from competitor_analyzer import CompetitorAnalyzer
from schema_validator import SchemaValidator
from utils import format_schema_data
import plotly.express as px
import time
import json

# Configure logging
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

        # Load custom CSS
        css_path = Path('assets/styles.css')
        if css_path.exists():
            with open(css_path) as f:
                st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

        # Title and Description
        st.title("Schema.org Analysis Tool")
        st.markdown("""
        Analyze your website's schema markup implementation and compare it against competitors.
        Get recommendations for improvements and ensure compliance with schema.org standards.
        """)

        # Input form with improved layout
        st.markdown('<div class="url-input-form">', unsafe_allow_html=True)
        with st.form("url_input"):
            st.markdown("### Enter URL and Keyword")
            
            url = st.text_input(
                "Website URL",
                placeholder="https://example.com",
                help="Enter the full URL including https://"
            )
            
            keyword = st.text_input(
                "Target Keyword",
                placeholder="digital marketing",
                help="Enter the main keyword for competitor analysis"
            )
            
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                submitted = st.form_submit_button("🔍 Analyze Schema")
        st.markdown('</div>', unsafe_allow_html=True)

        if submitted:
            if not url:
                st.error("Please enter a valid URL")
                return
            if not keyword:
                st.error("Please enter a target keyword")
                return

            # Initialize progress components
            progress_bar = st.progress(0)
            status_text = st.empty()
            error_container = st.empty()

            try:
                # Initialize analyzers
                schema_analyzer = SchemaAnalyzer(url)
                competitor_analyzer = CompetitorAnalyzer(keyword)
                
                # Load schema types
                schema_types_df = pd.read_csv('supported_schema.csv')
                schema_validator = SchemaValidator(schema_types_df)

                schema_data = None
                competitor_data = None
                validation_results = None

                try:
                    # Extract schema data
                    status_text.text("🔍 Analyzing schema markup...")
                    schema_data = schema_analyzer.extract_schema()
                    progress_bar.progress(0.25)
                    
                    # Analyze competitors
                    status_text.text("🔄 Analyzing competitors...")
                    try:
                        competitor_data = competitor_analyzer.analyze_competitors(
                            progress_callback=lambda p: progress_bar.progress(0.25 + p * 0.25)
                        )
                    except Exception as e:
                        logger.error(f"Error analyzing competitors: {str(e)}")
                        error_container.error(f"Error analyzing competitors: {str(e)}")
                        competitor_data = {}

                    # Validate schema
                    status_text.text("✅ Validating schema...")
                    try:
                        if schema_data:
                            validation_results = schema_validator.validate_schema(schema_data)
                            
                            # Show validation errors if any
                            if validation_results.get('errors'):
                                error_details = []
                                for error in validation_results['errors']:
                                    if isinstance(error, dict):
                                        error_details.append(f"{error.get('type', 'Unknown')}: {error.get('message', 'Unknown error')}")
                                    else:
                                        error_details.append(str(error))
                                error_container.error("Validation Errors:\n" + "\n".join(error_details))
                            
                            progress_bar.progress(0.75)
                        else:
                            validation_results = {
                                'good_schemas': [],
                                'needs_improvement': [],
                                'suggested_additions': [],
                                'warnings': ['No schema data found on the page'],
                                'errors': []
                            }
                            st.warning("No schema markup found on the page")
                        progress_bar.progress(0.75)
                    except Exception as e:
                        logger.error(f"Error validating schema: {str(e)}")
                        error_container.error(f"Error validating schema: {str(e)}")
                        validation_results = None

                    # Display results
                    progress_bar.progress(1.0)
                    status_text.text("✨ Analysis complete!")
                    time.sleep(1)
                    progress_bar.empty()
                    status_text.empty()

                    if validation_results:
                        # Display results in tabs
                        analysis_tab, competitor_tab, recommendations_tab = st.tabs([
                            "🔍 Schema Analysis",
                            "📊 Competitor Insights",
                            "💡 Recommendations"
                        ])

                        with analysis_tab:
                            # Summary metrics
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric(
                                    "Good Implementations",
                                    len(validation_results.get('good_schemas', [])),
                                    help="Number of well-implemented schemas"
                                )
                            with col2:
                                st.metric(
                                    "Needs Improvement",
                                    len(validation_results.get('needs_improvement', [])),
                                    help="Number of schemas requiring updates"
                                )
                            with col3:
                                st.metric(
                                    "Suggested Additions",
                                    len(validation_results.get('suggested_additions', [])),
                                    help="Number of recommended new schemas"
                                )

                            # Display schema details
                            if validation_results.get('good_schemas'):
                                st.subheader("✅ Good Implementations")
                                for schema in validation_results['good_schemas']:
                                    with st.expander(f"Schema: {schema.get('type', 'Unknown')}"):
                                        st.json(schema)

                            if validation_results.get('needs_improvement'):
                                st.subheader("🔧 Needs Improvement")
                                for schema in validation_results['needs_improvement']:
                                    with st.expander(f"Schema: {schema.get('type', 'Unknown')}"):
                                        st.json(schema)

                        with competitor_tab:
                            if competitor_data:
                                st.subheader("Competitor Schema Usage")
                                # Create DataFrame for visualization
                                schema_counts = {}
                                for schemas in competitor_data.values():
                                    for schema_type in schemas.keys():
                                        schema_counts[schema_type] = schema_counts.get(schema_type, 0) + 1

                                if schema_counts:
                                    df = pd.DataFrame(
                                        {'Schema Type': list(schema_counts.keys()),
                                         'Count': list(schema_counts.values())}
                                    )
                                    fig = px.bar(
                                        df,
                                        x='Schema Type',
                                        y='Count',
                                        title='Schema Types Used by Competitors'
                                    )
                                    st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("No competitor data available")

                        with recommendations_tab:
                            st.subheader("💡 Recommendations")
                            if validation_results.get('suggested_additions'):
                                for suggestion in validation_results['suggested_additions']:
                                    with st.expander(f"Add {suggestion.get('type', 'Unknown')} Schema"):
                                        st.markdown(suggestion.get('recommendations', ''))

                except Exception as e:
                    logger.error(f"Error in analysis process: {str(e)}")
                    st.error(f"An error occurred during analysis: {str(e)}")

            except Exception as e:
                logger.error(f"Error initializing analyzers: {str(e)}")
                st.error(f"Failed to initialize analysis: {str(e)}")

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error(f"Application error: {str(e)}")

if __name__ == "__main__":
    main()