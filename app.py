import streamlit as st
import requests

API_URL = "http://localhost:8000"

def main():
    st.set_page_config(
        page_title="Expense Receipt Parser",
        page_icon="🧾",
        layout="centered"
    )
    
    st.title("🧾 Expense Receipt Parser")
    st.markdown("Upload a receipt image and provide context to extract expense data.")
    
    # File uploader for receipt image
    uploaded_file = st.file_uploader(
        "Upload Receipt Image",
        type=["jpg", "jpeg", "png"],
        help="Upload a clear image of your receipt"
    )
    
    # Text area for context
    context = st.text_area(
        "Context",
        placeholder="Provide additional context such as:\n- Expense category (dinner, lunch, taxi, etc.)\n- Participants (e.g., 'John Smith from Acme Corp, Jane Doe')\n- Project name to charge to",
        height=150,
        help="This helps the AI better categorize and fill out the expense details"
    )
    
    # Submit button
    if st.button("Parse Receipt", type="primary", use_container_width=True):
        if uploaded_file is None:
            st.error("Please upload a receipt image.")
        else:
            with st.spinner("Analyzing receipt..."):
                try:
                    # Call the API
                    files = {"image": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    data = {"context": context}
                    
                    response = requests.post(f"{API_URL}/parse-receipt", files=files, data=data)
                    
                    if response.status_code != 200:
                        st.error(f"API Error: {response.json().get('detail', 'Unknown error')}")
                        return
                    
                    result = response.json()
                    expense = result["expense"]
                    saved_path = result["saved_path"]
                    
                    # Display success message
                    st.success(f"Expense saved to: `{saved_path}`")
                    
                    # Display the extracted expense data
                    st.subheader("Extracted Expense Data")
                    
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.markdown("**Expense Name:**")
                        st.write(expense["expense_name"])
                        
                        st.markdown("**Amount:**")
                        st.write(f"${expense['amount']:.2f}")
                        
                        st.markdown("**Date:**")
                        date = expense["date"]
                        st.write(f"{date['month']}/{date['day']}/{date['year']}")
                    
                    with col2:
                        st.markdown("**Category:**")
                        st.write(expense["category"])
                        
                        st.markdown("**Project:**")
                        st.write(expense["project_name"] or "N/A")
                    
                    # Participants section
                    if expense["participants"]:
                        st.markdown("**Participants:**")
                        for p in expense["participants"]:
                            company_str = f" ({p['company']})" if p.get("company") else ""
                            st.write(f"- {p['first']} {p['last']}{company_str}")
                    else:
                        st.markdown("**Participants:** None")
                    
                    # Show raw JSON
                    with st.expander("View Raw JSON"):
                        st.json(expense)
                        
                except requests.exceptions.ConnectionError:
                    st.error("Could not connect to API. Make sure the API server is running on http://localhost:8000")
                except Exception as e:
                    st.error(f"Error: {str(e)}")


if __name__ == "__main__":
    main()



