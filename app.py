import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
import json
import io

# =========================
# PAGE CONFIG
# =========================
st.set_page_config(
    page_title="Interactive Chart Builder",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# =========================
# CUSTOM CSS (MODERN UI)
# =========================
st.markdown("""
<style>
.main {
    background-color: #f8fafc;
}
h1, h2, h3 {
    font-weight: 700;
    color: #0f172a;
}
.metric-card {
    background-color: white;
    padding: 20px;
    border-radius: 14px;
    box-shadow: 0px 4px 10px rgba(0,0,0,0.08);
    text-align: center;
}
.section-card {
    background-color: white;
    padding: 18px;
    border-radius: 16px;
    box-shadow: 0px 6px 14px rgba(0,0,0,0.08);
    margin-bottom: 20px;
}
.sidebar-title {
    font-weight: 700;
    font-size: 20px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# =========================
# DATABASE INIT
# =========================
DB_PATH = "graph_configs.db"
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

# =========================
# APP HEADER
# =========================
st.markdown("""
<h1>📊 Interactive Data Visualization Dashboard</h1>
<p style="color:#64748b; font-size:16px;">
Upload datasets, apply filters, build interactive charts, and save configurations.
</p>
<hr>
""", unsafe_allow_html=True)

# =========================
# SIDEBAR CONTROLS
# =========================
with st.sidebar:
    st.markdown("<div class='sidebar-title'>⚙️ Chart Controls</div>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("Upload Dataset", type=["csv", "xlsx"])

CHART_TYPES = ["Bar", "Line", "Scatter", "Pie", "Histogram"]

# =========================
# MAIN APP LOGIC
# =========================
if uploaded_file:
    try:
        df = pd.read_csv(uploaded_file) if uploaded_file.name.endswith(".csv") else pd.read_excel(uploaded_file)
        st.success("✅ File uploaded successfully!")

        # =========================
        # KPI CARDS
        # =========================
        graphs = conn.execute("SELECT id, name FROM graphs").fetchall()

        k1, k2, k3 = st.columns(3)

        with k1:
            st.markdown(f"<div class='metric-card'>📄 Rows<br><h2>{len(df)}</h2></div>", unsafe_allow_html=True)
        with k2:
            st.markdown(f"<div class='metric-card'>📊 Columns<br><h2>{len(df.columns)}</h2></div>", unsafe_allow_html=True)
        with k3:
            st.markdown(f"<div class='metric-card'>💾 Saved Charts<br><h2>{len(graphs)}</h2></div>", unsafe_allow_html=True)

        st.markdown("## 📁 Dataset Preview")
        with st.container():
            st.dataframe(df.head(), use_container_width=True)

        # =========================
        # SIDEBAR SELECTIONS
        # =========================
        with st.sidebar:
            chart_type = st.selectbox("📈 Chart Type", CHART_TYPES)

            numeric_cols = df.select_dtypes(include=["int64", "float64"]).columns
            all_cols = df.columns

            x_param = st.selectbox("🧭 X-axis", all_cols)
            y_param = st.selectbox("📊 Y-axis", numeric_cols if chart_type != "Histogram" else all_cols)

        # =========================
        # FILTERING
        # =========================
        st.markdown("## 🔍 Apply Filters")
        filters = {}
        filtered_df = df.copy()

        with st.expander("Click to Apply Filters"):
            for col in df.select_dtypes(include=["object", "category"]).columns:
                selected = st.multiselect(f"Filter by {col}", df[col].unique())
                if selected:
                    filters[col] = selected

        for col, vals in filters.items():
            filtered_df = filtered_df[filtered_df[col].isin(vals)]

        # =========================
        # CHART GENERATION
        # =========================
        st.markdown("## 📈 Generated Visualization")

        fig = None
        if chart_type == "Bar":
            fig = px.bar(filtered_df, x=x_param, y=y_param)
        elif chart_type == "Line":
            fig = px.line(filtered_df, x=x_param, y=y_param)
        elif chart_type == "Scatter":
            fig = px.scatter(filtered_df, x=x_param, y=y_param)
        elif chart_type == "Pie":
            fig = px.pie(filtered_df, names=x_param, values=y_param)
        elif chart_type == "Histogram":
            fig = px.histogram(filtered_df, x=x_param)

        if fig:
            with st.container():
                st.plotly_chart(fig, use_container_width=True)

        # =========================
        # ACTION BUTTONS
        # =========================
        excel_buf = io.BytesIO()
        filtered_df.to_excel(excel_buf, index=False)

        b1, b2, b3 = st.columns(3)

        with b1:
            save = st.button("💾 Save Chart", use_container_width=True)

        with b2:
            st.download_button(
                "⬇️ Export CSV",
                filtered_df.to_csv(index=False),
                "processed_data.csv",
                use_container_width=True
            )

        with b3:
            st.download_button(
                "⬇️ Export Excel",
                excel_buf.getvalue(),
                "processed_data.xlsx",
                use_container_width=True
            )

        if save:
            conn.execute(
                "INSERT INTO graphs (name, chart_type, x_param, y_param, filters) VALUES (?, ?, ?, ?, ?)",
                (
                    f"{chart_type} | {x_param} vs {y_param}",
                    chart_type,
                    x_param,
                    y_param,
                    json.dumps(filters)
                )
            )
            conn.commit()
            st.success("✅ Chart configuration saved!")

        # =========================
        # SAVED CHARTS PANEL
        # =========================
        st.markdown("## 🗂️ Saved Visualizations")

        graphs = conn.execute("SELECT id, name, chart_type, x_param, y_param, filters FROM graphs").fetchall()

        for graph_id, name, ctype, xval, yval, fjson in graphs:
            with st.container():
                panel1, panel2, panel3 = st.columns([6, 2, 2])
                panel1.markdown(f"**{name}**")

                with panel2:
                    if st.button("🔁 View", key=f"regen_{graph_id}", use_container_width=True):
                        temp_df = df.copy()
                        stored_filters = json.loads(fjson)
                        for col, vals in stored_filters.items():
                            temp_df = temp_df[temp_df[col].isin(vals)]

                        if ctype == "Bar":
                            fig = px.bar(temp_df, x=xval, y=yval)
                        elif ctype == "Line":
                            fig = px.line(temp_df, x=xval, y=yval)
                        elif ctype == "Scatter":
                            fig = px.scatter(temp_df, x=xval, y=yval)
                        elif ctype == "Pie":
                            fig = px.pie(temp_df, names=xval, values=yval)
                        elif ctype == "Histogram":
                            fig = px.histogram(temp_df, x=xval)

                        st.plotly_chart(fig, use_container_width=True)

                with panel3:
                    if st.button("🗑️ Delete", key=f"del_{graph_id}", use_container_width=True):
                        conn.execute("DELETE FROM graphs WHERE id=?", (graph_id,))
                        conn.commit()
                        st.experimental_rerun()

    except Exception as e:
        st.error(f"❌ Error: {e}")

else:
    st.info("⬅️ Upload a dataset from the sidebar to get started.")

conn.close()
