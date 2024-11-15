import streamlit as st
import pandas as pd
from schema_analyzer import SchemaAnalyzer
from competitor_analyzer import CompetitorAnalyzer
from schema_validator import SchemaValidator
import plotly.express as px
import plotly.graph_objects as go

# Load schema types
schema_types_df = pd.read_csv('supported_schema.csv')

# Page config
st.set_page_config(
    page_title="Schema Analysis Tool",
    page_icon="🔍",
    layout="wide"
)

# Custom CSS
with open('assets/styles.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

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
    with st.spinner("Analyzing schema markup..."):
        # Initialize analyzers
        schema_analyzer = SchemaAnalyzer(url)
        competitor_analyzer = CompetitorAnalyzer(keyword)
        schema_validator = SchemaValidator(schema_types_df)

        # Get current schema
        current_schema = schema_analyzer.extract_schema()
        
        # Get competitor data
        competitor_data = competitor_analyzer.analyze_competitors()
        
        # Validate schema
        validation_results = schema_validator.validate_schema(current_schema)

        # Results display
        st.header("Analysis Results")
        
        # Current Implementation
        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Current Schema Implementation")
            if current_schema:
                for schema_type, data in current_schema.items():
                    st.write(f"📌 {schema_type}")
                    st.json(data)
            else:
                st.warning("No schema markup detected")

        # Competitor Analysis
        with col2:
            st.subheader("Competitor Schema Usage")
            fig = px.bar(
                competitor_analyzer.get_schema_usage_stats(),
                x='schema_type',
                y='usage_count',
                title='Popular Schema Types Among Competitors'
            )
            st.plotly_chart(fig)

        # Recommendations
        st.header("Recommendations")
        
        # Missing Schema Types
        missing_types = schema_validator.get_missing_schema_types(current_schema)
        if missing_types:
            st.subheader("Missing Schema Opportunities")
            for schema_type in missing_types:
                st.markdown(f"""
                * **{schema_type}**
                  * URL: {schema_types_df[schema_types_df['Name'] == schema_type]['Schema URL'].iloc[0]}
                  * Google Doc: {schema_types_df[schema_types_df['Name'] == schema_type]['Google Doc URL'].iloc[0]}
                """)

        # Rich Results Potential
        st.subheader("Rich Results Potential")
        rich_results = schema_validator.analyze_rich_result_potential(current_schema)
        for result_type, details in rich_results.items():
            st.info(f"🎯 {result_type}: {details}")

        # Documentation References
        st.header("Documentation References")
        st.dataframe(
            schema_types_df[['Name', 'Schema URL', 'Google Doc URL']],
            hide_index=True
        )

else:
    st.info("Enter a URL and keyword to begin analysis")
