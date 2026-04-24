use std::fs;
use std::net::TcpStream;
use std::sync::Mutex;
use std::thread;
use std::time::Duration;

use tauri::Manager;
use tauri_plugin_shell::ShellExt;

fn wait_for_backend() -> Result<(), String> {
  for _ in 0..120 {
    if TcpStream::connect("127.0.0.1:8000").is_ok() {
      return Ok(());
    }
    thread::sleep(Duration::from_millis(500));
  }
  Err("backend sidecar did not listen on 127.0.0.1:8000 within 60s".to_string())
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
  tauri::Builder::default()
    .plugin(tauri_plugin_shell::init())
    .setup(|app| {
      if cfg!(debug_assertions) {
        app.handle().plugin(
          tauri_plugin_log::Builder::default()
            .level(log::LevelFilter::Info)
            .build(),
        )?;
      }

      let resource_dir = app
        .path()
        .resource_dir()
        .map_err(|e| format!("failed to resolve resource directory: {}", e))?;
      let market_data_dir = resource_dir.join("market_data");
      let qlib_dir = market_data_dir.join("qlib");
      let qlib_cn_dir = qlib_dir.join("cn_data");
      let qlib_us_dir = qlib_dir.join("us_data");
      let local_futures_dir = market_data_dir.join("local_futures");

      let app_data_dir = app
        .path()
        .app_data_dir()
        .map_err(|e| format!("failed to resolve app data directory: {}", e))?;
      let data_dir = app_data_dir.join("data");
      let results_dir = app_data_dir.join("results");
      let logs_dir = app
        .path()
        .app_log_dir()
        .map_err(|e| format!("failed to resolve app log directory: {}", e))?;

      fs::create_dir_all(&data_dir)
        .map_err(|e| format!("failed to create app data directory: {}", e))?;
      fs::create_dir_all(&results_dir)
        .map_err(|e| format!("failed to create results directory: {}", e))?;
      fs::create_dir_all(&logs_dir)
        .map_err(|e| format!("failed to create logs directory: {}", e))?;

      // Spawn the Python sidecar with bundled read-only market data and writable runtime paths.
      let mut sidecar_command = app.shell().sidecar("aiminer-backend")
        .map_err(|e| format!("failed to create sidecar command: {}", e))?;
      sidecar_command = sidecar_command
        .env("AIMINER_DATA_DIR", data_dir.as_os_str())
        .env("AIMINER_RESULTS_DIR", results_dir.as_os_str())
        .env("AIMINER_LOGS_DIR", logs_dir.as_os_str())
        .env("AIMINER_PACKAGED_MARKET_DATA_DIR", market_data_dir.as_os_str())
        .env("QLIB_CN_DATA_PATH", qlib_cn_dir.as_os_str())
        .env("QLIB_US_DATA_PATH", qlib_us_dir.as_os_str())
        .env("QLIB_DATA_PATH", qlib_cn_dir.as_os_str());
      if local_futures_dir.exists() {
        sidecar_command = sidecar_command
          .env("AIMINER_LOCAL_DATA_PATH", local_futures_dir.as_os_str())
          .env("AIMINER_LOCAL_FUTURES_PATH", local_futures_dir.as_os_str());
      }
      
      let (mut rx, child) = sidecar_command
        .spawn()
        .map_err(|e| format!("failed to spawn sidecar: {}", e))?;
      tauri::async_runtime::spawn(async move {
        while rx.recv().await.is_some() {}
      });

      if let Err(err) = wait_for_backend() {
        let _ = child.kill();
        return Err(err.into());
      }
      app.manage(Mutex::new(Some(child)));

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
