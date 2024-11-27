import streamlit as st
import pandas as pd
import plotly.express as px
import time
import logging
from typing import Dict, List, Any, Optional
from schema_analyzer import SchemaAnalyzer
from competitor_analyzer import CompetitorAnalyzer
from schema_validator import SchemaValidator

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def initialize_app() -> bool:
    """Initialize the Streamlit application with required settings."""
    try:
        st.set_page_config(
            page_title="Schema.org Analyzer",
            page_icon="🚂",
            layout="wide"
        )
        return True
    except Exception as e:
        logger.error(f"Error initializing app: {str(e)}")
        st.error(f"Error initializing application: {str(e)}")
        return False

def get_doc_url(row: pd.Series, column: str) -> Optional[str]:
    """Get documentation URL from DataFrame row"""
    try:
        return row[column].iloc[0] if column in row else None
    except Exception:
        return None

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

def display_schema_issues(issues: List[Dict[str, Any]], container=None):
    """Display schema validation issues with proper formatting in a specified container"""
    display_target = container if container else st
    display_target.markdown("### Issues Found")
    
    for issue in issues:
        severity = issue.get('severity', 'info')
        icon_map = {
            "error": "🚫",
            "warning": "⚠️",
            "info": "ℹ️"
        }
        icon = icon_map.get(severity, "ℹ️")
        message = issue.get('message', '')
        
        display_target.markdown(
            f"""<div class="issue-{severity}">
                {icon} <strong>{severity.title()}</strong>: {message}
            </div>""",
            unsafe_allow_html=True
        )
        
        if suggestion := issue.get('suggestion'):
            display_target.markdown(
                f"""<div class="suggestion">
                    💡 <em>Suggestion</em>: {suggestion}
                </div>""",
                unsafe_allow_html=True
            )

def display_schema_card(schema: Dict[str, Any], card_type: str, schema_types_df: pd.DataFrame):
    """Display a schema card with consistent styling and expandable content
    
    Args:
        schema: Schema data dictionary
        card_type: Type of card ('good', 'needs_improvement', or 'suggested')
        schema_types_df: DataFrame containing schema type information
    """
    icons = {
        'good': '✅',
        'needs_improvement': '⚠️',
        'suggested': '💡'
    }
    
    titles = {
        'good': 'Good Implementation',
        'needs_improvement': 'Needs Improvement',
        'suggested': schema.get('reason', 'Suggested Addition')
    }
    
    icon = icons.get(card_type, '📄')
    title = titles.get(card_type)
    
    with st.expander(f"{icon} {schema['type']} ({title})", expanded=False):
        st.markdown(f"""
            <div class="schema-card {card_type}">
                <h4>Implementation Details</h4>
            </div>
        """, unsafe_allow_html=True)
        
        display_schema_documentation_links(schema['type'], schema_types_df)
        
        if card_type == 'needs_improvement' and 'issues' in schema:
            display_schema_issues(schema['issues'])
            
        if 'data' in schema:
            st.json(schema['data'])
        elif 'example_implementation' in schema:
            st.markdown("#### Example Implementation")
            st.json(schema['example_implementation'])

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
        st.title("🚂 Schema.org Analysis Tool")
        st.markdown("""
        Analyze your website's schema markup implementation and compare it against competitors.
        Get recommendations for improvements and ensure compliance with schema.org standards.
        """)

        # Add form styling
        st.markdown('''
            <style>
                div[data-testid="stForm"] {
                    background: white;
                    border-radius: 8px;
                    padding: 1.5rem;
                    margin: 1rem 0;
                    box-shadow: none;
                }
                
                /* Remove any duplicate containers */
                div.url-input-form {
                    display: none;
                }
                
                /* Clean up form spacing */
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
            
            # Create three columns for button centering
            col1, col2, col3 = st.columns([1, 2, 1])

            # Place the button in the middle column
            with col2:
                submitted = st.form_submit_button(
                    "🔍 Analyze Schema",
                    use_container_width=True,
                    type="primary",
                    help="Click to analyze schema markup and get recommendations"
                )

            # Add minimal CSS just for button styling
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
                schema_validator = SchemaValidator(schema_types_df, keyword)

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
                        metrics = [
                            ("Good Implementations", 'good_schemas', "Number of well-implemented schemas"),
                            ("Needs Improvement", 'needs_improvement', "Number of schemas requiring updates"),
                            ("Suggested Additions", 'suggested_additions', "Number of recommended new schemas")
                        ]
                        
                        for (title, key, help_text), col in zip(metrics, [col1, col2, col3]):
                            with col:
                                st.metric(
                                    title,
                                    len(validation_results.get(key, [])),
                                    help=help_text
                                )

                        # Schema sections with consistent styling
                        sections = [
                            ("✅ Good Implementations", 'good_schemas', 'good'),
                            ("⚠️ Needs Improvement", 'needs_improvement', 'needs_improvement'),
                            ("💡 Suggested Additions", 'suggested_additions', 'suggested')
                        ]
                        
                        for section_title, section_key, card_type in sections:
                            if schemas := validation_results.get(section_key):
                                st.markdown(f"### {section_title}")
                                for schema in schemas:
                                    display_schema_card(schema, card_type, schema_types_df)

                    with competitor_tab:
                        st.subheader("📊 Schema Implementation Comparison")
                        
                        # Get competitor insights
                        insights = competitor_analyzer.get_competitor_insights()
                        
                        # Create visualization data
                        if insights:
                            df = pd.DataFrame(insights)
                            
                            # Bar chart for schema usage
                            fig = px.bar(df, 
                                       x='schema_type', 
                                       y='percentage',
                                       title='Schema Usage Across Competitors',
                                       labels={'schema_type': 'Schema Type', 
                                              'percentage': 'Usage Percentage (%)'},
                                       color='percentage',
                                       color_continuous_scale='Viridis')
                            
                            fig.update_layout(
                                xaxis_tickangle=-45,
                                showlegend=False,
                                height=500
                            )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Detailed statistics table
                            st.subheader("📈 Detailed Statistics")
                            stats_df = df[['schema_type', 'count', 'percentage']].copy()
                            stats_df.columns = ['Schema Type', 'Number of Competitors', 'Usage Percentage (%)']
                            stats_df['Usage Percentage (%)'] = stats_df['Usage Percentage (%)'].round(1)
                            st.dataframe(stats_df, use_container_width=True)
                            
                            # Current implementation comparison
                            if schema_data:
                                st.subheader("🔄 Your Implementation vs Competitors")
                                current_types = set(schema_data.keys())
                                comparison_data = []
                                
                                for schema_type in set(df['schema_type']):
                                    competitor_usage = df[df['schema_type'] == schema_type]['percentage'].iloc[0]
                                    status = "✅ Implemented" if schema_type in current_types else "❌ Missing"
                                    comparison_data.append({
                                        'Schema Type': schema_type,
                                        'Status': status,
                                        'Competitor Usage': f"{competitor_usage:.1f}%"
                                    })
                                
                                comparison_df = pd.DataFrame(comparison_data)
                                st.dataframe(comparison_df, use_container_width=True)
                        else:
                            st.info("No competitor data available for comparison")

            except Exception as e:
                logger.error(f"Error in analysis: {str(e)}")
                error_container.error(f"Error in analysis: {str(e)}")
                return

    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error(f"Application error: {str(e)}")

if __name__ == "__main__":
    main()
