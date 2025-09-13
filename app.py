import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import json
import io

# Constants
DB_PATH = "graph_configs.db"
CHART_TYPES = ["Bar", "Line", "Scatter", "Pie", "Histogram"]

# Initialize DB
conn = sqlite3.connect(DB_PATH)
conn.execute("""
CREATE TABLE IF NOT EXISTS graphs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    chart_type TEXT,
    x_param TEXT,
    y_param TEXT,
    filters TEXT
)
""")
conn.commit()

# App UI
st.set_page_config(page_title="📊 Chart Builder", layout="wide")
st.title("📊 Interactive Chart Builder")

# Upload dataset
uploaded_file = st.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx"])
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        st.success("File uploaded successfully!")
        st.dataframe(df.head())

        # Chart configuration
        chart_type = st.selectbox("Chart Type", CHART_TYPES)
        x_param = st.selectbox("X-axis", df.columns)
        y_param = st.selectbox("Y-axis", df.columns)
        filters = {}

        with st.expander("Optional Filters"):
            for col in df.select_dtypes(include=["object", "category"]).columns:
                options = df[col].unique().tolist()
                selected = st.multiselect(f"Filter {col}", options)
                if selected:
                    filters[col] = selected

        # Apply filters
        for col, vals in filters.items():
            df = df[df[col].isin(vals)]

        # Generate chart
        fig = None
        if chart_type == "Bar":
            fig = px.bar(df, x=x_param, y=y_param)
        elif chart_type == "Line":
            fig = px.line(df, x=x_param, y=y_param)
        elif chart_type == "Scatter":
            fig = px.scatter(df, x=x_param, y=y_param)
        elif chart_type == "Pie":
            fig = px.pie(df, names=x_param, values=y_param)
        elif chart_type == "Histogram":
            fig = px.histogram(df, x=x_param)

        if fig:
            st.plotly_chart(fig, use_container_width=True)

        # Save config
        if st.button("💾 Save Graph Configuration"):
            config = {
                "chart_type": chart_type,
                "x_param": x_param,
                "y_param": y_param,
                "filters": filters
            }
            conn.execute("INSERT INTO graphs (name, chart_type, x_param, y_param, filters) VALUES (?, ?, ?, ?, ?)",
                         (f"{chart_type}: {x_param} vs {y_param}", chart_type, x_param, y_param, json.dumps(filters)))
            conn.commit()
            st.success("Configuration saved!")

        # Export options
        st.download_button("⬇️ Export Data as CSV", df.to_csv(index=False), "processed_data.csv")
        excel_buf = io.BytesIO()
        df.to_excel(excel_buf, index=False)
        st.download_button("⬇️ Export Data as Excel", excel_buf.getvalue(), "processed_data.xlsx")
        st.download_button("⬇️ Export Config as JSON", json.dumps(config), "graph_config.json")

        # Saved Graphs
        st.subheader("📁 Saved Graphs")
        graphs = conn.execute("SELECT id, name FROM graphs").fetchall()
        for graph_id, name in graphs:
            col1, col2, col3 = st.columns([4, 1, 1])
            with col1:
                st.write(name)
            with col2:
                if st.button("🗑️ Delete", key=f"del_{graph_id}"):
                    conn.execute("DELETE FROM graphs WHERE id=?", (graph_id,))
                    conn.commit()
                    st.experimental_rerun()
            with col3:
                if st.button("🔁 Regenerate", key=f"regen_{graph_id}"):
                    row = conn.execute("SELECT chart_type, x_param, y_param, filters FROM graphs WHERE id=?", (graph_id,)).fetchone()
                    chart_type, x_param, y_param, filters_json = row
                    filters = json.loads(filters_json)
                    temp_df = df.copy()
                    for col, vals in filters.items():
                        temp_df = temp_df[temp_df[col].isin(vals)]
                    fig = None
                    if chart_type == "Bar":
                        fig = px.bar(temp_df, x=x_param, y=y_param)
                    elif chart_type == "Line":
                        fig = px.line(temp_df, x=x_param, y=y_param)
                    elif chart_type == "Scatter":
                        fig = px.scatter(temp_df, x=x_param, y=y_param)
                    elif chart_type == "Pie":
                        fig = px.pie(temp_df, names=x_param, values=y_param)
                    elif chart_type == "Histogram":
                        fig = px.histogram(temp_df, x=x_param)
                    if fig:
                        st.plotly_chart(fig, use_container_width=True)

    except Exception as e:
        st.error(f"Error: {e}")
else:
    st.info("Upload a dataset to get started.")

conn.close()
