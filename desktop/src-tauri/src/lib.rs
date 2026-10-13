use serde::{Deserialize, Serialize};
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::Arc;
use tauri::{AppHandle, Emitter, State};
use tokio::io::{AsyncBufReadExt, BufReader};
use tokio::process::Command as TokioCommand;
use tokio::sync::Mutex;

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TranslationParams {
    pub file: String,
    pub lang_in: String,
    pub lang_out: String,
    pub service: String,
    pub pages: Option<Vec<u32>>,
    pub output_dir: Option<String>,
    pub envs: Option<HashMap<String, String>>,
    pub prompt: Option<String>,
    pub thread: Option<u32>,
    pub export_format: Option<String>,
    pub ignore_cache: Option<bool>,
}

#[derive(Default)]
pub struct AppState {
    pub current_pid: Arc<Mutex<Option<u32>>>,
}

fn get_project_root() -> PathBuf {
    // 1. Check from current working directory (walking up)
    if let Ok(mut current) = std::env::current_dir() {
        for _ in 0..7 {
            if current.join(".venv").join("Scripts").join("python.exe").exists()
                || current.join(".venv").join("bin").join("python").exists()
            {
                return current;
            }
            if !current.pop() {
                break;
            }
        }
    }

    // 2. Check from current executable directory (walking up)
    if let Ok(exe_path) = std::env::current_exe() {
        let mut current = exe_path;
        for _ in 0..7 {
            if current.join(".venv").join("Scripts").join("python.exe").exists()
                || current.join(".venv").join("bin").join("python").exists()
            {
                return current;
            }
            if !current.pop() {
                break;
            }
        }
    }

    // 3. Fallback
    PathBuf::from(".")
}

fn get_python_executable() -> PathBuf {
    let root = get_project_root();
    let venv_python_win = root.join(".venv").join("Scripts").join("python.exe");
    if venv_python_win.exists() {
        return venv_python_win;
    }
    let venv_python_unix = root.join(".venv").join("bin").join("python");
    if venv_python_unix.exists() {
        return venv_python_unix;
    }
    PathBuf::from("python")
}

#[tauri::command]
async fn get_system_status() -> Result<serde_json::Value, String> {
    let root = get_project_root();
    let python = get_python_executable();
    let venv_ready = python.exists();

    Ok(serde_json::json!({
        "project_root": root.to_string_lossy().to_string(),
        "python_path": python.to_string_lossy().to_string(),
        "venv_ready": venv_ready
    }))
}

#[tauri::command]
async fn start_translation(
    params: TranslationParams,
    app_handle: AppHandle,
    state: State<'_, AppState>,
) -> Result<(), String> {
    let root = get_project_root();
    let python = get_python_executable();

    if !python.exists() && python == PathBuf::from("python") {
        return Err("Không tìm thấy môi trường ảo Python .venv. Vui lòng kiểm tra lại!".into());
    }

    let mut output_dir = params.output_dir.clone().unwrap_or_default();
    if output_dir.trim().is_empty() {
        output_dir = root.join("pdf2zh_desktop_output").to_string_lossy().to_string();
    }

    let request_json = serde_json::json!({
        "action": "translate",
        "file": params.file,
        "lang_in": params.lang_in,
        "lang_out": params.lang_out,
        "service": params.service,
        "pages": params.pages,
        "output_dir": output_dir,
        "envs": params.envs.unwrap_or_default(),
        "prompt": params.prompt,
        "thread": params.thread.unwrap_or(4),
        "export_format": params.export_format.unwrap_or_else(|| "both".into()),
        "ignore_cache": params.ignore_cache.unwrap_or(false),
    });

    let json_str = serde_json::to_string(&request_json).map_err(|e| e.to_string())?;

    let mut cmd = TokioCommand::new(python);
    cmd.current_dir(&root);
    cmd.env("PYTHONIOENCODING", "utf-8");
    cmd.env("PYTHONUTF8", "1");
    cmd.env("PYTHONUNBUFFERED", "1");
    cmd.args(["-m", "pdf2zh.ipc_worker"]);
    cmd.stdin(Stdio::piped());
    cmd.stdout(Stdio::piped());
    cmd.stderr(Stdio::piped());

    #[cfg(windows)]
    {
        // CREATE_NO_WINDOW flag on Windows
        cmd.creation_flags(0x08000000);
    }

    let mut child = cmd.spawn().map_err(|e| format!("Không thể khởi chạy worker: {}", e))?;

    if let Some(pid) = child.id() {
        let mut p = state.current_pid.lock().await;
        *p = Some(pid);
    }

    // Write JSON input to child stdin
    if let Some(mut stdin) = child.stdin.take() {
        use tokio::io::AsyncWriteExt;
        let _ = stdin.write_all(json_str.as_bytes()).await;
        let _ = stdin.write_all(b"\n").await;
        let _ = stdin.flush().await;
        drop(stdin); // Close stdin to signal end of stream
    }

    let stdout = child.stdout.take().ok_or("Failed to capture stdout")?;
    let stderr = child.stderr.take();
    let app_handle_clone = app_handle.clone();
    let pid_lock = state.current_pid.clone();

    if let Some(err_stream) = stderr {
        tokio::spawn(async move {
            let reader = BufReader::new(err_stream);
            let mut lines = reader.lines();
            while let Ok(Some(_)) = lines.next_line().await {
                // Continuously drain stderr to prevent OS pipe buffer clogging
            }
        });
    }

    tokio::spawn(async move {
        let reader = BufReader::new(stdout);
        let mut lines = reader.lines();

        while let Ok(Some(line)) = lines.next_line().await {
            let trimmed = line.trim();
            if trimmed.is_empty() {
                continue;
            }

            if let Ok(val) = serde_json::from_str::<serde_json::Value>(trimmed) {
                let event_type = val.get("type").and_then(|t| t.as_str()).unwrap_or("");
                match event_type {
                    "progress" => {
                        let _ = app_handle_clone.emit("translation-progress", val);
                    }
                    "success" => {
                        let _ = app_handle_clone.emit("translation-success", val);
                    }
                    "error" => {
                        let _ = app_handle_clone.emit("translation-error", val);
                    }
                    "ready" => {
                        let _ = app_handle_clone.emit("translation-ready", val);
                    }
                    _ => {
                        let _ = app_handle_clone.emit("translation-log", val);
                    }
                }
            }
        }

        // Clean up PID lock when child terminates
        let mut p = pid_lock.lock().await;
        *p = None;
    });

    Ok(())
}

#[tauri::command]
async fn cancel_translation(state: State<'_, AppState>) -> Result<(), String> {
    let mut pid_guard = state.current_pid.lock().await;
    if let Some(pid) = *pid_guard {
        #[cfg(windows)]
        {
            let _ = Command::new("taskkill")
                .args(["/F", "/T", "/PID", &pid.to_string()])
                .output();
        }
        #[cfg(not(windows))]
        {
            let _ = Command::new("kill").args(["-9", &pid.to_string()]).output();
        }
        *pid_guard = None;
        return Ok(());
    }
    Ok(())
}

#[tauri::command]
fn open_in_explorer(path: String) -> Result<(), String> {
    let p = Path::new(&path);
    #[cfg(windows)]
    {
        if p.exists() {
            if p.is_dir() {
                let _ = Command::new("explorer").arg(&path).spawn();
            } else {
                let _ = Command::new("explorer")
                    .arg(format!("/select,{}", path))
                    .spawn();
            }
            return Ok(());
        }
    }
    #[cfg(target_os = "macos")]
    {
        let _ = Command::new("open").arg("-R").arg(&path).spawn();
        return Ok(());
    }
    #[cfg(target_os = "linux")]
    {
        let _ = Command::new("xdg-open").arg(&path).spawn();
        return Ok(());
    }
    #[allow(unreachable_code)]
    Err("Không tìm thấy đường dẫn".into())
}

#[tauri::command]
fn open_file(path: String) -> Result<(), String> {
    #[cfg(windows)]
    {
        let _ = Command::new("cmd")
            .args(["/c", "start", "", &path])
            .spawn();
        return Ok(());
    }
    #[cfg(target_os = "macos")]
    {
        let _ = Command::new("open").arg(&path).spawn();
        return Ok(());
    }
    #[cfg(target_os = "linux")]
    {
        let _ = Command::new("xdg-open").arg(&path).spawn();
        return Ok(());
    }
    #[allow(unreachable_code)]
    Err("Không thể mở file".into())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .manage(AppState::default())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .invoke_handler(tauri::generate_handler![
            get_system_status,
            start_translation,
            cancel_translation,
            open_in_explorer,
            open_file
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
