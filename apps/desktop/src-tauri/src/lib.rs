use std::sync::{Arc, Mutex};
use std::time::{Duration, Instant};

use tauri::{Manager, RunEvent};
use tauri_plugin_shell::process::{CommandChild, CommandEvent};
use tauri_plugin_shell::ShellExt;

struct SidecarProcess {
    child: Arc<Mutex<Option<CommandChild>>>,
}

#[cfg(target_os = "windows")]
fn terminate_sidecar(process: CommandChild) {
    use std::os::windows::process::CommandExt;

    const CREATE_NO_WINDOW: u32 = 0x08000000;
    let status = std::process::Command::new("taskkill")
        .args(["/PID", &process.pid().to_string(), "/T", "/F"])
        .creation_flags(CREATE_NO_WINDOW)
        .status();
    if !status.is_ok_and(|result| result.success()) {
        let _ = process.kill();
    }
}

#[cfg(not(target_os = "windows"))]
fn terminate_sidecar(process: CommandChild) {
    let _ = process.kill();
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let application = tauri::Builder::default()
        .plugin(tauri_plugin_shell::init())
        .setup(|app| {
            let sidecar = app
                .shell()
                .sidecar("task-service")
                .map_err(|error| format!("SidecarConfigurationError: {error}"))?
                .args(["--host", "127.0.0.1", "--port", "8765"]);
            let (mut events, child) = sidecar
                .spawn()
                .map_err(|error| format!("SidecarStartError: {error}"))?;
            let child_handle = Arc::new(Mutex::new(Some(child)));
            app.manage(SidecarProcess {
                child: child_handle,
            });

            tauri::async_runtime::spawn(async move {
                while let Some(event) = events.recv().await {
                    match event {
                        CommandEvent::Stdout(bytes) => {
                            println!("[task-service] {}", String::from_utf8_lossy(&bytes));
                        }
                        CommandEvent::Stderr(bytes) => {
                            eprintln!("[task-service] {}", String::from_utf8_lossy(&bytes));
                        }
                        CommandEvent::Terminated(payload) => {
                            eprintln!("[task-service] terminated: {:?}", payload);
                        }
                        _ => {}
                    }
                }
            });

            let deadline = Instant::now() + Duration::from_secs(15);
            while Instant::now() < deadline {
                if std::net::TcpStream::connect(("127.0.0.1", 8765)).is_ok() {
                    break;
                }
                std::thread::sleep(Duration::from_millis(100));
            }
            if Instant::now() >= deadline {
                return Err("SidecarReadyTimeoutError: task service did not open port 8765".into());
            }

            let window_config = app
                .config()
                .app
                .windows
                .first()
                .expect("main window configuration is missing")
                .clone();
            let mut window_builder =
                tauri::WebviewWindowBuilder::from_config(app.handle(), &window_config)?;

            // Allow portable and restricted environments to select a writable WebView directory.
            if let Some(data_directory) = std::env::var_os("ML_GUI_WEBVIEW_DATA_DIR") {
                window_builder = window_builder.data_directory(data_directory.into());
            }

            window_builder.build()?;
            Ok(())
        })
        .build(tauri::generate_context!())
        .expect("failed to build MachingLearing GUI");

    application.run(|app, event| {
        if let RunEvent::ExitRequested { .. } = event {
            if let Some(state) = app.try_state::<SidecarProcess>() {
                if let Ok(mut child) = state.child.lock() {
                    if let Some(process) = child.take() {
                        terminate_sidecar(process);
                    }
                }
            }
        }
    });
}
