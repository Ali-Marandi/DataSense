#define AppName "DataSense"
#ifndef AppVersion
  #define AppVersion "0.1.0"
#endif
#ifndef AppPublisher
  #define AppPublisher "DataSense"
#endif
#ifndef AppExeName
  #define AppExeName "DataSense.exe"
#endif
#ifndef SourceDir
  #define SourceDir "..\dist\DataSense"
#endif

[Setup]
AppId={{9E130AA6-4E94-4C87-A7F0-F1DAFA46C956}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist\installer
OutputBaseFilename=DataSense-{#AppVersion}-windows-x64-setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
UninstallDisplayIcon={app}\{#AppExeName}
PrivilegesRequired=lowest

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "{#SourceDir}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExeName}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  if IsAdminInstallMode then
    MsgBox('DataSense installs per user by default to keep the local-first desktop workflow simple.', mbInformation, MB_OK);
end;
