import streamlit as st
import requests

API_URL = "http://localhost:8000"

st.set_page_config(page_title="GraphRAG AI", layout="wide")

st.title("GraphRAG Knowledge Engine")

# Tabs
tab1, tab2 = st.tabs(["Ask", "Ingest"])

# ---------------- ASK ----------------
with tab1:
    st.subheader("Ask a Question")

    query = st.text_input("Enter your question")

    if st.button("Ask"):
        if query:
            try:
                res = requests.post(f"{API_URL}/ask", json={"query": query})

                if res.status_code != 200:
                    st.error(f"Error: {res.text}")
                else:
                    data = res.json()

                    st.success("Answer:")
                    st.write(data.get("answer", "No answer"))

                    st.subheader("Sources")
                    st.json(data.get("sources", []))

                    st.subheader("Graph Context")
                    st.json(data.get("subgraph", {}))

            except Exception as e:
                st.error(f"Request failed: {e}")

# ---------------- INGEST ----------------
with tab2:
    st.subheader("Add Knowledge")

    text = st.text_area("Enter text to ingest")
    source = st.text_input("Source name", "user_input")

    if st.button("Ingest"):
        if text:
            try:
                res = requests.post(
                    f"{API_URL}/ingest",
                    json={
                        "text": text,
                        "source_name": source
                    }
                )

                if res.status_code != 200:
                    st.error(f"Error: {res.text}")
                else:
                    data = res.json()

                    # SAFE ACCESS ✅
                    message = data.get("message", "Ingested successfully ✅")
                    st.success(message)

                    st.write("Entities created:", data.get("entities_created", 0))
                    st.write("Relationships created:", data.get("relationships_created", 0))

            except Exception as e:
                st.error(f"Request failed: {e}")