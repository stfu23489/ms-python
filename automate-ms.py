import subprocess
import datetime
import time
import os
import signal
import threading

CMD = ["npm", "run", "start"]
RUN_TIMES = ["12:00", "18:00"]
NO_LOG_TIMEOUT_MINUTES = 5

current_process = None
last_log_time = None
hang_monitor_stop = threading.Event()

def kill_process(proc):
    global current_process
    if proc and proc.poll() is None:
        try:
            proc.terminate()
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            os.kill(proc.pid, signal.SIGKILL)
        print(f"Killed process PID={proc.pid}")
    current_process = None

def hang_monitor():
    global current_process, last_log_time
    while not hang_monitor_stop.is_set():
        if current_process and current_process.poll() is None and last_log_time:
            elapsed = (datetime.datetime.now() - last_log_time).total_seconds()
            if elapsed > NO_LOG_TIMEOUT_MINUTES * 60:
                print(f"No log output for {NO_LOG_TIMEOUT_MINUTES} minutes, restarting process...")
                kill_process(current_process)
                run_npm()
                return
        time.sleep(60)

def run_npm():
    global current_process, last_log_time, hang_monitor_stop
    if current_process and current_process.poll() is None:
        print("Previous process still running, killing it before starting new one.")
        kill_process(current_process)
        hang_monitor_stop.set()

    print("Starting Microsoft Rewards Script...")

    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    env = os.environ.copy()
    env["FORCE_COLOR"] = "1"

    current_process = subprocess.Popen(
        CMD,
        startupinfo=startupinfo,
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        env=env
    )
    last_log_time = datetime.datetime.now()

    hang_monitor_stop.clear()
    threading.Thread(target=hang_monitor, daemon=True).start()

    for line in current_process.stdout:
        if line:
            last_log_time = datetime.datetime.now()
            print(line, end="")
            if "[ERROR]" in line:
                print("ERROR detected! Restarting process...")
                kill_process(current_process)
                hang_monitor_stop.set()
                return run_npm()

    print("Finished Microsoft Rewards Script.")
    hang_monitor_stop.set()

def main_loop():
    print("Scheduler started.")
    while True:
        now = datetime.datetime.now().strftime("%H:%M")
        if now in RUN_TIMES:
            run_npm()
        time.sleep(15 * 60)

if __name__ == "__main__":
    main_loop()
