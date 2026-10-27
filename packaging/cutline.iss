; ============================================================
;  Cutline: установщик (Inno Setup 6+)
;  Сборка: iscc packaging\cutline.iss  ->  dist\Cutline-Setup.exe
;  Требует готовый dist\Cutline (см. build_windows.bat)
; ============================================================
#define AppName "Cutline"
; Версию можно переопределить из CI: iscc /DAppVersion=1.2.3 packaging\cutline.iss
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppPublisher "Cutline"
#define AppExeName "Cutline.exe"
#define ShellExeName "Cutline Desktop.exe"

[Setup]
AppId={{B4B0B3C2-5B4B-4E6C-9B0F-1D7A7A6C0F21}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={localappdata}\Programs\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
; Никаких прав администратора: установка в профиль пользователя
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=Cutline-Setup
SetupIconFile=icon.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#ShellExeName}
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Переносим весь каталог сборки: exe, шаблоны, ffmpeg, настольная оболочка
Source: "..\dist\Cutline\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
; Основной ярлык - нативное окно (оболочка сама поднимет сервер)
Name: "{group}\{#AppName}"; Filename: "{app}\{#ShellExeName}"
Name: "{group}\{#AppName} (в браузере)"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Удалить {#AppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#ShellExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#ShellExeName}"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{app}"
