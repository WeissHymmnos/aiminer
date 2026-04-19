use tauri_plugin_shell::ShellExt;

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

      // Spawn the Python sidecar
      let sidecar_command = app.shell().sidecar("aiminer-backend")
        .map_err(|e| format!("failed to create sidecar command: {}", e))?;
      
      let (mut _rx, _child) = sidecar_command
        .spawn()
        .map_err(|e| format!("failed to spawn sidecar: {}", e))?;

      Ok(())
    })
    .run(tauri::generate_context!())
    .expect("error while running tauri application");
}
