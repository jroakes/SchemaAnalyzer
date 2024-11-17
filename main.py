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

def format_json_schema(schema_data: Dict) -> str:
    """Format schema data as JSON string with proper indentation"""
    try:
        return json.dumps(schema_data, indent=2)
    except:
        return str(schema_data)

def get_doc_url(schema_row: pd.DataFrame, url_type: str) -> Optional[str]:
    """Safely get documentation URL from schema row"""
    try:
        if not schema_row.empty and url_type in schema_row.columns:
            url = schema_row[url_type].values[0]
            return None if pd.isna(url) else str(url)
        return None
    except Exception as e:
        logger.error(f"Error getting {url_type}: {str(e)}")
        return None

def check_environment():
    """Check if all required environment variables are set"""
    required_vars = ['VALUESERP_API_KEY', 'GOOGLE_API_KEY']
    missing_vars = [var for var in required_vars if not os.environ.get(var)]
    if missing_vars:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing_vars)}")

def initialize_app():
    """Initialize the Streamlit application with error handling"""
    try:
        # Check environment variables
        check_environment()
        
        # Configure page
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
        else:
            logger.warning("Custom CSS file not found at assets/styles.css")
            
        return True
    except Exception as e:
        logger.error(f"Failed to initialize application: {str(e)}")
        st.error(f"Application initialization failed: {str(e)}")
        return False

def display_schema_documentation_links(schema_type: str, schema_types_df: pd.DataFrame):
    """Display documentation links for a schema type"""
    try:
        schema_row = schema_types_df[schema_types_df['Name'] == schema_type]
        if not schema_row.empty:
            col1, col2 = st.columns(2)
            with col1:
                google_url = get_doc_url(schema_row, 'Google Doc URL')
                if google_url:
                    st.markdown(f"[📚 Google Developers Guide]({google_url})")
            with col2:
                schema_url = get_doc_url(schema_row, 'Schema URL')
                if schema_url:
                    st.markdown(f"[🔗 Schema.org Reference]({schema_url})")
    except Exception as e:
        logger.error(f"Error displaying documentation links: {str(e)}")

def display_schema_issues(issues: List[Dict[str, Any]]):
    """Display schema validation issues with proper formatting"""
    st.markdown("### Issues Found")
    for issue in issues:
        severity = issue.get('severity', 'info')
        icon = "🚫" if severity == "error" else "⚠️" if severity == "warning" else "ℹ️"
        message = issue.get('message', '')
        st.markdown(
            f"""<div class="issue-{severity}">
                {icon} <strong>{severity.title()}</strong>: {message}
            </div>""",
            unsafe_allow_html=True
        )
        if suggestion := issue.get('suggestion'):
            st.markdown(
                f"""<div class="suggestion">
                    💡 <em>Suggestion</em>: {suggestion}
                </div>""",
                unsafe_allow_html=True
            )

def display_schema_recommendations(recommendations: str):
    """Display schema recommendations with proper formatting"""
    st.markdown("### Recommendations")
    if '|' in recommendations and '---' in recommendations:
        # Convert markdown table to HTML
        rows = [row.strip() for row in recommendations.split('\n') if row.strip()]
        if len(rows) >= 3:  # Ensure we have header, separator, and data
            table_html = '<table class="styled-table">'
            
            # Add header
            header = [cell.strip() for cell in rows[0].split('|')[1:-1]]
            table_html += '<thead><tr>' + ''.join(f'<th>{cell}</th>' for cell in header) + '</tr></thead>'
            
            # Add data rows
            table_html += '<tbody>'
            for row in rows[2:]:
                cells = [cell.strip() for cell in row.split('|')[1:-1]]
                table_html += '<tr>' + ''.join(f'<td>{cell}</td>' for cell in cells) + '</tr>'
            table_html += '</tbody></table>'
            
            st.markdown(table_html, unsafe_allow_html=True)
    else:
        st.markdown(recommendations)

def main():
    """Main application function with enhanced error handling"""
    try:
        # Initialize application
        if not initialize_app():
            return

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
                # Load schema types
                try:
                    schema_types_df = pd.read_csv('supported_schema.csv')
                except Exception as e:
                    logger.error(f"Failed to load schema types: {str(e)}")
                    st.error("Failed to load schema types data. Please try again.")
                    return

                # Initialize analyzers
                schema_analyzer = SchemaAnalyzer(url)
                competitor_analyzer = CompetitorAnalyzer(keyword)
                schema_validator = SchemaValidator(schema_types_df)

                # Extract schema data
                status_text.text("🔍 Analyzing schema markup...")
                schema_data = schema_analyzer.extract_schema()
                progress_bar.progress(0.25)

                # Analyze competitors
                status_text.text("🔄 Analyzing competitors...")
                competitor_data = {}
                try:
                    competitor_data = competitor_analyzer.analyze_competitors(
                        progress_callback=lambda p: progress_bar.progress(0.25 + p * 0.25)
                    )
                except Exception as e:
                    logger.error(f"Error analyzing competitors: {str(e)}")
                    error_container.error(f"Error analyzing competitors: {str(e)}")

                # Validate schema
                status_text.text("✅ Validating schema...")
                validation_results = None
                try:
                    if schema_data:
                        validation_results = schema_validator.validate_schema(schema_data)
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
                except Exception as e:
                    logger.error(f"Error validating schema: {str(e)}")
                    error_container.error(f"Error validating schema: {str(e)}")
                    return

                # Display results
                if validation_results:
                    progress_bar.progress(1.0)
                    status_text.text("✨ Analysis complete!")
                    time.sleep(1)
                    progress_bar.empty()
                    status_text.empty()

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
                                schema_type = schema.get('type', 'Unknown')
                                with st.expander(f"Schema: {schema_type}"):
                                    display_schema_documentation_links(schema_type, schema_types_df)
                                    
                                    st.markdown("### Implementation Details")
                                    if isinstance(schema.get('recommendations'), str):
                                        display_schema_recommendations(schema['recommendations'])
                                    else:
                                        st.write("Schema Properties:")
                                        for key, value in schema.items():
                                            if key not in ['type', 'recommendations', 'issues']:
                                                st.markdown(f"**{key}**: {value}")

                        if validation_results.get('needs_improvement'):
                            st.subheader("🔧 Needs Improvement")
                            for schema in validation_results['needs_improvement']:
                                schema_type = schema.get('type', 'Unknown')
                                with st.expander(f"Schema: {schema_type}"):
                                    # Add source badge
                                    source = schema.get('reason', 'Schema.org')
                                    st.markdown(
                                        f'''<div class="source-badge">
                                            <span class="source-icon">🔍</span>
                                            <span class="source-text">Source: {source}</span>
                                        </div>''',
                                        unsafe_allow_html=True
                                    )
                                    
                                    # Display documentation links
                                    display_schema_documentation_links(schema_type, schema_types_df)
                                    
                                    # Display formatted JSON schema
                                    if schema.get('key'):
                                        st.markdown("### Current Implementation")
                                        try:
                                            schema_json = json.loads(schema['key'])
                                            st.json(schema_json)
                                        except:
                                            st.code(schema['key'], language='json')
                                    
                                    # Display issues with icons
                                    if schema.get('issues'):
                                        display_schema_issues(schema['issues'])
                                    
                                    # Display recommendations
                                    if schema.get('recommendations'):
                                        display_schema_recommendations(schema['recommendations'])

                        with competitor_tab:
                            if competitor_data:
                                st.subheader("Competitor Schema Analysis")
                                st.markdown("### Schema Usage Among Competitors")
                                competitor_stats = competitor_analyzer.get_schema_usage_stats()
                                
                                if competitor_stats:
                                    # Create DataFrame for visualization
                                    stats_df = pd.DataFrame(competitor_stats)
                                    fig = px.bar(
                                        stats_df,
                                        x='schema_type',
                                        y='percentage',
                                        title='Schema Usage Distribution',
                                        labels={'schema_type': 'Schema Type', 'percentage': 'Usage (%)'}
                                    )
                                    st.plotly_chart(fig)

                            else:
                                st.info("No competitor data available")

                        with recommendations_tab:
                            st.subheader("💡 Recommendations")
                            if validation_results.get('suggested_additions'):
                                for suggestion in validation_results['suggested_additions']:
                                    with st.expander(f"Add {suggestion['type']} Schema"):
                                        st.markdown(f"**Why**: {suggestion.get('reason', 'Improve SEO')}")
                                        if suggestion.get('recommendations'):
                                            display_schema_recommendations(
                                                suggestion['recommendations'].get('recommendations', '')
                                            )

            except Exception as e:
                logger.error(f"Error in analysis: {str(e)}")
                st.error(f"An error occurred during analysis: {str(e)}")

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()