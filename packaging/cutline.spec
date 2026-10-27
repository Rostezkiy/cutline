# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-спецификация Cutline (onedir).

Сборка:  build_windows.bat  (или: pyinstaller --noconfirm --clean packaging/cutline.spec)

Результат: dist/Cutline/Cutline.exe + шаблоны интерфейса.

ffmpeg/ffprobe в дистрибутив НЕ входят: пользователь скачивает их из GUI
(см. binaries.py), поэтому сборка весит на ~300 МБ меньше. Если бинарники
нужны офлайн - положите их в packaging/bin перед сборкой, они попадут в dist.
"""

import os

from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

ROOT = os.path.abspath(os.path.join(SPECPATH, '..'))
BIN_DIR = os.path.join(ROOT, 'packaging', 'bin')

datas = [(os.path.join(ROOT, 'templates'), 'templates')]
# faster-whisper поставляет tokenizer.json/vocabulary и прочие данные
datas += collect_data_files('faster_whisper')

binaries = []
for name in ('ffmpeg.exe', 'ffprobe.exe', 'ffmpeg', 'ffprobe'):
    candidate = os.path.join(BIN_DIR, name)
    if os.path.exists(candidate):
        binaries.append((candidate, '.'))
binaries += collect_dynamic_libs('ctranslate2')
binaries += collect_dynamic_libs('onnxruntime')

hiddenimports = [
    'waitress',
    'ctranslate2',
    'huggingface_hub',
    'onnxruntime',
    'av',
    'models_api',
    'files_api',
    'binaries',
    # Модули приложения: substring-импорты PyInstaller может не увидеть
    'config',
    'jobstore',
    'media',
    'transcribe',
    'summarize',
    'pipeline',
    'routes',
]

# Тяжёлые/неиспользуемые пакеты не тащим в сборку
excludes = [
    'torch', 'torchaudio', 'torchvision', 'tensorflow', 'matplotlib', 'scipy',
    'pandas', 'IPython', 'notebook', 'pytest', 'tkinter', 'PyQt5', 'PySide6',
]

a = Analysis(
    [os.path.join(ROOT, 'run.py')],
    pathex=[ROOT],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='Cutline',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='Cutline',
)
