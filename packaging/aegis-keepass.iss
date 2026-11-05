; Inno Setup script for the Windows desktop app.
; Compile with scripts/package-windows-installer.ps1, which defines:
;   AppVersion, ArchLabel (x64 or arm64), AllowedArch (x64os or arm64)

#ifndef AppVersion
  #error AppVersion is required
#endif
#ifndef ArchLabel
  #error ArchLabel is required
#endif
#ifndef AllowedArch
  #error AllowedArch is required
#endif

#define AppName "Aegis-KeePass OTP Sync"
#define AppExe "aegis-keepass.exe"
#define AppPublisher "Waldemar Scudeller Jr."

[Setup]
AppId={{A9E3C4D1-7B62-4F05-8E19-6C0D2A8B5F47}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
DefaultDirName={autopf}\{#AppName}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=aegis-keepass-{#AppVersion}-windows-{#ArchLabel}
SetupIconFile=..\build\aegis-keepass.ico
UninstallDisplayIcon={app}\{#AppExe}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed={#AllowedArch}
ArchitecturesInstallIn64BitMode={#AllowedArch}
PrivilegesRequired=lowest
MinVersion=10.0
LicenseFile=..\LICENSE
CloseApplications=yes
RestartApplications=no

[Files]
Source: "..\dist\{#AppExe}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\NOTICES"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"

[Run]
Filename: "{app}\{#AppExe}"; Description: "Launch {#AppName}"; Flags: nowait postinstall skipifsilent

[Code]
const
  WebView2Key = 'SOFTWARE\Microsoft\EdgeUpdate\Clients\{{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}';

function HasWebView2(RootKey: Integer): Boolean;
var
  Version: String;
begin
  Result :=
    RegQueryStringValue(RootKey, WebView2Key, 'pv', Version) and
    (Version <> '') and (Version <> '0.0.0.0');
end;

function InitializeSetup: Boolean;
begin
  Result := True;
  if HasWebView2(HKLM) or HasWebView2(HKLM64) or HasWebView2(HKCU) then
    Exit;
  MsgBox(
    'Edge WebView2 Runtime was not found. The app needs it to open its window. ' +
    'Most Windows 10 and 11 systems already have it. You can finish installing, then install WebView2 from Microsoft if the window does not open.',
    mbInformation, MB_OK);
end;
