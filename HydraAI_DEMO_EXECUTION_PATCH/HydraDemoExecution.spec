# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all
po_datas, po_binaries, po_hidden = collect_all("pocket_option")
kr_datas, kr_binaries, kr_hidden = collect_all("keyring")
a = Analysis(["demo_execution_worker.py"], pathex=[], binaries=po_binaries+kr_binaries,
    datas=po_datas+kr_datas, hiddenimports=po_hidden+kr_hidden, hookspath=[],
    hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="HydraDemoExecution",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True, console=True,
    disable_windowed_traceback=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=True, upx_exclude=[], name="HydraDemoExecution")
