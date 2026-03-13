import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Page Configuration
st.set_page_config(page_title="Task Manager Dashboard", layout="wide")
st.title("📊 Task Management Dashboard")

# 2. Connect to Google Sheets and load data
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()

# 3. Clean and process data
# Ensure dates are treated as datetime objects
date_columns = ['Thời hạn hoàn thành', 'Ngày hiện tại', 'Ngày hoàn thành thực tế']
for col in date_columns:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

st.markdown("### 📋 Raw Data from Google Sheets")
st.dataframe(df) # Display the table on the website

st.divider()

# 4. Draw Diagrams

col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🏢 Tasks by Lead Department")
    if 'Đơn vị chủ trì' in df.columns:
        # Count tasks per department
        dept_counts = df['Đơn vị chủ trì'].value_counts().reset_index()
        dept_counts.columns = ['Đơn vị chủ trì', 'Số lượng công việc']
        
        # Draw Bar Chart
        fig_bar = px.bar(
            dept_counts, 
            x='Đơn vị chủ trì', 
            y='Số lượng công việc',
            color='Đơn vị chủ trì',
            title="Workload per Department"
        )
        fig_bar.update_xaxes(title_text=None)
        st.plotly_chart(fig_bar, use_container_width=True)

with col2:
    st.markdown("### 🏢 Tasks by Leader")
    if 'Lãnh đạo phụ trách' in df.columns:
        # Count tasks per department
        dept_counts = df['Lãnh đạo phụ trách'].value_counts().reset_index()
        dept_counts.columns = ['Lãnh đạo phụ trách', 'Số lượng công việc']
        
        # Draw Bar Chart
        fig_bar = px.bar(
            dept_counts, 
            x='Lãnh đạo phụ trách', 
            y='Số lượng công việc',
            color='Lãnh đạo phụ trách',
            title="Workload per Department"
        )
        fig_bar.update_xaxes(title_text=None)
        st.plotly_chart(fig_bar, use_container_width=True)

# --- NEW SECTION: Show Details Below the Charts ---
st.divider()

col3, col4 = st.columns(2)
with col3:
    st.markdown("### ⏳ Task Status (Days Remaining)")
    if 'Thời hạn còn lại' in df.columns:
        
        def get_status(days):
            if pd.isna(days): return "Unknown"
            if isinstance(days, str):
                try:
                    days = float(days)
                except ValueError:
                    return "Text/Skipped"
            
            if days < 0: return "Overdue"
            elif days <= 3: return "Due Soon"
            else: return "On Track"
            
        df['Trạng thái'] = df['Thời hạn còn lại'].apply(get_status)
        df_chart = df[df['Trạng thái'] != "Text/Skipped"]
        
        status_counts = df_chart['Trạng thái'].value_counts().reset_index()
        status_counts.columns = ['Trạng thái', 'Số lượng']
        
        # --- CHANGED: Use a Bar Chart instead of Pie so clicking works! ---
        fig_status = px.bar(
            status_counts, 
            x='Trạng thái', 
            y='Số lượng',
            title="Overall Task Status (Click a bar!)",
            color='Trạng thái',
            color_discrete_map={
                'Overdue':'red', 
                'Due Soon':'orange', 
                'On Track':'green',
                'Unknown':'gray'
            }
        )
        
        # Capture the click event. This works flawlessly on Bar charts.
        status_event = st.plotly_chart(fig_status, use_container_width=True, on_select="rerun")

# 1. (Optional) Uncomment the line below if you ever need to debug and see exactly what the click sends!
# st.write(pie_event.selection) 

# 2. Check if the user clicked on a slice
with col4:
    if status_event and len(status_event.selection.points) > 0:
        
        # For Bar charts, Plotly returns the clicked category perfectly in the "x" key!
        selected_status = status_event.selection.points[0]["x"]
        
        st.markdown(f"### 🔍 Detailed Tasks: **{selected_status}**")
        
        # Filter the dataframe
        filtered_df = df[df['Trạng thái'] == selected_status]
        
        display_columns = [
            'Nội dung công việc', 
            'Lãnh đạo phụ trách',
            'Chuyên viên tham mưu trực tiếp', 
            'Thời hạn hoàn thành', 
            'Thời hạn còn lại'
        ]
        
        existing_cols = [col for col in display_columns if col in filtered_df.columns]
        
        st.dataframe(filtered_df[existing_cols], use_container_width=True)
    else:
        st.info("👈 Click directly on a colored bar in the Task Status chart left to see the specific tasks here.")


st.divider()

# 5. Gantt Chart / Project Timeline
st.markdown("### 📅 Project Timeline")
if 'Nội dung công việc' in df.columns and 'Ngày hiện tại' in df.columns and 'Thời hạn hoàn thành' in df.columns:
    # Filter out rows missing essential date data
    timeline_df = df.dropna(subset=['Ngày hiện tại', 'Thời hạn hoàn thành'])
    
    fig_gantt = px.timeline(
        timeline_df, 
        x_start="Ngày hiện tại", 
        x_end="Thời hạn hoàn thành", 
        y="Thời hạn còn lại",
        color="Chuyên viên tham mưu trực tiếp",
        title="Task Deadlines and Assignees"
    )
    fig_gantt.update_yaxes(autorange="reversed") # Standard Gantt chart format (top to bottom)
    st.plotly_chart(fig_gantt, use_container_width=True)