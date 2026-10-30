"""Read Windows process memory without adding a runtime dependency."""
import ctypes,os,time
from ctypes import wintypes

def memory_bytes(pid=None):
    if os.name!='nt':return {}
    class Counters(ctypes.Structure):
        _fields_=[('cb',wintypes.DWORD),('PageFaultCount',wintypes.DWORD)]+[
            (name,ctypes.c_size_t) for name in ('PeakWorkingSetSize','WorkingSetSize',
            'QuotaPeakPagedPoolUsage','QuotaPagedPoolUsage','QuotaPeakNonPagedPoolUsage',
            'QuotaNonPagedPoolUsage','PagefileUsage','PeakPagefileUsage','PrivateUsage')]
    kernel=ctypes.WinDLL('kernel32',use_last_error=True)
    kernel.GetCurrentProcess.restype=wintypes.HANDLE
    kernel.OpenProcess.argtypes=[wintypes.DWORD,wintypes.BOOL,wintypes.DWORD]
    kernel.OpenProcess.restype=wintypes.HANDLE
    kernel.CloseHandle.argtypes=[wintypes.HANDLE]
    handle=kernel.OpenProcess(0x410,False,pid) if pid else kernel.GetCurrentProcess()
    if not handle:raise OSError(ctypes.get_last_error(),'Cannot inspect process')
    counters=Counters();counters.cb=ctypes.sizeof(counters)
    psapi=ctypes.WinDLL('psapi',use_last_error=True)
    psapi.GetProcessMemoryInfo.argtypes=[wintypes.HANDLE,ctypes.POINTER(Counters),wintypes.DWORD]
    try:
        if not psapi.GetProcessMemoryInfo(handle,ctypes.byref(counters),counters.cb):
            raise OSError(ctypes.get_last_error(),'Cannot read process memory')
        return {'private_bytes':counters.PrivateUsage,'working_set_bytes':counters.WorkingSetSize,
                'peak_working_set_bytes':counters.PeakWorkingSetSize}
    finally:
        if pid:kernel.CloseHandle(handle)

if __name__=='__main__':
    import argparse,json
    parser=argparse.ArgumentParser();parser.add_argument('--pid',type=int)
    parser.add_argument('--samples',type=int,default=1);parser.add_argument('--interval',type=float,default=1)
    args=parser.parse_args();records=[]
    for index in range(args.samples):
        records.append({'at':time.time(),**memory_bytes(args.pid)})
        if index+1<args.samples:time.sleep(args.interval)
    print(json.dumps(records,indent=2))
