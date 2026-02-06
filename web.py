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
        elif c
