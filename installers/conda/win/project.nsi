# Mantid NSIS script
# Assumes you have passed /DVERSION, /DOUTFILE_NAME, /DPACKAGE_DIR, /DICON_PATH, /DMUI_PAGE_LICENSE_PATH as arguments

# This must be set for long paths to work properly.
# Unicode only defaults to true in NSIS 3.07 onwards.
Unicode True

!include MUI2.nsh

!define START_MENU_FOLDER "Mantid"
!define PACKAGE_NAME "mantidTest"
!define PACKAGE_VENDOR "ISIS Rutherford Appleton Laboratory UKRI, NScD Oak Ridge National Laboratory, European Spallation Source and Institut Laue - Langevin"

# --------------------------------------------------------------------
# Add functions needed for install and uninstall with the modern UI

# Overwrite .onInit to give the option to uninstall a previous version if it exists
Function .onInit
ReadRegStr $0 HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PACKAGE_NAME}" "UninstallString"
${If} $0 != ""
${AndIf} ${Cmd} `MessageBox MB_YESNO|MB_ICONQUESTION "Run the uninstaller of the previous version?" /SD IDYES IDYES`
	Exec $0
${EndIf}
FunctionEnd

# --------------------------------------------------------------------
# ModernUI variables definitions, some of these are passed in as arguements such as MUI_ICON, MUI_UNICON etc.
!define MUI_ICON "${ICON_PATH}"
!define MUI_UNICON "${ICON_PATH}"

!insertmacro MUI_PAGE_WELCOME
!insertmacro MUI_PAGE_LICENSE "${MUI_PAGE_LICENSE_PATH}"
!insertmacro MUI_PAGE_DIRECTORY

!insertmacro MUI_PAGE_INSTFILES
!insertmacro MUI_PAGE_FINISH

!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES

!insertmacro MUI_LANGUAGE "English"

# --------------------------------------------------------------------

# The name of the installer
Name "Mantid Workbench"

# The file to write
OutFile "${OUTFILE_NAME}"

# The default installation directory
InstallDir "C:\MantidInstall"

# The text to prompt the user to enter a directory
DirText "This will install mantid and its components"

RequestExecutionLevel user

# The stuff to install
Section "-Core installation"
    # Set output path to the installation directory.
    SetOutPath "$INSTDIR"

    # Put files there
    File /r "${PACKAGE_DIR}\*.*"

    # Add MantidWorkbench-script.pyw file to the install directory
    FileOpen $0 "$INSTDIR\bin\MantidWorkbench-script.pyw" w
    FileWrite $0 "#!$INSTDIR\bin\pythonw.exe$\n"
    FileWrite $0 "import workbench.app.main$\n"
    FileWrite $0 "workbench.app.main.main()$\n"
    FileClose $0

    # Store installation folder in registry
    WriteRegStr HKCU "Software\${PACKAGE_VENDOR}\${PACKAGE_NAME}" "" $INSTDIR

    # Make an uninstaller
    WriteUninstaller $INSTDIR\Uninstall.exe

	# Write registry entries for uninstaller for "Add/Remove programs" information
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PACKAGE_NAME}" "DisplayName" "${PACKAGE_NAME}"
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PACKAGE_NAME}" "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PACKAGE_NAME}" "DisplayVersion" "${VERSION}"
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PACKAGE_NAME}" "NoRepair" 1
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PACKAGE_NAME}" "NoModify" 1
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PACKAGE_NAME}" "DisplayIcon" "$\"$INSTDIR\uninstall.exe$\""
	WriteRegStr HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PACKAGE_NAME}" "Publisher" "${PACKAGE_VENDOR}"

    # Create shortucts for startmenu
    CreateDirectory "$SMPROGRAMS\${START_MENU_FOLDER}"
    CreateShortCut "$SMPROGRAMS\${START_MENU_FOLDER}\Mantid Workbench.lnk" "$INSTDIR\bin\MantidWorkbench.exe"
    CreateShortCut "$SMPROGRAMS\${START_MENU_FOLDER}\Mantid Notebook.lnk" "$INSTDIR\bin\mantidpython.bat" "notebook --notebook-dir=%userprofile%"
    CreateShortCut "$SMPROGRAMS\${START_MENU_FOLDER}\Uninstall.lnk" "$\"$INSTDIR\uninstall.exe$\""

SectionEnd ; end the section

# The uninstall section
Section "Uninstall"
    # Remove uninstall registry entries
	DeleteRegKey HKCU "Software\Microsoft\Windows\CurrentVersion\Uninstall\${PACKAGE_NAME}"
	DeleteRegKey HKCU "Software\${PACKAGE_VENDOR}\${PACKAGE_NAME}"

    # Remove mantid itself
    RMDir /r $INSTDIR\bin
    RMDir /r $INSTDIR\include
    RMDir /r $INSTDIR\instrument\*.*
    RMDir /r $INSTDIR\lib\*.*
    RMDir /r $INSTDIR\plugins\*.*
    RMDir /r $INSTDIR\scripts\*.*
    RMDir /r $INSTDIR\share\*.*
    Delete $INSTDIR\Uninstall.exe
    RMDir $INSTDIR

    # Remove shortcuts
    Delete "$SMPROGRAMS\${START_MENU_FOLDER}\Mantid Workbench.lnk"
    Delete "$SMPROGRAMS\${START_MENU_FOLDER}\Mantid Workbench (Python).lnk"
    Delete "$SMPROGRAMS\${START_MENU_FOLDER}\Mantid Notebook.lnk"
    Delete "$SMPROGRAMS\${START_MENU_FOLDER}\Uninstall.lnk"
    RMDir "$SMPROGRAMS\${START_MENU_FOLDER}"
SectionEnd

