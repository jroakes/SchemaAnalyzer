import os
import streamlit as st
import pandas as pd
from schema_analyzer import SchemaAnalyzer
from competitor_analyzer import CompetitorAnalyzer
from schema_validator import SchemaValidator
import plotly.express as px
import plotly.graph_objects as go
import time

# Initialize session state if not exists
if 'analysis_complete' not in st.session_state:
    st.session_state.analysis_complete = False

# Page config
st.set_page_config(
    page_title="Schema Analysis Tool",
    page_icon="🔍",
    layout="wide"
)

# Load schema types
@st.cache_data
def load_schema_types():
    try:
        return pd.read_csv('supported_schema.csv')
    except Exception as e:
        st.error(f"Error loading schema types: {str(e)}")
        return pd.DataFrame()

schema_types_df = load_schema_types()

# Custom CSS
try:
    with open('assets/styles.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except Exception as e:
    st.warning("Custom styles could not be loaded.")

st.title("Schema Markup Analysis Tool")

# Input form
with st.form("url_input"):
    col1, col2 = st.columns(2)
    with col1:
        url = st.text_input("Enter URL to analyze", placeholder="https://example.com")
    with col2:
        keyword = st.text_input("Enter target keyword", placeholder="digital marketing")
    
    submitted = st.form_submit_button("Analyze Schema")

if submitted and url and keyword:
    try:
        # Initialize progress containers
        schema_progress = st.progress(0, text="Analyzing schema markup...")
        competitor_progress = st.progress(0, text="Analyzing competitors...")
        
        # Initialize analyzers
        schema_analyzer = SchemaAnalyzer(url)
        competitor_analyzer = CompetitorAnalyzer(keyword)
        schema_validator = SchemaValidator(schema_types_df)

        # Get current schema
        current_schema = schema_analyzer.extract_schema()
        schema_progress.progress(1.0, text="Schema analysis complete!")
        
        # Get competitor data with progress tracking
        def update_competitor_progress(progress):
            competitor_progress.progress(progress, text=f"Analyzing competitors ({int(progress * 100)}%)")
            
        competitor_data = competitor_analyzer.analyze_competitors(progress_callback=update_competitor_progress)
        competitor_progress.progress(1.0, text="Competitor analysis complete!")
        
        # Validate schema
        validation_results = schema_validator.validate_schema(current_schema)
        
        # Set analysis complete flag
        st.session_state.analysis_complete = True

        # Results display
        st.header("Analysis Results")
        
        # Current Implementation
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Current Schema Implementation")
            if current_schema:
                for schema_type, data in current_schema.items():
                    with st.expander(f"📌 {schema_type}"):
                        st.json(data)
                        if schema_type in validation_results['recommendations']:
                            st.info(validation_results['recommendations'][schema_type]['description'])
                            if validation_results['recommendations'][schema_type]['best_practices']:
                                st.markdown("**Best Practices:**")
                                for practice in validation_results['recommendations'][schema_type]['best_practices']:
                                    st.markdown(f"- {practice}")
            else:
                st.warning("No schema markup detected")

        # Competitor Analysis
        with col2:
            st.subheader("Competitor Schema Usage")
            
            # Create responsive visualization
            competitor_stats = competitor_analyzer.get_schema_usage_stats()
            if competitor_stats:
                fig = go.Figure()
                
                fig.add_trace(go.Bar(
                    x=[stat['schema_type'] for stat in competitor_stats],
                    y=[stat['usage_count'] for stat in competitor_stats],
                    text=[f"{stat['percentage']:.1f}%" for stat in competitor_stats],
                    textposition='auto',
                    hovertemplate="<b>%{x}</b><br>" +
                                "Count: %{y}<br>" +
                                "Usage: %{text}<br>" +
                                "<extra></extra>"
                ))
                
                fig.update_layout(
                    title='Popular Schema Types Among Competitors',
                    xaxis_title='Schema Type',
                    yaxis_title='Usage Count',
                    template='plotly_white',
                    height=400,
                    margin=dict(t=30, l=10, r=10, b=10),
                    showlegend=False
                )
                
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No competitor data available")

        # Recommendations
        st.header("Recommendations")
        
        # Missing Schema Types
        missing_types = schema_validator.get_missing_schema_types(current_schema)
        if missing_types:
            st.subheader("Missing Schema Opportunities")
            for schema_info in missing_types:
                with st.expander(f"💡 {schema_info['type']}"):
                    tooltip = schema_info['tooltip']
                    st.markdown(f"""
                    **Why implement this?**  
                    {tooltip}
                    
                    **Resources:**
                    - [Schema.org Documentation]({schema_info['url']})
                    - [Google Search Guidelines]({schema_info['google_doc'] if schema_info['google_doc'] else '#'})
                    """)

        # Rich Results Potential
        st.subheader("Rich Results Potential")
        rich_results = schema_validator.analyze_rich_result_potential(current_schema)
        for result_type, details in rich_results.items():
            with st.expander(f"🎯 {result_type}"):
                st.markdown(f"""
                **{details['message']}**  
                {details['description']}
                
                **Required Properties:**
                """)
                for req in details['requirements']:
                    st.markdown(f"- `{req}`")

        # Documentation References
        st.header("Documentation References")
        st.dataframe(
            schema_types_df[['Name', 'Description', 'Schema URL', 'Google Doc URL']].style.set_properties(**{
                'background-color': 'white',
                'color': 'black',
                'border-color': 'lightgray'
            }),
            hide_index=True,
            use_container_width=True
        )
            
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        import traceback
        st.error(traceback.format_exc())
else:
    st.info("Enter a URL and keyword to begin analysis")
