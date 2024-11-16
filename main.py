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
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

def display_documentation_references(schema_types_df, schema_type):
    """Display enhanced documentation references with tooltips"""
    row = schema_types_df[schema_types_df['Name'] == schema_type]
    if not row.empty:
        st.markdown("### 📚 Documentation References")
        
        # Schema.org Reference
        schema_url = row['Schema URL'].iloc[0]
        if schema_url:
            st.markdown(f"""
            **Schema.org Reference**
            <div title="Official Schema.org specification">
                🔗 <a href="{schema_url}" target="_blank">{schema_type} Schema Definition</a>
            </div>
            """, unsafe_allow_html=True)
            
        # Google Documentation
        google_doc = row['Google Doc URL'].iloc[0]
        if pd.notna(google_doc):
            st.markdown(f"""
            **Google Search Documentation**
            <div title="Google's implementation guidelines and rich result information">
                📱 <a href="{google_doc}" target="_blank">Rich Results Guide</a>
            </div>
            """, unsafe_allow_html=True)
            
        # Description
        description = row['Description'].iloc[0]
        if description:
            st.info(f"ℹ️ {description}")

def display_recommendations_with_tooltips(recommendations):
    """Display schema recommendations with informative tooltips"""
    if not recommendations:
        st.warning("No recommendations available")
        return
        
    st.markdown("### 💡 Implementation Recommendations")
    
    # Required Properties
    with st.expander("Required Properties", expanded=True):
        st.markdown("""
        <div title="These properties are mandatory for valid implementation">
            Properties that must be included for valid schema markup
        </div>
        """, unsafe_allow_html=True)
        st.markdown(recommendations.get('required_properties', 'No required properties specified'))
        
    # Recommended Properties
    with st.expander("Recommended Properties", expanded=True):
        st.markdown("""
        <div title="These properties enhance the schema implementation">
            Optional but valuable properties for better schema coverage
        </div>
        """, unsafe_allow_html=True)
        st.markdown(recommendations.get('recommended_properties', 'No recommended properties specified'))
        
    # Rich Results Properties
    with st.expander("Rich Results Properties", expanded=True):
        st.markdown("""
        <div title="Properties needed for Google rich results">
            Properties required for enhanced search results display
        </div>
        """, unsafe_allow_html=True)
        st.markdown(recommendations.get('rich_results_properties', 'No rich results properties specified'))

def display_schema_analysis_results(schema_data, validation_results, competitor_data, schema_types_df):
    """Display comprehensive schema analysis results with enhanced error handling"""
    try:
        st.markdown("## Analysis Results")
        
        # Schema Data Display
        if schema_data:
            with st.expander("📊 Extracted Schema Data", expanded=True):
                for schema_type, data in schema_data.items():
                    st.subheader(f"Type: {schema_type}")
                    
                    # Display documentation references
                    display_documentation_references(schema_types_df, schema_type)
                    
                    # Display schema data
                    st.json(data)
                    
                    # Display recommendations if available
                    if validation_results and 'property_recommendations' in validation_results:
                        recommendations = validation_results['property_recommendations'].get(schema_type, {})
                        if recommendations:
                            display_recommendations_with_tooltips(recommendations)
        else:
            st.warning("No schema data was extracted")
            
        # Validation Results
        if validation_results:
            with st.expander("✅ Validation Results", expanded=True):
                col1, col2 = st.columns(2)
                
                with col1:
                    if validation_results['valid_types']:
                        st.success("Valid Schema Types:")
                        for type_name in validation_results['valid_types']:
                            st.markdown(f"✓ {type_name}")
                            
                with col2:
                    if validation_results['invalid_types']:
                        st.error("Invalid Schema Types:")
                        for type_name in validation_results['invalid_types']:
                            st.markdown(f"⚠️ {type_name}")
                
                # Display warnings and errors
                if validation_results['warnings']:
                    st.warning("Warnings:")
                    for warning in validation_results['warnings']:
                        st.markdown(f"⚠️ {warning}")
                        
                if validation_results['errors']:
                    st.error("Errors:")
                    for error in validation_results['errors']:
                        st.markdown(f"❌ {error}")
                        
        # Competitor Insights
        if competitor_data:
            with st.expander("🔍 Competitor Insights", expanded=True):
                try:
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
                            title='Schema Usage Across Competitors',
                            labels={'Count': 'Number of Implementations'},
                            color='Count',
                            color_continuous_scale='Viridis'
                        )
                        fig.update_layout(
                            showlegend=False,
                            hovermode='x',
                            hoverlabel=dict(bgcolor="white"),
                            margin=dict(t=50, l=0, r=0, b=0)
                        )
                        st.plotly_chart(fig, use_container_width=True)
                    else:
                        st.info("No schema usage data available from competitors")
                except Exception as e:
                    logger.error(f"Error displaying competitor insights: {str(e)}")
                    st.error("Error displaying competitor insights")
                    
    except Exception as e:
        logger.error(f"Error displaying analysis results: {str(e)}")
        st.error(f"An error occurred while displaying analysis results: {str(e)}")

# Update the main() function to use the new display functions
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

                # Create progress containers
                progress_bar = st.progress(0)
                status_text = st.empty()
                error_container = st.empty()
                
                # Initialize result containers
                schema_data = None
                competitor_data = None
                validation_results = None

                try:
                    # Extract schema from URL
                    status_text.text("🔍 Extracting schema from URL...")
                    try:
                        schema_data = schema_analyzer.extract_schema()
                        progress_bar.progress(0.25)
                    except Exception as e:
                        logger.error(f"Error extracting schema: {str(e)}")
                        error_container.error(f"Error extracting schema: {str(e)}")
                        schema_data = {}

                    # Get competitor data
                    status_text.text("🔍 Analyzing competitors...")
                    try:
                        competitor_data = competitor_analyzer.analyze_competitors(
                            progress_callback=lambda p: progress_bar.progress(0.25 + p * 0.25)
                        )
                        progress_bar.progress(0.50)
                    except Exception as e:
                        logger.error(f"Error analyzing competitors: {str(e)}")
                        error_container.error(f"Error analyzing competitors: {str(e)}")
                        competitor_data = {}

                    # Validate schema
                    status_text.text("✅ Validating schema...")
                    try:
                        if schema_data:
                            validation_results = schema_validator.validate_schema(schema_data)
                        else:
                            validation_results = {
                                'valid_types': [],
                                'invalid_types': [],
                                'warnings': ['No schema data to validate'],
                                'errors': []
                            }
                        progress_bar.progress(0.75)
                    except Exception as e:
                        logger.error(f"Error validating schema: {str(e)}")
                        error_container.error(f"Error validating schema: {str(e)}")
                        validation_results = None

                    # Analysis complete
                    progress_bar.progress(1.0)
                    status_text.text("✨ Analysis complete!")
                    time.sleep(1)  # Give user time to see completion
                    status_text.empty()

                    # Display results using new functions
                    display_schema_analysis_results(
                        schema_data,
                        validation_results,
                        competitor_data,
                        schema_types_df
                    )

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