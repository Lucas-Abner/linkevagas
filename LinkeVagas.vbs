Set objShell = CreateObject("WScript.Shell")

' Pega a pasta onde este script (LinkeVagas.vbs) está salvo
strPath = CreateObject("Scripting.FileSystemObject").GetParentFolderName(WScript.ScriptFullName)

' Define o diretório de trabalho como a pasta do projeto
objShell.CurrentDirectory = strPath

' Executa o pythonw.exe do ambiente virtual passando o gui.main
' O "0" no final significa "janela oculta" (hide window) e o "False" significa não esperar o programa terminar
objShell.Run Chr(34) & strPath & "\.venv\Scripts\pythonw.exe" & Chr(34) & " -m gui.main", 0, False
