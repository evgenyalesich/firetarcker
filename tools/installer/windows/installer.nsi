!define APPNAME "FireStorm"
!ifndef VERSION
  !define VERSION "0.0.0"
!endif
!ifndef ROOT
  !define ROOT "."
!endif
!ifndef OUTDIR
  !define OUTDIR "${ROOT}\dist_installer\windows"
!endif
!define EXE_NAME "FireStorm.exe"
!define INSTALL_DIR "$PROGRAMFILES\FireStorm"

Name "${APPNAME}"
OutFile "${OUTDIR}\FireStorm-${VERSION}-setup.exe"
InstallDir "${INSTALL_DIR}"
RequestExecutionLevel admin

Icon "${ROOT}\FireStorm\img\gui_icon.ico"
UninstallIcon "${ROOT}\FireStorm\img\gui_icon.ico"

Page directory
Page instfiles
UninstPage instfiles

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "${ROOT}\dist\FireStorm\*"
  CreateShortCut "$DESKTOP\FireStorm.lnk" "$INSTDIR\${EXE_NAME}"
  CreateShortCut "$SMPROGRAMS\FireStorm.lnk" "$INSTDIR\${EXE_NAME}"
  WriteUninstaller "$INSTDIR\Uninstall.exe"
SectionEnd

Section "Uninstall"
  Delete "$DESKTOP\FireStorm.lnk"
  Delete "$SMPROGRAMS\FireStorm.lnk"
  Delete "$INSTDIR\Uninstall.exe"
  RMDir /r "$INSTDIR"
SectionEnd
