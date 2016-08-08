!include LogicLib.nsh
!include "MUI2.nsh"

!define MUI_ICON "resources\icon.ico"

Outfile "bombman_install.exe"
 
Caption "Install Bombman"
LicenseData "gpl.txt"

InstallDir "C:\bombman"
Page license
Page directory
Page instfiles

Section

SetOutPath $INSTDIR

# install python 2.7 and pygame

File "python27_install.msi"
File "pygame27_install.msi"

ExecWait '"$SYSDIR\msiExec" /i "$INSTDIR\python27_install.msi"' $0
ExecWait '"$SYSDIR\msiExec" /i "$INSTDIR\pygame27_install.msi"' $0

# read python install path from registry (will be in one of the following)

ReadRegStr $5 HKLM SOFTWARE\Python\PythonCore\2.7\InstallPath ""
StrLen $6 $5

${If} $6 == 0
  ReadRegStr $5 HKCU SOFTWARE\Python\PythonCore\2.7\InstallPath ""
  StrLen $6 $5
${EndIf}

${If} $6 == 0
  ReadRegStr $5 HKLM SOFTWARE\Wow6432Node\Python\PythonCore\2.7\InstallPath ""
${EndIf}

DetailPrint "Python 2.7 path: $5"

DetailPrint "testing python plus pygame"

FileOpen $4 "$INSTDIR\test_pygame.py" w
FileWrite $4 "import sys$\r$\n"
FileWrite $4 "try:$\r$\n"
FileWrite $4 "  import pygame$\r$\n"
FileWrite $4 "  sys.exit(0)$\r$\n"
FileWrite $4 "except Exception:$\r$\n"
FileWrite $4 "  sys.exit(1)$\r$\n"
FileClose $4

ExecWait '"$5\python.exe" "$INSTDIR\test_pygame.py"' $9

DetailPrint "testing script returned $9"

Delete "$INSTDIR\test_pygame.py"

${IfNot} $9 == 0   # check the test result
  MessageBox MB_OK "Error: Python 2.7 or Pygame are not correctly installed, exiting now."
  Quit
${EndIf}

File bombman.py
File /r maps
File /r resources

# create batch run file

FileOpen $4 "$INSTDIR\run_bombman.bat" w
FileWrite $4 '"$5\python.exe" bombman.py'
FileClose $4

# create desktop shortcut

CreateShortCut "$DESKTOP\bombman.lnk" "$INSTDIR\run_bombman.bat" "" "$INSTDIR\resources\icon.ico" 0

MessageBox MB_OK "Bombman has been succesfully installed."

SectionEnd
