import streamlit as st

st.set_page_config(page_title="Loan Miner GUI", layout="centered")
st.title("📥 Multi Loan Downloader Launcher")

import subprocess
import os
import threading
import queue
from streamlit_autorefresh import st_autorefresh

# ✅ Auto-refresh every 2 seconds
st_autorefresh(interval=2000, limit=None, key="refresh")

# Load EXE mappings
exe_file_path = "//192.168.0.88/Joel/Alvin/UAT/UAT/lenders.txt"
base_path = "//192.168.0.88/Joel/Alvin/UAT/UAT/"

exe_files = {}
if os.path.exists(exe_file_path):
    with open(exe_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if "=" in line:
                name, path = line.strip().split("=", 1)
                exe_files[name.strip()] = os.path.join(base_path, path.strip())
else:
    st.error(f"EXE config file not found: {exe_file_path}")

# Initialize session state
if "log_queues" not in st.session_state:
    st.session_state.log_queues = {}
if "status_dict" not in st.session_state:
    st.session_state.status_dict = {}
if "log_buffers" not in st.session_state:
    st.session_state.log_buffers = {}

# ✅ Lender selection
selected_miners = st.multiselect("✅ Select lenders to run", sorted(exe_files.keys()))
user_inputs = {}

# ✅ Display lender input fields in 2-column grid
input_cols = st.columns(2)
for idx, lender in enumerate(selected_miners):
    col = input_cols[idx % 2]
    with col:
        st.markdown(f"### {lender}")
        loan_number = st.text_input(f"Loan Number for {lender}", key=f"{lender}_loan")
        download_path = st.text_input(f"Download Path for {lender}", key=f"{lender}_path")
        auth_code = st.text_input(f"Auth Code for {lender}", key=f"{lender}_auth")
        action = st.radio(
            f"Select Action for {lender}",
            options=[("1", "Get Loan Officer Info"), ("2", "Download Loan Documents")],
            format_func=lambda x: x[1],
            key=f"{lender}_action"
        )
        user_inputs[lender] = {
            "loan_number": loan_number,
            "download_path": download_path,
            "action_code": action[0],
            "auth_code": auth_code
        }

# ✅ Threaded miner execution
def run_miner(lender, exe_path, loan_number, download_path, action_code, log_queue, status_dict):
    status_dict[lender] = "running"
    full_log = []

    try:
        process = subprocess.Popen(
            # [exe_path, download_path, loan_number, action_code],
            [exe_path, download_path, loan_number, action_code, user_inputs[lender]["auth_code"]],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for line in iter(process.stdout.readline, ''):
            line = line.strip()
            if line:
                full_log.append(line)
                log_queue.put(line)
        process.stdout.close()
        process.wait()
        msg = f"Miner {lender} finished with exit code {process.returncode}"
        full_log.append(msg)
        log_queue.put(msg)
        status_dict[lender] = "finished"
    except Exception as e:
        err_msg = f"Error in miner {lender}: {e}"
        full_log.append(err_msg)
        log_queue.put(err_msg)
        status_dict[lender] = "error"

    # ✅ Save logs to text file
    try:
        os.makedirs(download_path, exist_ok=True)
        log_file = os.path.join(download_path, f"{loan_number}_log.txt")
        with open(log_file, "w", encoding="utf-8") as f:
            f.write("\n".join(full_log))
    except Exception as e:
        log_queue.put(f"Failed to save log: {e}")

# ✅ Start button
if st.button("🚀 Start Miners"):
    for lender in selected_miners:
        loan_number = user_inputs[lender]["loan_number"]
        download_path = user_inputs[lender]["download_path"]
        if not loan_number or not download_path:
            st.warning(f"Please enter Loan Number and Download Path for {lender}")
            continue

        if lender not in st.session_state.log_queues:
            st.session_state.log_queues[lender] = queue.Queue()
        st.session_state.status_dict[lender] = "starting"

        t = threading.Thread(
            target=run_miner,
            args=(
                lender,
                exe_files[lender],
                loan_number,
                download_path,
                user_inputs[lender]["action_code"],
                st.session_state.log_queues[lender],
                st.session_state.status_dict
            ),
            daemon=True
        )
        t.start()

# ✅ Status icons
def get_status_icon(status):
    return {
        "running": "🟢 Running",
        "finished": "✅ Finished",
        "error": "🔴 Error",
        "starting": "🕓 Starting",
        "idle": "🕓 Idle"
    }.get(status, "❔ Unknown")

# ✅ Log/status display in 2-column layout with collapsible panels
log_cols = st.columns(2)

for idx, lender in enumerate(selected_miners):
    col = log_cols[idx % 2]
    with col:
        st.markdown(f"### {lender}")
        status = st.session_state.status_dict.get(lender, "idle")
        st.write(f"Status: **{get_status_icon(status)}**")

        q = st.session_state.log_queues.get(lender)
        if lender not in st.session_state.log_buffers:
            st.session_state.log_buffers[lender] = []

        buffer = st.session_state.log_buffers[lender]

        if q:
            while not q.empty():
                line = q.get()
                buffer.append(line)

        with st.expander("📄 View Log", expanded=False):
            if buffer:
                st.code("\n".join(buffer[-100:]), language="bash")
            else:
                st.text("No logs yet.")
