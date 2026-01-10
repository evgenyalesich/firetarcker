!define APPNAME "FireStorm"
!define VERSION "${VERSION}"
!define EXE_NAME "FireStorm.exe"
!define INSTALL_DIR "$PROGRAMFILES\FireStorm"

Name "${APPNAME}"
OutFile "dist_installer\windows\FireStorm-${VERSION}-setup.exe"
InstallDir "${INSTALL_DIR}"
RequestExecutionLevel admin

Icon "FireStorm\img\gui_icon.ico"
UninstallIcon "FireStorm\img\gui_icon.ico"

Page directory
Page instfiles
UninstPage instfiles

Section "Install"
  SetOutPath "$INSTDIR"
  File /r "dist\FireStorm\*"
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
