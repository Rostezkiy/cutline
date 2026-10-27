# Иконки

Tauri требует готовые иконки в этой папке (`32x32.png`, `128x128.png`, `icon.ico`).

Сгенерировать из одного квадратного PNG (минимум 512×512):

```bash
cd tauri/src-tauri
cargo tauri icon ..\..\logo.png
```

Или удалите поле `bundle.icon` в `tauri.conf.json`, если иконки не нужны
(для `cargo tauri dev` они не обязательны, для установщика NSIS — нужны).
