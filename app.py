import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import plotly.express as px
from datetime import datetime

# 1. Cấu hình trang
st.set_page_config(page_title="Bảng điều khiển Quản lý Công việc", layout="wide")
st.title("📊 Bảng điều khiển Quản lý Công việc")

# --- KHỞI TẠO BỘ NHỚ TẠM (SESSION STATE) ĐỂ LƯU VẾT CLICK ---
if "active_view" not in st.session_state:
    st.session_state.active_view = None
    st.session_state.dept_pts = []
    st.session_state.leader_pts = []

# 2. Kết nối Google Sheets và tải dữ liệu
conn = st.connection("gsheets", type=GSheetsConnection)
df = conn.read()

# 3. Làm sạch và xử lý dữ liệu
date_columns = ['Thời hạn hoàn thành', 'Ngày hiện tại', 'Ngày hoàn thành thực tế']
for col in date_columns:
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors='coerce')

# Tính toán Trạng thái
if 'Thời hạn còn lại' in df.columns:
    def get_status(days):
        if pd.isna(days): return "Không rõ"
        if isinstance(days, str):
            try:
                days = float(days)
            except ValueError:
                return "Bỏ qua/Văn bản"
        
        if days < 0: return "Quá hạn"
        elif days <= 3: return "Sắp đến hạn"
        else: return "Đúng tiến độ"
        
    df['Trạng thái'] = df['Thời hạn còn lại'].apply(get_status)

st.markdown("### 📋 Dữ liệu thô từ Google Sheets")
st.dataframe(df, use_container_width=True)

st.divider()

st.markdown("### 🎯 Tổng quan tình hình thực hiện")

# Lọc bỏ các dòng trắng hoặc dữ liệu không hợp lệ
df_valid = df[df['Trạng thái'] != "Bỏ qua/Văn bản"]

# Tính toán các con số
total_tasks = len(df_valid)
overdue_tasks = len(df_valid[df_valid['Trạng thái'] == "Quá hạn"])
due_soon_tasks = len(df_valid[df_valid['Trạng thái'] == "Sắp đến hạn"])
on_track_tasks = len(df_valid[df_valid['Trạng thái'] == "Đúng tiến độ"])

# Chia làm 4 cột bằng nhau
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

with kpi1:
    st.metric(label="Tổng số công việc", value=total_tasks)
with kpi2:
    st.metric(label="🟢 Đúng tiến độ", value=on_track_tasks)
with kpi3:
    st.metric(label="🟠 Sắp đến hạn", value=due_soon_tasks)
with kpi4:
    # Tham số delta giúp hiển thị mũi tên tăng/giảm. Ở đây ta có thể dùng nó để cảnh báo chữ đỏ
    st.metric(label="🔴 Quá hạn", value=overdue_tasks, delta="- Cần xử lý gấp", delta_color="inverse")

st.divider()

# 4. Vẽ biểu đồ
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 🏢 Công việc theo Đơn vị chủ trì")
    if 'Đơn vị chủ trì' in df.columns:
        dept_counts = df['Đơn vị chủ trì'].value_counts().reset_index()
        dept_counts.columns = ['Đơn vị chủ trì', 'Số lượng công việc']
        
        fig_bar = px.bar(
            dept_counts, 
            x='Đơn vị chủ trì', 
            y='Số lượng công việc',
            color='Đơn vị chủ trì',
            title="Nhấn vào cột của Đơn vị để xem chi tiết!"
        )
        fig_bar.update_xaxes(title_text=None)
        fig_bar.update_layout(showlegend=False) 
        
        dept_event = st.plotly_chart(fig_bar, use_container_width=True, on_select="rerun")

with col2:
    st.markdown("### 👤 Công việc theo Lãnh đạo phụ trách")
    if 'Lãnh đạo phụ trách' in df.columns and 'Trạng thái' in df.columns:
        df_valid = df[df['Trạng thái'] != "Bỏ qua/Văn bản"]
        leader_status_counts = df_valid.groupby(['Lãnh đạo phụ trách', 'Trạng thái']).size().reset_index(name='Số lượng công việc')
        
        fig_bar_leader = px.bar(
            leader_status_counts, 
            x='Lãnh đạo phụ trách', 
            y='Số lượng công việc',
            color='Trạng thái',
            title="Nhấn vào cột của Lãnh đạo để xem chi tiết!",
            barmode='stack',
            color_discrete_map={
                'Quá hạn': '#EF4444', 
                'Sắp đến hạn': '#F59E0B', 
                'Đúng tiến độ': '#10B981', 
                'Không rõ': '#9CA3AF'
            }
        )
        fig_bar_leader.update_xaxes(title_text=None)
        leader_event = st.plotly_chart(fig_bar_leader, use_container_width=True, on_select="rerun")


# --- XỬ LÝ SỰ KIỆN CLICK THÔNG MINH (SỬA LỖI KHÔNG HIỆN BẢNG) ---
cur_dept = dept_event.selection.points if ('dept_event' in locals() and dept_event) else []
cur_leader = leader_event.selection.points if ('leader_event' in locals() and leader_event) else []

# Kiểm tra xem có click mới vào biểu đồ Đơn vị không
if cur_dept != st.session_state.dept_pts:
    st.session_state.dept_pts = cur_dept
    if len(cur_dept) > 0:
        st.session_state.active_view = "dept"
    elif st.session_state.active_view == "dept":
        st.session_state.active_view = None

# Kiểm tra xem có click mới vào biểu đồ Lãnh đạo không
if cur_leader != st.session_state.leader_pts:
    st.session_state.leader_pts = cur_leader
    if len(cur_leader) > 0:
        st.session_state.active_view = "leader"
    elif st.session_state.active_view == "leader":
        st.session_state.active_view = None

# --- HIỂN THỊ BẢNG DỮ LIỆU DUY NHẤT ---
if st.session_state.active_view == "dept":
    selected_dept = st.session_state.dept_pts[0]["x"]
    st.markdown(f"#### 📋 Chi tiết các nhiệm vụ do **{selected_dept}** chủ trì:")
    
    filtered_df_to_show = df[df['Đơn vị chủ trì'] == selected_dept]
    display_cols = ['Nội dung công việc', 'Lãnh đạo phụ trách', 'Chuyên viên tham mưu trực tiếp', 'Trạng thái', 'Thời hạn hoàn thành']
    
    existing_cols = [col for col in display_cols if col in filtered_df_to_show.columns]
    styled_df = filtered_df_to_show[existing_cols].copy()
    if 'Thời hạn hoàn thành' in styled_df.columns:
        styled_df['Thời hạn hoàn thành'] = styled_df['Thời hạn hoàn thành'].dt.strftime('%d/%m/%Y')
        
    st.dataframe(styled_df, use_container_width=True, column_config={"Nội dung công việc": st.column_config.TextColumn("Nội dung công việc", width="large")})

elif st.session_state.active_view == "leader":
    selected_leader = st.session_state.leader_pts[0]["x"]
    st.markdown(f"#### 📋 Chi tiết các nhiệm vụ do Lãnh đạo **{selected_leader}** phụ trách:")
    
    filtered_df_to_show = df[df['Lãnh đạo phụ trách'] == selected_leader]
    display_cols = ['Nội dung công việc', 'Đơn vị chủ trì', 'Chuyên viên tham mưu trực tiếp', 'Trạng thái', 'Thời hạn hoàn thành']
    
    existing_cols = [col for col in display_cols if col in filtered_df_to_show.columns]
    styled_df = filtered_df_to_show[existing_cols].copy()
    if 'Thời hạn hoàn thành' in styled_df.columns:
        styled_df['Thời hạn hoàn thành'] = styled_df['Thời hạn hoàn thành'].dt.strftime('%d/%m/%Y')
        
    st.dataframe(styled_df, use_container_width=True, column_config={"Nội dung công việc": st.column_config.TextColumn("Nội dung công việc", width="large")})

else:
    st.info("👆 Nhấn vào một cột trong bất kỳ biểu đồ nào ở trên để xem danh sách công việc chi tiết tại đây (Nhấn lại vào nền trống của biểu đồ để bỏ chọn).")


st.divider()

# --- BIỂU ĐỒ TRẠNG THÁI VÀ CHI TIẾT THEO TRẠNG THÁI ---
col3, col4 = st.columns(2)
with col3:
    st.markdown("### ⏳ Trạng thái Công việc (Số ngày còn lại)")
    if 'Trạng thái' in df.columns:
        df_chart = df[df['Trạng thái'] != "Bỏ qua/Văn bản"]
        status_counts = df_chart['Trạng thái'].value_counts().reset_index()
        status_counts.columns = ['Trạng thái', 'Số lượng']
        
        fig_status = px.bar(
            status_counts, 
            x='Trạng thái', 
            y='Số lượng',
            title="Tổng quan trạng thái (Nhấn vào cột!)",
            color='Trạng thái',
            color_discrete_map={
                'Quá hạn': '#EF4444', 
                'Sắp đến hạn': '#F59E0B', 
                'Đúng tiến độ': '#10B981',
                'Không rõ': '#9CA3AF'
            }
        )
        fig_status.update_xaxes(title_text=None)
        fig_status.update_layout(showlegend=False)
        
        status_event = st.plotly_chart(fig_status, use_container_width=True, on_select="rerun")

with col4:
    if status_event and len(status_event.selection.points) > 0:
        selected_status = status_event.selection.points[0]["x"]
        st.markdown(f"### 🔍 Chi tiết công việc: **{selected_status}**")
        
        filtered_df = df[df['Trạng thái'] == selected_status]
        
        display_columns = ['Nội dung công việc', 'Lãnh đạo phụ trách', 'Chuyên viên tham mưu trực tiếp', 'Thời hạn hoàn thành', 'Thời hạn còn lại']
        existing_cols = [col for col in display_columns if col in filtered_df.columns]
        
        styled_df = filtered_df[existing_cols].copy()
        if 'Thời hạn hoàn thành' in styled_df.columns:
            styled_df['Thời hạn hoàn thành'] = styled_df['Thời hạn hoàn thành'].dt.strftime('%d/%m/%Y')
            
        st.dataframe(styled_df, use_container_width=True, column_config={"Nội dung công việc": st.column_config.TextColumn("Nội dung công việc", width="large")})
    else:
        st.info("👈 Nhấn trực tiếp vào một cột màu trong biểu đồ Trạng thái bên trái để xem chi tiết các công việc tại đây.")

st.divider()

# 5. Gantt Chart / Project Timeline
st.markdown("### 📅 Tiến độ công việc")
if 'Nội dung công việc' in df.columns and 'Ngày hiện tại' in df.columns and 'Thời hạn hoàn thành' in df.columns:
    timeline_df = df.dropna(subset=['Ngày hiện tại', 'Thời hạn hoàn thành']).copy()
    
    # Rút gọn tên công việc (cắt ở 60 ký tự) để trục Y không bị phình to
    timeline_df['Tên hiển thị'] = timeline_df['Nội dung công việc'].apply(
        lambda x: (str(x)[:60] + '...') if len(str(x)) > 60 else str(x)
    )
    
    fig_gantt = px.timeline(
        timeline_df, 
        x_start="Ngày hiện tại", 
        x_end="Thời hạn hoàn thành", 
        y="Tên hiển thị", # Sử dụng cột đã rút gọn cho trục Y
        color="Chuyên viên tham mưu trực tiếp",
        title="Thời hạn công việc và Người phụ trách",
        # Cấu hình hover: Hiện full text, ẩn text rút gọn
        hover_data={"Nội dung công việc": True, "Tên hiển thị": False} 
    )
    fig_gantt.update_yaxes(autorange="reversed") 
    
    # Thiết lập layout để tối ưu không gian hiển thị thanh thời gian
    fig_gantt.update_layout(
        yaxis_title=None, # Ẩn chữ "Tên hiển thị" bên lề cho đỡ rối
        margin=dict(l=10, r=20, t=40, b=20)
    )
    
    st.plotly_chart(fig_gantt, use_container_width=True)