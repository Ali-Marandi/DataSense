; Inno Setup script producing the DataSense Windows installer.
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
AppId={{6F1D2C74-6D3B-4B1E-9C3C-DA7EC1F0A501}
AppName=DataSense
AppVersion={#AppVersion}
AppPublisher=Ali Marandi
AppPublisherURL=https://github.com/Ali-Marandi/DataSense
DefaultDirName={autopf}\DataSense
DefaultGroupName=DataSense
UninstallDisplayIcon={app}\DataSense.exe
OutputDir=output
OutputBaseFilename=DataSense-{#AppVersion}-setup
SetupIconFile=..\assets\icon.ico
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequiredOverridesAllowed=dialog

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Files]
Source: "..\dist\DataSense\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\DataSense"; Filename: "{app}\DataSense.exe"
Name: "{group}\Uninstall DataSense"; Filename: "{uninstallexe}"
Name: "{autodesktop}\DataSense"; Filename: "{app}\DataSense.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\DataSense.exe"; Description: "Launch DataSense"; Flags: nowait postinstall skipifsilent
