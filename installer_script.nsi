Outfile "bombman_install.exe"
 
Caption "Install Bombman"
LicenseData "gpl.txt"

InstallDir "C:\Users\Uzivatel\Documents\GitHub\bombman-master\test"
Page license
Page directory
Page instfiles

Section

SetOutPath $INSTDIR

# download pygame

NSISdl::download /TIMEOUT=30000 /NOIEPROXY "http://pygame.org/ftp/pygame-1.9.1.win32-py2.7.msi" "pygame27_install.msi"

Pop $R0 ;Get the return value
  StrCmp $R0 "success" +3
    MessageBox MB_OK "Download failed: $R0"
    Quit

# install pygame, including python

ExecWait '"$SYSDIR\msiExec" /i "$INSTDIR\pygame27_install.msi"' $0

# TODO: check return code of $0 here

File bombman.py
File /r maps
File /r resources

# create batch file

FileOpen $4 "$INSTDIR\run_bombman.bat" w
FileWrite $4 "python bombman.py"
FileClose $4

# create desktop shortcut

CreateShortCut "$DESKTOP\bombman.lnk" "$INSTDIR\run_bombman.bat"

MessageBox MB_OK "Bombman has been succesfully installed."

SectionEnd