// Оболочка Cutline: WebView2-окно поверх локального Flask-сервера.
// Сборка описана в tauri/README.md. Сервер (Cutline.exe или python run.py)
// запускается из этой же папки, а при выходе — останавливается.

#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::net::{SocketAddr, TcpStream};
use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::Mutex;
use std::thread;
use std::time::{Duration, Instant};

use tauri::{Manager, RunEvent, Url};

const PORT: u16 = 5000;
const STARTUP_TIMEOUT: Duration = Duration::from_secs(300);
const POLL_INTERVAL: Duration = Duration::from_millis(400);

/// Дочерний процесс сервера (если оболочка его запускала).
struct ServerProcess(Mutex<Option<Child>>);

fn server_addr() -> SocketAddr {
    SocketAddr::from(([127, 0, 0, 1], PORT))
}

fn server_ready() -> bool {
    TcpStream::connect_timeout(&server_addr(), Duration::from_millis(500)).is_ok()
}

/// Каталог, где лежит сервер: рядом с оболочкой (сборка) или корень репозитория (dev).
fn server_dir() -> PathBuf {
    let exe = std::env::current_exe().unwrap_or_else(|_| PathBuf::from("."));
    let dir = exe.parent().map(PathBuf::from).unwrap_or_else(|| PathBuf::from("."));
    if dir.join("Cutline.exe").exists() || dir.join("run.py").exists() {
        return dir;
    }
    for up in ["../..", "../../.."] {
        let candidate = dir.join(up);
        if candidate.join("run.py").exists() {
            return candidate;
        }
    }
    dir
}

/// Поднимает сервер, если он ещё не отвечает. Возвращает None, если сервер уже запущен.
fn spawn_server() -> Option<Child> {
    if server_ready() {
        return None;
    }
    let dir = server_dir();
    let mut command = if dir.join("Cutline.exe").exists() {
        Command::new(dir.join("Cutline.exe"))
    } else if dir.join("run.py").exists() {
        let python = if cfg!(windows) { "python" } else { "python3" };
        let mut cmd = Command::new(python);
        cmd.arg("run.py");
        cmd
    } else {
        eprintln!(
            "Cutline не найден рядом с оболочкой ({}). Соберите dist/Cutline или запустите из репозитория.",
            dir.display()
        );
        return None;
    };

    command.current_dir(&dir).env("OPEN_BROWSER", "0").env("PORT", PORT.to_string());
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        const CREATE_NO_WINDOW: u32 = 0x0800_0000;
        command.creation_flags(CREATE_NO_WINDOW);
    }

    match command.spawn() {
        Ok(child) => Some(child),
        Err(err) => {
            eprintln!("Не удалось запустить сервер Cutline: {err}");
            None
        }
    }
}

fn main() {
    let app = tauri::Builder::default()
        .setup(|app| {
            app.manage(ServerProcess(Mutex::new(spawn_server())));

            if let Some(window) = app.get_webview_window("main") {
                thread::spawn(move || {
                    let started = Instant::now();
                    while started.elapsed() < STARTUP_TIMEOUT {
                        if server_ready() {
                            match Url::parse(&format!("http://127.0.0.1:{PORT}/")) {
                                Ok(url) => {
                                    let _ = window.set_title("Cutline");
                                    let _ = window.navigate(url);
                                }
                                Err(err) => eprintln!("Некорректный адрес сервера: {err}"),
                            }
                            return;
                        }
                        thread::sleep(POLL_INTERVAL);
                    }
                    eprintln!("Сервер Cutline не ответил за {} с.", STARTUP_TIMEOUT.as_secs());
                });
            }
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("Не удалось создать окно Cutline");

    app.run(|handle, event| {
        if matches!(event, RunEvent::Exit) {
            if let Some(state) = handle.try_state::<ServerProcess>() {
                if let Ok(mut guard) = state.0.lock() {
                    if let Some(mut child) = guard.take() {
                        let _ = child.kill();
                        let _ = child.wait();
                    }
                }
            }
        }
    });
}
