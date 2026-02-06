import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import json
from github import Github # Thư viện kết nối GitHub

# --- CẤU HÌNH ---
st.set_page_config(page_title="GPA Cloud Sync", layout="wide", page_icon="☁️")
DATA_FILE = "data.json" # Tên file sẽ lưu trên GitHub

# --- KẾT NỐI GITHUB ---
def get_repo():
    # Lấy token từ Streamlit Secrets
    token = st.secrets["GITHUB_TOKEN"]
    repo_name = st.secrets["REPO_NAME"]
    g = Github(token)
    return g.get_repo(repo_name)

def load_data_from_github():
    try:
        repo = get_repo()
        # Tìm file data.json
        contents = repo.get_contents(DATA_FILE)
        json_str = contents.decoded_content.decode()
        data = json.loads(json_str)
        
        manager = GPAManager()
        for d in data:
            manager.add_subject(d['code'], d['name'], d['semester'], d['credits'], d['score_10'])
        return manager
    except Exception as e:
        # Nếu chưa có file hoặc lỗi, trả về manager rỗng
        return GPAManager()

def save_data_to_github():
    try:
        repo = get_repo()
        # Chuyển dữ liệu thành chuỗi JSON
        json_str = json.dumps([s.to_dict() for s in st.session_state.manager.subjects], ensure_ascii=False, indent=2)
        
        try:
            # Thử lấy file cũ để update
            contents = repo.get_contents(DATA_FILE)
            repo.update_file(contents.path, "Update GPA Data (Auto)", json_str, contents.sha)
            st.toast("✅ Đã lưu lên Đám Mây GitHub!", icon="☁️")
        except:
            # Nếu chưa có file thì tạo mới
            repo.create_file(DATA_FILE, "Init GPA Data", json_str)
            st.toast("✅ Đã tạo file dữ liệu mới!", icon="☁️")
    except Exception as e:
        st.error(f"Lỗi lưu GitHub: {e}")

# --- BACKEND (LOGIC CŨ) ---
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
    def __init__(self):
        self.subjects = []
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

# --- KHỞI TẠO DỮ LIỆU TỪ GITHUB ---
if 'manager' not in st.session_state:
    with st.spinner("Đang tải dữ liệu từ Đám Mây..."):
        st.session_state.manager = load_data_from_github()

# --- GIAO DIỆN ---
st.title("☁️ GPA Manager - Lưu Trữ Đám Mây")

with st.sidebar:
    st.header("Hệ Thống")
    if st.button("🔄 Đồng Bộ Ngay (Tải lại)", type="primary"):
        st.session_state.manager = load_data_from_github()
        st.rerun()
    st.info("Dữ liệu được lưu trực tiếp vào file `data.json` trên GitHub của bạn. Không bao giờ mất!")

tab1, tab2, tab3 = st.tabs(["1. Dữ Liệu", "2. Chi Tiết", "3. Biểu Đồ"])

with tab1:
    with st.container(border=True):
        st.subheader("Thông Tin Môn Học")
        
        # Tìm kiếm
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
        
        # Form
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

        b1, b2, b3, b4 = st.columns(4)
        if b1.button("Thêm", use_container_width=True):
            if code:
                st.session_state.manager.add_subject(code, name, sem, cred, score)
                save_data_to_github() # LƯU LÊN CLOUD
                st.rerun()
        if b2.button("Sửa", use_container_width=True):
            st.session_state.manager.update_subject(code, name, sem, cred, score)
            save_data_to_github() # LƯU LÊN CLOUD
            st.rerun()
        if b3.button("Xóa", use_container_width=True):
            st.session_state.manager.delete_subject(code, sem)
            save_data_to_github() # LƯU LÊN CLOUD
            st.rerun()
        if b4.button("Clear", use_container_width=True):
            st.session_state.k_code = ""; st.session_state.k_name = ""; st.session_state.k_score = 0.0
            st.rerun()

    # Table
    table_data = []
    for sub in st.session_state.manager.subjects:
        note = st.session_state.manager.get_comparison_note(sub)
        table_data.append({"HK": sub.semester, "Mã": sub.code, "Tên": f"{sub.name}{note}", "TC": sub.credits, "Điểm": sub.score_10, "Chữ": sub.score_char})
    if table_data:
        st.dataframe(pd.DataFrame(table_data).sort_values("HK"), use_container_width=True, hide_index=True)
    
    accum, cpa = st.session_state.manager.calculate_cpa()
    st.divider()
    m1, m2 = st.columns(2)
    m1.metric("CPA Tích Lũy", f"{cpa:.2f}")
    m2.metric("Tín Chỉ Tích Lũy", f"{accum}")

with tab2:
    sem_data = st.session_state.manager.get_sem_data()
    for sem, subs in sem_data.items():
        tc = sum(s.credits for s in subs)
        gpa = sum(s.score_4 * s.credits for s in subs)/tc if tc>0 else 0
        with st.expander(f"Học Kỳ {sem} (GPA: {gpa:.2f})", expanded=True):
            st.dataframe(pd.DataFrame([s.to_dict() for s in subs]), use_container_width=True)

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
