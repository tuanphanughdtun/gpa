import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
from github import Github

# --- CẤU HÌNH ---
st.set_page_config(page_title="GPA Cloud Manager", layout="wide", page_icon="🎓")
DATA_FILE = "data.json"

# --- CSS: CĂN TRÁI CHO SỐ VÀ BẢNG ---
st.markdown("""
<style>
    /* Căn trái chữ số bên trong ô nhập liệu */
    input[inputmode="decimal"] { text-align: left !important; }
    input[type="number"] { text-align: left !important; }
    /* Căn trái tiêu đề và nội dung bảng */
    th { text-align: left !important; }
    td { text-align: left !important; }
</style>
""", unsafe_allow_html=True)

# --- KẾT NỐI GITHUB ---
def get_repo():
    token = st.secrets["GITHUB_TOKEN"]
    repo_name = st.secrets["REPO_NAME"]
    g = Github(token)
    return g.get_repo(repo_name)

def load_full_database():
    try:
        repo = get_repo()
        contents = repo.get_contents(DATA_FILE)
        json_str = contents.decoded_content.decode()
        data = json.loads(json_str)
        if isinstance(data, list): return {"DEFAULT": data}
        return data
    except: return {}

def save_current_student_to_github(student_id):
    try:
        repo = get_repo()
        full_data = load_full_database()
        current_student_data = [s.to_dict() for s in st.session_state.manager.subjects]
        full_data[student_id] = current_student_data
        json_str = json.dumps(full_data, ensure_ascii=False, indent=2)
        try:
            contents = repo.get_contents(DATA_FILE)
            repo.update_file(contents.path, f"Update {student_id}", json_str, contents.sha)
            st.toast(f"✅ Đã lưu: {student_id}!", icon="☁️")
        except:
            repo.create_file(DATA_FILE, "Init DB", json_str)
            st.toast("✅ Đã tạo file mới!", icon="☁️")
    except Exception as e: st.error(f"Lỗi GitHub: {e}")

# --- BACKEND ---
class Subject:
    def __init__(self, code, name, semester, credits, score_10):
        self.code = code.strip().upper()
        self.name = name.strip()
        self.semester = semester.strip()
        self.credits = int(credits)
        self.score_10 = float(score_10)
        self.score_char, self.score_4 = self.convert_score(self.score_10)
    def convert_score(self, s10):
        if s10 >= 8.5: return 'A', 4.0
        elif s10 >= 8.0: return 'B+', 3.5
        elif s10 >= 7.0: return 'B', 3.0
        elif s10 >= 6.5: return 'C+', 2.5
        elif s10 >= 5.5: return 'C', 2.0
        elif s10 >= 5.0: return 'D+', 1.5
        elif s10 >= 4.0: return 'D', 1.0
        else: return 'F', 0.0
    def to_dict(self):
        return {"code": self.code, "name": self.name, "semester": self.semester, "credits": self.credits, "score_10": self.score_10}

class GPAManager:
    def __init__(self): self.subjects = []
    def add_subject(self, code, name, semester, credits, score_10):
        self.subjects.append(Subject(code, name, semester, credits, score_10))
    def update_subject(self, code, name, semester, credits, score_10):
        for i, sub in enumerate(self.subjects):
            if sub.code == code and sub.semester == semester:
                self.subjects[i] = Subject(code, name, semester, credits, score_10)
                break
    def delete_subject(self, code, semester):
        self.subjects = [s for s in self.subjects if not (s.code == code and s.semester == semester)]
    def calculate_cpa(self):
        best_map = {}
        for sub in self.subjects:
            if sub.code not in best_map: best_map[sub.code] = sub
            else:
                if sub.score_10 > best_map[sub.code].score_10: best_map[sub.code] = sub
        final = list(best_map.values())
        if not final: return 0, 0.0
        tc = sum(s.credits for s in final)
        if tc == 0: return 0, 0.0
        return tc, sum(s.score_4 * s.credits for s in final) / tc
    
    def get_rank(self, cpa):
        if cpa >= 3.6: return "Xuất sắc"
        elif cpa >= 3.2: return "Giỏi"
        elif cpa >= 2.5: return "Khá"
        elif cpa >= 2.0: return "Trung bình"
        else: return "Yếu"

    def get_comparison_note(self, current_sub):
        duplicates = [s for s in self.subjects if s.code == current_sub.code and s is not current_sub]
        notes = []
        for other in duplicates:
            if current_sub.score_10 > other.score_10: notes.append(f"Cao hơn HK {other.semester}")
            elif current_sub.score_10 < other.score_10: notes.append(f"Thấp hơn HK {other.semester}")
        return f" ({', '.join(notes)})" if notes else ""
    def get_sem_data(self):
        sem_dict = {}
        for sub in self.subjects:
            if sub.semester not in sem_dict: sem_dict[sub.semester] = []
            sem_dict[sub.semester].append(sub)
        return dict(sorted(sem_dict.items()))

# --- GIAO DIỆN CHÍNH ---
st.title("🎓 GPA Manager - Multi User")

with st.sidebar:
    st.header("🔑 Đăng Nhập")
    student_id = st.text_input("Nhập Mã Số SV / ID:", key="student_id_input", placeholder="VD: 2021001")
    st.divider()
    st.header("Hệ Thống")
    if student_id:
        if st.button("🔄 Đồng Bộ (Tải lại)", type="primary"):
            if 'full_db' in st.session_state: del st.session_state.full_db
            st.rerun()
        st.success(f"User: **{student_id}**")
    else: st.warning("Nhập ID để xem.")

if not student_id:
    st.info("👈 Vui lòng nhập **Mã Số Sinh Viên (ID)** ở thanh bên trái.")
    st.stop()

# Load Data
if 'manager' not in st.session_state or st.session_state.get('current_id') != student_id:
    with st.spinner(f"Đang tải {student_id}..."):
        full_db = load_full_database()
        st.session_state.full_db = full_db
        manager = GPAManager()
        student_data = full_db.get(student_id, [])
        for d in student_data: manager.add_subject(d['code'], d['name'], d['semester'], d['credits'], d['score_10'])
        st.session_state.manager = manager
        st.session_state.current_id = student_id

tab1, tab2, tab3 = st.tabs(["1. Dữ Liệu", "2. Chi Tiết", "3. Biểu Đồ"])

with tab1:
    with st.container(border=True):
        st.subheader(f"Thông Tin Môn Học ({student_id})")

        # [QUAN TRỌNG] CHUẨN BỊ DỮ LIỆU BẢNG TRƯỚC
        table_data = []
        for sub in st.session_state.manager.subjects:
            note = st.session_state.manager.get_comparison_note(sub)
            table_data.append({
                "HK": sub.semester, 
                "Mã": sub.code, 
                "Tên": f"{sub.name}{note}", 
                "TC": str(sub.credits), 
                "Điểm (10)": f"{sub.score_10:.1f}", 
                "Điểm (4)": f"{sub.score_4:.1f}", 
                "Chữ": sub.score_char
            })
        
        # [FIX LỖI KEYERROR] CHỈ TẠO DATAFRAME KHI CÓ DỮ LIỆU
        if table_data:
            df = pd.DataFrame(table_data).sort_values("HK")
        else:
            df = pd.DataFrame() # Tạo bảng rỗng nếu chưa có dữ liệu

        # [QUAN TRỌNG] XỬ LÝ CLICK BẢNG TẠI ĐÂY (TRƯỚC KHI VẼ FORM)
        if not df.empty and "main_table_key" in st.session_state:
            selection = st.session_state.main_table_key.get("selection", {})
            if selection and "rows" in selection and len(selection["rows"]) > 0:
                selected_idx = selection["rows"][0]
                
                if "last_selected_idx" not in st.session_state:
                    st.session_state.last_selected_idx = -1
                
                if selected_idx != st.session_state.last_selected_idx:
                    row_data = df.iloc[selected_idx]
                    sel_code = row_data["Mã"]
                    sel_sem = row_data["HK"]
                    
                    found_sub = None
                    for s in st.session_state.manager.subjects:
                        if s.code == sel_code and s.semester == sel_sem:
                            found_sub = s; break
                    
                    if found_sub:
                        st.session_state.k_sem = found_sub.semester
                        st.session_state.k_code = found_sub.code
                        st.session_state.k_name = found_sub.name
                        st.session_state.k_cred = found_sub.credits
                        st.session_state.k_score = found_sub.score_10
                        st.session_state.last_selected_idx = selected_idx
                        st.rerun()

        # --- PHẦN VẼ FORM NHẬP LIỆU ---
        c_s1, c_s2 = st.columns([3,1])
        with c_s1: search_q = st.text_input("Tìm kiếm môn:", key="search_q")
        with c_s2: 
            st.write("")
            st.write("")
            if st.button("Tìm & Điền", use_container_width=True):
                found = None
                for sub in st.session_state.manager.subjects:
                    if search_q.lower() in sub.code.lower() or search_q.lower() in sub.name.lower():
                        found = sub; break
                if found:
                    st.session_state.k_sem = found.semester
                    st.session_state.k_code = found.code
                    st.session_state.k_name = found.name
                    st.session_state.k_cred = found.credits
                    st.session_state.k_score = found.score_10
                    st.rerun()
        
        # Init state
        if 'k_sem' not in st.session_state: st.session_state.k_sem = ""
        if 'k_code' not in st.session_state: st.session_state.k_code = ""
        if 'k_name' not in st.session_state: st.session_state.k_name = ""
        if 'k_cred' not in st.session_state: st.session_state.k_cred = 3
        if 'k_score' not in st.session_state: st.session_state.k_score = 0.0

        c1, c2, c3, c4, c5 = st.columns([1,1,2,1,1])
        with c1: sem = st.text_input("Mã HK", key="k_sem")
        with c2: code = st.text_input("Mã Môn", key="k_code")
        with c3: name = st.text_input("Tên Môn", key="k_name")
        with c4: cred = st.number_input("TC", 1, 20, key="k_cred")
        with c5: score = st.number_input("Điểm", 0.0, 10.0, step=0.1, key="k_score")

        b1, b2, b3 = st.columns(3)
        if b1.button("Thêm", use_container_width=True):
            if code:
                st.session_state.manager.add_subject(code, name, sem, cred, score)
                save_current_student_to_github(student_id); st.rerun()
        if b2.button("Sửa", use_container_width=True):
            st.session_state.manager.update_subject(code, name, sem, cred, score)
            save_current_student_to_github(student_id); st.rerun()
        if b3.button("Xóa", use_container_width=True):
            st.session_state.manager.delete_subject(code, sem)
            save_current_student_to_github(student_id); st.rerun()

    # --- VẼ BẢNG DỮ LIỆU ---
    if not df.empty:
        st.dataframe(
            df.style.set_properties(**{'text-align': 'left'}),
            use_container_width=True, 
            hide_index=True,
            on_select="rerun",
            selection_mode="single-row",
            key="main_table_key"
        )
    else: st.info("Chưa có dữ liệu.")
    
    accum, cpa = st.session_state.manager.calculate_cpa()
    rank = st.session_state.manager.get_rank(cpa)
    
    st.divider()
    m1, m2, m3 = st.columns(3)
    m1.metric("GPA Tích Lũy", f"{cpa:.2f}")
    m2.metric("Xếp Loại", f"{rank}", delta_color="off")
    m3.metric("Tín Chỉ Tích Lũy", f"{accum}")

with tab2:
    sem_data = st.session_state.manager.get_sem_data()
    for sem, subs in sem_data.items():
        tc = sum(s.credits for s in subs)
        gpa = sum(s.score_4 * s.credits for s in subs)/tc if tc>0 else 0
        rank_sem = st.session_state.manager.get_rank(gpa)
        
        with st.expander(f"Học Kỳ {sem} (GPA: {gpa:.2f} - {rank_sem})", expanded=True):
            sem_table_data = []
            for s in subs:
                note = st.session_state.manager.get_comparison_note(s)
                sem_table_data.append({
                    "Mã": s.code,
                    "Tên": f"{s.name}{note}",
                    "TC": str(s.credits),
                    "Điểm (10)": f"{s.score_10:.1f}",
                    "Điểm (4)": f"{s.score_4:.1f}",
                    "Chữ": s.score_char
                })
            
            df_sem = pd.DataFrame(sem_table_data)
            st.dataframe(
                df_sem.style.set_properties(**{'text-align': 'left'}),
                use_container_width=True, hide_index=True
            )

with tab3:
    sem_data = st.session_state.manager.get_sem_data()
    if sem_data:
        sems, gpas = [], []
        for sem, subs in sem_data.items():
            tc = sum(s.credits for s in subs)
            gpas.append(sum(s.score_4 * s.credits for s in subs)/tc if tc>0 else 0)
            sems.append(sem)
        fig, ax = plt.subplots(figsize=(10, 4))
        ax.plot(sems, gpas, 'o-', color='green'); ax.set_ylim(0, 4); ax.grid(True, linestyle='--')
        for i, v in enumerate(gpas): ax.text(i, v+0.1, f"{v:.2f}", ha='center')
        st.pyplot(fig)
