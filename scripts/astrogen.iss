; Inno Setup Script for AstroGen Space Studio
; Download Inno Setup from: https://jrsoftware.org/isdl.php
; To compile: Open Inno Setup, open this file, and press Build -> Compile.

[Setup]
AppName=AstroGen
AppVersion=1.0.0
AppPublisher=AstroGen Research Group
DefaultDirName={autopf}\AstroGen
DefaultGroupName=AstroGen
OutputDir=..\dist
OutputBaseFilename=AstroGen_Setup
SetupIconFile=..\frontend\logo.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
DisableProgramGroupPage=yes
; We store database and models dynamically in user's hidden APPDATA folder,
; and only keep the generated data folder visible in the install path.

[Files]
; Copy all the compiled files from dist/AstroGen into the installation folder
Source: "..\dist\AstroGen\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs

[Icons]
; Create desktop and Start Menu shortcuts
Name: "{autoprograms}\AstroGen"; Filename: "{app}\AstroGen.exe"
Name: "{autodesktop}\AstroGen"; Filename: "{app}\AstroGen.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop shortcut"; GroupDescription: "Additional shortcuts:"

[Run]
; Option to run the application immediately after installation
Filename: "{app}\AstroGen.exe"; Description: "Launch AstroGen Space Studio"; Flags: nowait postinstall skipifsilent
