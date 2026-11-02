"""Install the application files separately from the protected user profile."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
from datetime import datetime

SOURCE=Path(__file__).resolve().parent
sys.path.insert(0,str(SOURCE/'desktop'))
from storage import data_root,backup_profile


def ps_string(value):return "'"+str(value).replace("'","''")+"'"


def install():
    if not (SOURCE/'desktop/assets/bdo-lite.ico').exists():
        sys.path.insert(0,str(SOURCE/'scripts'))
        from generate_assets import generate
        generate(SOURCE)
    profile=data_root();profile.mkdir(parents=True,exist_ok=True)
    backup=backup_profile(profile,'before-update')
    target=profile/'app'
    if (target/'desktop'/'app.py').exists():
        saved=profile/'backups'/('app-files-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        shutil.copytree(target,saved,ignore=shutil.ignore_patterns('__pycache__','*.sqlite3*','settings.json','runtime-status.json'))
    target.mkdir(exist_ok=True)
    for name in ('bdo-market-intelligence.html','fairycodex.html','README.md','RELEASE_NOTES.md','requirements.txt','RUN.bat','VERSION'):
        shutil.copy2(SOURCE/name,target/name)
    desktop=target/'desktop';desktop.mkdir(exist_ok=True)
    for source in (SOURCE/'desktop').glob('*.py'):shutil.copy2(source,desktop/source.name)
    shutil.copy2(SOURCE/'desktop'/'install-and-run.bat',desktop/'install-and-run.bat')
    shutil.copytree(SOURCE/'desktop'/'assets',desktop/'assets',dirs_exist_ok=True)
    interpreter=Path(sys.executable);windowed=interpreter.with_name('pythonw.exe')
    if not windowed.exists():windowed=interpreter
    script=("$visionShell=New-Object -ComObject WScript.Shell;"
            "$visionDesktop=[Environment]::GetFolderPath('Desktop');"
            "$visionLinkPath=Join-Path $visionDesktop 'BDO Vision.lnk';"
            "if(Test-Path -LiteralPath $visionLinkPath){Copy-Item -LiteralPath $visionLinkPath -Destination "+ps_string(backup/'previous-launcher.lnk')+";}"
            "$visionLink=$visionShell.CreateShortcut($visionLinkPath);"
            "$visionLink.TargetPath="+ps_string(windowed)+";"
            "$visionLink.Arguments="+ps_string('"'+str(desktop/'app.py')+'"')+";"
            "$visionLink.WorkingDirectory="+ps_string(desktop)+";"
            "$visionLink.IconLocation="+ps_string(desktop/'assets'/'bdo-lite.ico')+";"
            "$visionLink.Description='BDO Vision - saved loot, silver, crafting and grind sessions';"
            "$visionLink.Save()")
    subprocess.run(['powershell','-NoProfile','-NonInteractive','-WindowStyle','Hidden','-Command',script],check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    print('Installed application:',target)
    print('Protected history:',profile)
    print('Verified pre-update backup:',backup)
    print('Desktop shortcut: BDO Vision')


if __name__=='__main__':install()
