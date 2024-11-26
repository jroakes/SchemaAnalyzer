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
import plotly.graph_objects as go
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
                    if '|' in content and '-|-' in content:
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
            st.markdown(recommendations)
    else:
        st.json(recommendations)

def main():
    """Main application function with enhanced error handling"""
    try:
        if not initialize_app():
            return

        st.title("🚂 Schema.org Analysis Tool")
        st.markdown("""
        Analyze your website's schema markup implementation and compare it against competitors.
        Get recommendations for improvements and ensure compliance with schema.org standards.
        """)

        st.markdown('''
            <style>
                div[data-testid="stForm"] {
                    background: white;
                    border-radius: 8px;
                    padding: 1.5rem;
                    margin: 1rem 0;
                    box-shadow: none;
                }
                div.url-input-form {
                    display: none;
                }
                div[data-testid="stForm"] > div:first-child {
                    margin-top: 0;
                }
            </style>
        ''', unsafe_allow_html=True)

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
                submitted = st.form_submit_button(
                    "🔍 Analyze Schema",
                    use_container_width=True,
                    type="primary",
                    help="Click to analyze schema markup and get recommendations"
                )

            st.markdown('''
                <style>
                div.stButton > button {
                    background: linear-gradient(45deg, #2979ff, #1565c0);
                    color: white;
                    border-radius: 24px;
                    border: none;
                    font-weight: 600;
                    text-transform: uppercase;
                    letter-spacing: 1.2px;
                    padding: 0.75rem 2.5rem;
                }
                </style>
            ''', unsafe_allow_html=True)

        if submitted:
            if not url:
                st.error("Please enter a valid URL")
                return
            if not keyword:
                st.error("Please enter a target keyword")
                return

            progress_bar = st.progress(0)
            status_text = st.empty()
            error_container = st.empty()

            try:
                try:
                    schema_types_df = pd.read_csv('supported_schema.csv')
                except Exception as e:
                    logger.error(f"Failed to load schema types: {str(e)}")
                    st.error("Failed to load schema types data. Please try again.")
                    return

                schema_analyzer = SchemaAnalyzer(url)
                competitor_analyzer = CompetitorAnalyzer(keyword)
                schema_validator = SchemaValidator(schema_types_df, keyword)

                status_text.text("🔍 Analyzing schema markup...")
                schema_data = schema_analyzer.extract_schema()
                progress_bar.progress(0.25)

                status_text.text("🔄 Analyzing competitors...")
                competitor_data = {}
                try:
                    competitor_data = competitor_analyzer.analyze_competitors(
                        progress_callback=lambda p: progress_bar.progress(0.25 + p * 0.25)
                    )
                except Exception as e:
                    logger.error(f"Error analyzing competitors: {str(e)}")
                    error_container.error(f"Error analyzing competitors: {str(e)}")

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

                if validation_results:
                    progress_bar.progress(1.0)
                    status_text.text("✨ Analysis complete!")
                    time.sleep(1)
                    progress_bar.empty()
                    status_text.empty()

                    analysis_tab, competitor_tab = st.tabs([
                        "🔍 Schema Analysis",
                        "📊 Competitor Insights"
                    ])

                    with analysis_tab:
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

                    with competitor_tab:
                        st.subheader("📊 Schema Implementation Comparison")
                        
                        try:
                            with st.spinner("Analyzing competitor data..."):
                                competitor_analyzer = CompetitorAnalyzer(keyword)
                                competitor_data = competitor_analyzer.analyze_competitors()
                                
                                if not competitor_data:
                                    st.warning("No competitor data available for analysis.")
                                    return
                                    
                                insights = competitor_analyzer.get_competitor_insights()
                                
                                if insights:
                                    # Create main DataFrame for visualizations
                                    df = pd.DataFrame(insights)
                                    
                                    # 1. Schema Usage Bar Chart
                                    st.subheader("Schema Usage Distribution")
                                    fig_usage = px.bar(
                                        df,
                                        x='schema_type',
                                        y='percentage',
                                        title='Schema Usage Across Competitors',
                                        labels={
                                            'schema_type': 'Schema Type',
                                            'percentage': 'Usage Percentage (%)'
                                        },
                                        color='percentage',
                                        color_continuous_scale='Viridis'
                                    )
                                    
                                    fig_usage.update_layout(
                                        xaxis_tickangle=-45,
                                        showlegend=False,
                                        height=500,
                                        margin=dict(t=30, b=50)
                                    )
                                    
                                    st.plotly_chart(fig_usage, use_container_width=True)
                                    
                                    # 2. Implementation Comparison
                                    st.subheader("🔄 Your Implementation vs Competitors")
                                    current_types = set(schema_data.keys()) if schema_data else set()
                                    
                                    comparison_data = []
                                    for schema_type in set(df['schema_type']):
                                        competitor_usage = df[df['schema_type'] == schema_type]['percentage'].iloc[0]
                                        implemented = schema_type in current_types
                                        comparison_data.append({
                                            'Schema Type': schema_type,
                                            'Your Implementation': 1 if implemented else 0,
                                            'Competitor Usage (%)': competitor_usage,
                                            'Status': "✅ Implemented" if implemented else "❌ Missing"
                                        })
                                    
                                    comparison_df = pd.DataFrame(comparison_data)
                                    
                                    # Create grouped bar chart
                                    fig_comparison = go.Figure(data=[
                                        go.Bar(
                                            name='Your Implementation',
                                            x=comparison_df['Schema Type'],
                                            y=comparison_df['Your Implementation'],
                                            marker_color='#2979ff'
                                        ),
                                        go.Bar(
                                            name='Competitor Usage (%)',
                                            x=comparison_df['Schema Type'],
                                            y=comparison_df['Competitor Usage (%)'],
                                            marker_color='#00c853',
                                            opacity=0.7
                                        )
                                    ])
                                    
                                    fig_comparison.update_layout(
                                        barmode='group',
                                        title='Schema Implementation Comparison',
                                        xaxis_tickangle=-45,
                                        height=500,
                                        margin=dict(t=30, b=50)
                                    )
                                    
                                    st.plotly_chart(fig_comparison, use_container_width=True)
                                    
                                    # 3. Summary Statistics
                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.metric(
                                            "Total Competitors Analyzed",
                                            len(competitor_data),
                                            help="Number of competitor websites analyzed"
                                        )
                                    with col2:
                                        implementation_rate = len([
                                            1 for row in comparison_data 
                                            if row['Your Implementation'] == 1
                                        ]) / len(comparison_data) * 100
                                        st.metric(
                                            "Your Implementation Rate",
                                            f"{implementation_rate:.1f}%",
                                            help="Percentage of competitor schemas you have implemented"
                                        )
                                    
                                    # 4. Detailed Comparison Table
                                    st.subheader("📋 Detailed Schema Comparison")
                                    st.dataframe(
                                        comparison_df.style.apply(
                                            lambda x: ['background-color: #e8f5e9' if v == "✅ Implemented"
                                            else 'background-color: #ffebee' for v in x
                                            ],
                                            subset=['Status']
                                        ),
                                        use_container_width=True
                                    )
                                    
                                    # 5. Recommendations based on comparison
                                    st.subheader("💡 Implementation Recommendations")
                                    missing_schemas = comparison_df[comparison_df['Your Implementation'] == 0].sort_values(
                                        by='Competitor Usage (%)', 
                                        ascending=False
                                    )
                                    
                                    if not missing_schemas.empty:
                                        st.warning("#### Priority Implementation Suggestions")
                                        for _, row in missing_schemas.iterrows():
                                            st.markdown(
                                                f"- **{row['Schema Type']}**: {row['Competitor Usage (%)']}% of competitors "
                                                f"use this schema type"
                                            )
                                    else:
                                        st.success("✨ Great job! You've implemented all common schema types used by competitors.")
                                    
                            except Exception as e:
                                logger.error(f"Error in competitor analysis visualization: {str(e)}")
                                st.error(f"Error creating competitor analysis visualization: {str(e)}")
                                
            except Exception as e:
                logger.error(f"Error in main analysis: {str(e)}")
                st.error(f"An error occurred during analysis: {str(e)}")

if __name__ == "__main__":
    main()