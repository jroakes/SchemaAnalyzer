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
        if isinstance(schema_row, pd.DataFrame) and not schema_row.empty and url_type in schema_row.columns:
            url = schema_row[url_type].iloc[0]
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
    if not recommendations:
        return
        
    st.markdown("### Recommendations")
    
    if isinstance(recommendations, str):
        # Handle markdown-formatted recommendations
        if '##' in recommendations:
            sections = recommendations.split('##')
            for section in sections:
                if not section.strip():
                    continue
                    
                lines = section.split('\n')
                title = lines[0].strip()
                content = '\n'.join(lines[1:]).strip()
                
                if title:
                    st.markdown(f"#### {title}")
                
                if content:
                    # Check if content contains a table
                    if '|' in content and '-|-' in content:
                        # Find table and non-table content
                        table_lines = []
                        other_lines = []
                        
                        for line in content.split('\n'):
                            if '|' in line or '-|-' in line:
                                table_lines.append(line)
                            elif line.strip():
                                other_lines.append(line)
                        
                        if table_lines:
                            st.markdown('\n'.join(table_lines))
                        if other_lines:
                            st.markdown('\n'.join(other_lines))
                    else:
                        st.markdown(content)
        else:
            # Handle plain text recommendations
            st.markdown(recommendations)
    else:
        # Handle non-string recommendations (e.g., dict or list)
        st.json(recommendations)

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
            
            # Create a container for the button with custom styling
            st.markdown('''
                <style>
                    div[data-testid="stForm"] {
                        background: white;
                        border-radius: 8px;
                        padding: 1rem;
                        margin-bottom: 1rem;
                    }
                    
                    div.stButton {
                        text-align: center;
                        padding: 0;
                        margin-top: 1rem;
                    }
                    
                    div.stButton > button {
                        display: inline-flex;
                        align-items: center;
                        justify-content: center;
                        min-width: 200px;
                        max-width: 300px;
                        font-size: 1.2rem;
                        height: auto;
                        padding: 1rem 3rem;
                        background: linear-gradient(45deg, #2979ff, #1565c0);
                        border: none;
                        border-radius: 30px;
                        box-shadow: 0 4px 6px rgba(41, 121, 255, 0.2);
                        transition: all 0.3s ease;
                        text-transform: uppercase;
                        letter-spacing: 1px;
                        margin: 0 auto;
                    }
                    
                    div.stButton > button:hover {
                        transform: translateY(-2px);
                        box-shadow: 0 6px 12px rgba(41, 121, 255, 0.3);
                        background: linear-gradient(45deg, #1565c0, #0d47a1);
                    }
                    
                    div.stButton > button:active {
                        transform: translateY(1px);
                        box-shadow: 0 2px 4px rgba(41, 121, 255, 0.2);
                    }
                </style>
            ''', unsafe_allow_html=True)

            # Remove the custom container divs since we're handling it with CSS
            submitted = st.form_submit_button(
                "🔍 Analyze Schema",
                use_container_width=False,
                type="primary",
                help="Click to analyze schema markup and get recommendations"
            )
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
                    validation_results = schema_validator.validate_schema(schema_data)
                    progress_bar.progress(0.75)
                    if not schema_data:
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
                    analysis_tab, competitor_tab = st.tabs([
                        "🔍 Schema Analysis",
                        "📊 Competitor Insights"
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
                                    st.markdown(
                                        '''<div class="status-badge success">
                                            ✅ Passed Schema.org Validation
                                        </div>''',
                                        unsafe_allow_html=True
                                    )
                                    
                                    display_schema_documentation_links(schema_type, schema_types_df)
                                    
                                    st.markdown("### Current Implementation")
                                    if schema.get('key'):
                                        try:
                                            schema_json = json.loads(schema['key']) if isinstance(schema['key'], str) else schema['key']
                                            st.json(schema_json)  # Use st.json for better formatting
                                        except json.JSONDecodeError:
                                            st.code(schema['key'], language='json')

                        if validation_results.get('needs_improvement'):
                            st.subheader("🔧 Needs Improvement")
                            for schema in validation_results['needs_improvement']:
                                schema_type = schema.get('type', 'Unknown')
                                with st.expander(f"Schema: {schema_type}"):
                                    st.markdown(
                                        '''<div class="status-badge error">
                                            ❌ Failed Schema.org Validation
                                        </div>''',
                                        unsafe_allow_html=True
                                    )
                                    
                                    # Add source badge
                                    source = schema.get('reason', 'Schema Validation')
                                    st.markdown(
                                        f'''<div class="source-badge">
                                            <span class="source-icon">🔍</span>
                                            <span class="source-text">Source: {source}</span>
                                        </div>''',
                                        unsafe_allow_html=True
                                    )
                                    
                                    # Display documentation links
                                    display_schema_documentation_links(schema_type, schema_types_df)
                                    
                                    # Display current implementation
                                    if schema.get('key'):
                                        st.markdown("### Current Implementation")
                                        try:
                                            schema_json = json.loads(schema['key']) if isinstance(schema['key'], str) else schema['key']
                                            st.json(schema_json)  # Use st.json for better formatting
                                        except json.JSONDecodeError:
                                            st.code(schema['key'], language='json')
                                    
                                    # Display issues with improved formatting
                                    if schema.get('issues'):
                                        st.markdown("### Issues Found")
                                        for issue in schema['issues']:
                                            severity = issue.get('severity', 'info')
                                            icon = "🚫" if severity == "error" else "⚠️" if severity == "warning" else "ℹ️"
                                            message = issue.get('message', '')
                                            
                                            st.markdown(
                                                f'''<div class="issue-{severity}">
                                                    {icon} <strong>{severity.title()}</strong>: {message}
                                                </div>''',
                                                unsafe_allow_html=True
                                            )
                                            
                                            if suggestion := issue.get('suggestion'):
                                                st.markdown(
                                                    f'''<div class="suggestion">
                                                        💡 <em>Suggestion</em>: {suggestion}
                                                    </div>''',
                                                    unsafe_allow_html=True
                                                )
                                    
                                    # Display recommendations with improved formatting
                                    if schema.get('recommendations'):
                                        st.markdown("### Recommendations")
                                        recommendations = schema['recommendations']
                                        display_schema_recommendations(recommendations)

                        # Add suggested additions section
                        if validation_results.get('suggested_additions'):
                            st.subheader("💡 Suggested Additions")
                            for schema in validation_results['suggested_additions']:
                                schema_type = schema.get('type', 'Unknown')
                                with st.expander(f"Schema: {schema_type}"):
                                    # Display documentation links
                                    display_schema_documentation_links(schema_type, schema_types_df)
                                    
                                    # Display reason for suggestion
                                    st.markdown(f"**Reason:** {schema.get('reason', 'Recommended Schema')}")
                                    
                                    # Display recommendations
                                    if schema.get('recommendations', {}).get('recommendations'):
                                        st.markdown("### Implementation Guidelines")
                                        recommendations = schema['recommendations']['recommendations']
                                        if isinstance(recommendations, str):
                                            st.markdown(recommendations)
                                        else:
                                            st.json(recommendations)

                    with competitor_tab:
                        if competitor_data:
                            # Get competitor insights
                            insights = competitor_analyzer.get_competitor_insights()
                            
                            # Display competitor schema usage
                            st.subheader("📊 Schema Usage Among Competitors")
                            
                            # Create DataFrame for visualization
                            if insights:
                                df = pd.DataFrame(insights)
                                
                                # Create bar chart
                                fig = px.bar(
                                    df,
                                    x='schema_type',
                                    y='percentage',
                                    title='Schema Type Usage (%)',
                                    labels={'schema_type': 'Schema Type', 'percentage': 'Usage (%)'}
                                )
                                fig.update_layout(
                                    xaxis_tickangle=-45,
                                    showlegend=False,
                                    margin=dict(b=100)
                                )
                                st.plotly_chart(fig)
                                
                                # Display detailed insights
                                st.subheader("📋 Detailed Insights")
                                for insight in insights:
                                    with st.expander(f"Schema: {insight['schema_type']}"):
                                        st.markdown(f"""
                                        - **Usage:** {insight['count']} competitors ({insight['percentage']:.1f}%)
                                        - **Recommendation:** {insight['recommendation']}
                                        """)
                                        
                                        # Add documentation links
                                        display_schema_documentation_links(insight['schema_type'], schema_types_df)
                            
                            # Display skipped URLs if any
                            skipped = competitor_analyzer.get_skipped_urls()
                            if skipped:
                                st.subheader("⚠️ Analysis Limitations")
                                st.markdown("The following URLs could not be analyzed:")
                                for url, reason in skipped.items():
                                    st.markdown(f"- `{url}`: {reason}")
                        else:
                            st.info("No competitor data available. Try analyzing with a different keyword.")

            except Exception as e:
                logger.error(f"Error in analysis: {str(e)}")
                st.error(f"An error occurred during analysis: {str(e)}")

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    main()