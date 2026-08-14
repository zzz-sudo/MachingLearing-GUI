#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
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
        .run(tauri::generate_context!())
        .expect("failed to run MachingLearing GUI");
}
