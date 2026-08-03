; Instalador de primera vez para Sistema PAE (Inno Setup).
; Compilar con: ISCC.exe packaging\installer.iss   (desde la raíz del repo)
; Requiere que dist\SistemaPAE.exe y dist\updater.exe ya existan (compilados
; con packaging\pae.spec) y packaging\installer\vc_redist.x64.exe presente.
;
; Por qué existe: instalar sólo el .exe (descomprimiendo el .zip) en una
; máquina que nunca tuvo el programa puede dejar la interfaz sin texto/fondos
; si falta el Redistribuible de Visual C++ de Microsoft -- este instalador lo
; revisa e instala automáticamente si hace falta, además de crear accesos
; directos. Se instala en la carpeta del USUARIO (sin pedir permisos de
; administrador) porque el programa escribe su propia base de datos junto al
; .exe -- instalarlo en "Archivos de programa" rompería esa escritura para
; una cuenta sin privilegios de administrador.
;
; NO cambiar AppId entre versiones: es lo que le permite a Inno Setup
; reconocer una instalación existente y actualizarla en el mismo lugar (sin
; duplicar accesos directos ni perder data\ al reinstalar).

#define MyAppName "Sistema PAE"
#define MyAppVersion "0.28.0"
#define MyAppPublisher "Sistema PAE"
#define MyAppExeName "SistemaPAE.exe"

[Setup]
AppId={{B9F08AF3-7F70-433B-9A1C-0E24F6E69625}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\SistemaPAE
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=SistemaPAE_Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
; No se toca UninstallDelete: al desinstalar, data\ (la base de datos real)
; y certificados\ se quedan donde están -- sólo se borran los binarios que
; este instalador puso.

[Languages]
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"

[Files]
Source: "..\dist\SistemaPAE.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\dist\updater.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "installer\vc_redist.x64.exe"; DestDir: "{tmp}"; Flags: dontcopy deleteafterinstall

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"

[Run]
Filename: "{tmp}\vc_redist.x64.exe"; Parameters: "/install /quiet /norestart"; StatusMsg: "Instalando componentes necesarios de Microsoft (una sola vez)..."; Check: VCRedistNeedsInstall; Flags: waituntilterminated
Filename: "{app}\{#MyAppExeName}"; Description: "Ejecutar {#MyAppName} ahora"; Flags: nowait postinstall skipifsilent

[Code]
function VCRedistNeedsInstall: Boolean;
var
  Installed: Cardinal;
begin
  { Redistribuible combinado VS 2015-2022 (x64): esta clave y valor son los
    que Microsoft documenta para detectarlo. Si no existe o Installed <> 1,
    hace falta instalarlo. }
  Result := True;
  if RegQueryDWordValue(HKLM, 'SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\X64', 'Installed', Installed) then
  begin
    if Installed = 1 then
      Result := False;
  end;
end;

procedure ExtractVCRedist;
begin
  ExtractTemporaryFile('vc_redist.x64.exe');
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if (CurStep = ssInstall) and VCRedistNeedsInstall then
    ExtractVCRedist;
end;
