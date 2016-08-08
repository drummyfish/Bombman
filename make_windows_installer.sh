#!/bin/bash

# This script makes a Windows installer in Bash, using NSIS.
# NSIS is required: sudo apt-get install nsis.

# download python 2.7 installer:
wget -O "./python27_install.msi" "https://www.python.org/ftp/python/2.7.12/python-2.7.12.msi"

# download pygame 2.7 installer:
wget -O "./pygame27_install.msi" "http://pygame.org/ftp/pygame-1.9.1.win32-py2.7.msi"

# make the installer (embeds the above downloaded files):
makensis installer_script.nsi

# remove tmp stuff:

rm "./python27_install.msi"
rm "./pygame27_install.msi"
