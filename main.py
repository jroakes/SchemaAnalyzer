import streamlit as st

def main():
    st.set_page_config(
        page_title="Schema Analysis Tool",
        page_icon="🔍",
        layout="wide"
    )

    st.title("Schema Analysis Tool - Test")
    st.write("This is a test page")
    
    st.text_input("Test input")
    st.button("Test button")

if __name__ == "__main__":
    main()