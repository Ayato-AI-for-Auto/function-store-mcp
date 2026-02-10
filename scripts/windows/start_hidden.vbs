Set WshShell = CreateObject("WScript.Shell")
' 0 = Hide Window, False = Do not wait for completion
WshShell.Run chr(34) & ".\start_server.bat" & Chr(34), 0, False
