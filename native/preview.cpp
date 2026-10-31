// Isolated, read-only native reader lab. No ledger, bridge or profile writes.
#include "engine.hpp"
#include <commdlg.h>
#include <tlhelp32.h>
#include <thread>
#include <mutex>
#include <condition_variable>
#include <sstream>
#include <shellapi.h>
#pragma comment(lib,"comdlg32.lib")
#pragma comment(lib,"shell32.lib")
namespace {
constexpr UINT ResultMessage=WM_APP+1;
constexpr int Select=100,Toggle=101,Open=102;
HWND main_window=nullptr,output=nullptr,status=nullptr,toggle=nullptr;
HFONT body_font=nullptr,title_font=nullptr;
HBRUSH background=nullptr,panel=nullptr;
std::mutex work_mutex;std::condition_variable changed;
bool stopping=false,running=false,pending_image=false,smoke=false;RECT region{};
std::wstring image_path;std::thread worker;
POINT drag_start{};RECT drag_rect{};bool dragging=false;
COLORREF bg=RGB(12,10,19),card=RGB(22,19,33),text=RGB(232,229,245),muted=RGB(174,164,198);
struct Delivery {std::wstring text,status;int accepted=0,visible=0;double ms=0;SIZE_T private_bytes=0,working_set=0;};
std::wstring wide(const std::string& s){int n=MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),int(s.size()),nullptr,0);std::wstring r(n,0);if(n)MultiByteToWideChar(CP_UTF8,MB_ERR_INVALID_CHARS,s.data(),int(s.size()),r.data(),n);return r;}
void deliver(Delivery d){auto message=new Delivery(std::move(d));if(!PostMessageW(main_window,ResultMessage,0,LPARAM(message)))delete message;}
bool game_foreground(RECT r){
 HWND foreground=GetForegroundWindow();if(!foreground||IsIconic(foreground))return false;
 DWORD pid=0;GetWindowThreadProcessId(foreground,&pid);bool game=false;
 static DWORD cached_pid=0;static bool cached_game=false;static ULONGLONG checked=0;
 if(pid==cached_pid&&GetTickCount64()-checked<5000)game=cached_game;
 else {
 HANDLE snapshot=CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS,0);
 if(snapshot!=INVALID_HANDLE_VALUE){PROCESSENTRY32W p{};p.dwSize=sizeof(p);if(Process32FirstW(snapshot,&p))do{if(p.th32ProcessID==pid){game=!_wcsicmp(p.szExeFile,L"BlackDesert64.exe")||!_wcsicmp(p.szExeFile,L"BlackDesert32.exe");break;}}while(Process32NextW(snapshot,&p));CloseHandle(snapshot);}
 cached_pid=pid;cached_game=game;checked=GetTickCount64();
 }
 if(!game)return false;
 // A covered corner or center is enough to suspend reading. No hidden capture.
 for(POINT p:std::array<POINT,5>{{{r.left,r.top},{r.right-1,r.top},{r.left,r.bottom-1},{r.right-1,r.bottom-1},{(r.left+r.right)/2,(r.top+r.bottom)/2}}})
  if(GetAncestor(WindowFromPoint(p),GA_ROOT)!=foreground)return false;
 return true;
}
class Capture {
 HDC screen=nullptr,dc=nullptr;HBITMAP bitmap=nullptr;HGDIOBJ prior=nullptr;void* bits=nullptr;int w=0,h=0;
 void clear(){if(prior&&dc)SelectObject(dc,prior);if(bitmap)DeleteObject(bitmap);if(dc)DeleteDC(dc);if(screen)ReleaseDC(nullptr,screen);screen=dc=nullptr;bitmap=nullptr;prior=nullptr;bits=nullptr;w=h=0;}
public:
 ~Capture(){clear();}
 bool get(RECT r,Image& image){int nw=r.right-r.left,nh=r.bottom-r.top;if(nw<80||nh<20||nw>1600||nh>600)return false;
  if(nw!=w||nh!=h){clear();screen=GetDC(nullptr);dc=CreateCompatibleDC(screen);BITMAPINFO info{};info.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);info.bmiHeader.biWidth=nw;info.bmiHeader.biHeight=-nh;info.bmiHeader.biPlanes=1;info.bmiHeader.biBitCount=32;info.bmiHeader.biCompression=BI_RGB;bitmap=CreateDIBSection(screen,&info,DIB_RGB_COLORS,&bits,nullptr,0);if(!bitmap||!dc){clear();return false;}prior=SelectObject(dc,bitmap);w=nw;h=nh;image.w=w;image.h=h;image.pixels.resize(size_t(w)*h);}
  if(!BitBlt(dc,0,0,w,h,screen,r.left,r.top,SRCCOPY|CAPTUREBLT))return false;GdiFlush();image.w=w;image.h=h;image.pixels.resize(size_t(w)*h);std::memcpy(image.pixels.data(),bits,image.pixels.size()*4);return true;
 }
};
void work(){
 CoInitializeEx(nullptr,COINIT_MULTITHREADED);NativeReader reader;Capture capture;Image frame;
 std::unique_lock lock(work_mutex);
 while(!stopping){changed.wait(lock,[]{return stopping||running||pending_image;});if(stopping)break;
  bool from_file=pending_image;std::wstring path=image_path;pending_image=false;RECT box=region;lock.unlock();
  if(from_file)frame=load_image(path.c_str());
  bool visible=from_file||game_foreground(box);
  if(!visible)deliver({L"Reading is suspended while BDO is covered, minimized or in the background.\r\n\r\nNo loot or silver is inferred.",L"PAUSED · BDO is not fully visible"});
  else if((from_file&&frame.w)||(!from_file&&capture.get(box,frame))){
   auto report=reader.recognize(frame);std::wstringstream rows;int accepted=0;
   for(auto& row:report.rows){if(!row.item.empty()){rows<<L"  "<<wide(row.item)<<L"   × "<<row.quantity<<L"\r\n\r\n";accepted++;}else rows<<L"  Uncertain row — withheld\r\n\r\n";}
   if(report.rows.empty())rows<<L"No readable item notifications.\r\n\r\nSelect only the system text feed, including ‘You have obtained’.";
   PROCESS_MEMORY_COUNTERS_EX memory{};GetProcessMemoryInfo(GetCurrentProcess(),(PROCESS_MEMORY_COUNTERS*)&memory,sizeof(memory));
   wchar_t stats[256];swprintf_s(stats,L"%d / %zu rows · %.1f ms · %d reused · %.1f MiB private · %.1f MiB working set",accepted,report.rows.size(),report.milliseconds,report.cache_hits,memory.PrivateUsage/1048576.0,memory.WorkingSetSize/1048576.0);
   deliver({rows.str(),stats,accepted,int(report.rows.size()),report.milliseconds,memory.PrivateUsage,memory.WorkingSetSize});
  }else deliver({L"Unable to read the selected image or area.",L"Capture unavailable"});
  lock.lock();if(running)changed.wait_for(lock,std::chrono::milliseconds(500),[]{return stopping||!running||pending_image;});
 }
 lock.unlock();CoUninitialize();
}
LRESULT CALLBACK picker(HWND window,UINT message,WPARAM wp,LPARAM lp){
 if(message==WM_LBUTTONDOWN){dragging=true;GetCursorPos(&drag_start);SetCapture(window);return 0;}
 if(message==WM_MOUSEMOVE&&dragging){POINT now;GetCursorPos(&now);drag_rect={std::min(now.x,drag_start.x),std::min(now.y,drag_start.y),std::max(now.x,drag_start.x),std::max(now.y,drag_start.y)};InvalidateRect(window,nullptr,TRUE);return 0;}
 if(message==WM_LBUTTONUP){ReleaseCapture();dragging=false;RECT chosen=drag_rect;int w=chosen.right-chosen.left,h=chosen.bottom-chosen.top;DestroyWindow(window);ShowWindow(main_window,SW_RESTORE);if(w>=80&&h>=20&&w<=1600&&h<=600){std::lock_guard lock(work_mutex);region=chosen;SetWindowTextW(status,L"Area selected. Click Start, then bring BDO to the front.");EnableWindow(toggle,TRUE);}else SetWindowTextW(status,L"Choose an area between 80 × 20 and 1600 × 600 pixels.");return 0;}
 if(message==WM_KEYDOWN&&wp==VK_ESCAPE){dragging=false;DestroyWindow(window);ShowWindow(main_window,SW_RESTORE);return 0;}
 if(message==WM_PAINT){PAINTSTRUCT ps;HDC dc=BeginPaint(window,&ps);SetTextColor(dc,RGB(255,255,255));SetBkMode(dc,TRANSPARENT);const wchar_t* hint=L"Drag around the system item text feed. Escape cancels.";TextOutW(dc,30,30,hint,int(wcslen(hint)));if(dragging){RECT r=drag_rect;OffsetRect(&r,-GetSystemMetrics(SM_XVIRTUALSCREEN),-GetSystemMetrics(SM_YVIRTUALSCREEN));HBRUSH brush=CreateSolidBrush(RGB(184,125,255));FrameRect(dc,&r,brush);DeleteObject(brush);}EndPaint(window,&ps);return 0;}
 return DefWindowProcW(window,message,wp,lp);
}
void select_area(){
 {std::lock_guard lock(work_mutex);running=false;}changed.notify_one();SetWindowTextW(toggle,L"Start reader");ShowWindow(main_window,SW_HIDE);drag_rect={};
 HWND overlay=CreateWindowExW(WS_EX_TOPMOST|WS_EX_LAYERED,L"BDOVisionAreaPicker",L"Select text feed",WS_POPUP,GetSystemMetrics(SM_XVIRTUALSCREEN),GetSystemMetrics(SM_YVIRTUALSCREEN),GetSystemMetrics(SM_CXVIRTUALSCREEN),GetSystemMetrics(SM_CYVIRTUALSCREEN),nullptr,nullptr,GetModuleHandleW(nullptr),nullptr);
 if(!overlay){ShowWindow(main_window,SW_RESTORE);return;}SetLayeredWindowAttributes(overlay,0,150,LWA_ALPHA);ShowWindow(overlay,SW_SHOW);SetForegroundWindow(overlay);SetFocus(overlay);
}
LRESULT CALLBACK window_proc(HWND window,UINT message,WPARAM wp,LPARAM lp){
 if(message==WM_CREATE){
  auto control=[&](const wchar_t* cls,const wchar_t* label,DWORD style,int id){HWND child=CreateWindowExW(0,cls,label,WS_CHILD|WS_VISIBLE|style,0,0,0,0,window,HMENU(INT_PTR(id)),nullptr,nullptr);SendMessageW(child,WM_SETFONT,WPARAM(body_font),TRUE);return child;};
  control(L"BUTTON",L"Select text feed",BS_OWNERDRAW,Select);toggle=control(L"BUTTON",L"Start reader",BS_OWNERDRAW,Toggle);EnableWindow(toggle,FALSE);control(L"BUTTON",L"Open saved image",BS_OWNERDRAW,Open);
  output=control(L"EDIT",L"Choose a saved image or select BDO’s system text feed.\r\n\r\nThis preview reads visible rows only. Your existing app, settings and history stay safe.",ES_MULTILINE|ES_READONLY|ES_AUTOVSCROLL|WS_VSCROLL,103);
  status=control(L"STATIC",L"Ready · capture is off",SS_LEFT,104);return 0;
 }
 if(message==WM_SIZE){int w=LOWORD(lp),h=HIWORD(lp);MoveWindow(GetDlgItem(window,Select),28,142,170,38,TRUE);MoveWindow(toggle,210,142,160,38,TRUE);MoveWindow(GetDlgItem(window,Open),382,142,180,38,TRUE);MoveWindow(output,28,238,w-56,std::max(60,h-300),TRUE);MoveWindow(status,28,h-45,w-56,30,TRUE);return 0;}
 if(message==WM_GETMINMAXINFO){auto info=reinterpret_cast<MINMAXINFO*>(lp);info->ptMinTrackSize={650,480};return 0;}
 if(message==WM_COMMAND){int id=LOWORD(wp);if(id==Select)select_area();if(id==Toggle){{std::lock_guard lock(work_mutex);running=!running;SetWindowTextW(toggle,running?L"Pause reader":L"Start reader");}changed.notify_one();}if(id==Open){wchar_t path[32768]={};OPENFILENAMEW dialog{};dialog.lStructSize=sizeof(dialog);dialog.hwndOwner=window;dialog.lpstrFilter=L"Images\0*.png;*.bmp;*.jpg;*.jpeg\0\0";dialog.lpstrFile=path;dialog.nMaxFile=32768;dialog.Flags=OFN_FILEMUSTEXIST|OFN_NOCHANGEDIR;if(GetOpenFileNameW(&dialog)){std::lock_guard lock(work_mutex);running=false;pending_image=true;image_path=path;SetWindowTextW(toggle,L"Start reader");changed.notify_one();}}return 0;}
 if(message==ResultMessage){auto result=reinterpret_cast<Delivery*>(lp);SetWindowTextW(output,result->text.c_str());SetWindowTextW(status,result->status.c_str());if(smoke){std::printf("{\"accepted_rows\":%d,\"visible_rows\":%d,\"reader_ms\":%.3f,\"gui_private_bytes\":%llu,\"gui_working_set_bytes\":%llu}\n",result->accepted,result->visible,result->ms,(unsigned long long)result->private_bytes,(unsigned long long)result->working_set);std::fflush(stdout);DestroyWindow(window);}delete result;return 0;}
 if(message==WM_DRAWITEM){auto item=reinterpret_cast<DRAWITEMSTRUCT*>(lp);bool disabled=item->itemState&ODS_DISABLED,pressed=item->itemState&ODS_SELECTED;HBRUSH fill=CreateSolidBrush(disabled?RGB(24,21,34):pressed?RGB(81,48,124):RGB(47,32,69));FillRect(item->hDC,&item->rcItem,fill);DeleteObject(fill);HBRUSH border=CreateSolidBrush(disabled?RGB(49,42,63):RGB(125,86,166));FrameRect(item->hDC,&item->rcItem,border);DeleteObject(border);wchar_t label[80];GetWindowTextW(item->hwndItem,label,80);SetBkMode(item->hDC,TRANSPARENT);SetTextColor(item->hDC,disabled?muted:text);SelectObject(item->hDC,body_font);DrawTextW(item->hDC,label,-1,&item->rcItem,DT_CENTER|DT_VCENTER|DT_SINGLELINE);if(item->itemState&ODS_FOCUS){RECT focus=item->rcItem;InflateRect(&focus,-4,-4);DrawFocusRect(item->hDC,&focus);}return TRUE;}
 if(message==WM_CTLCOLORSTATIC||message==WM_CTLCOLOREDIT){HDC dc=HDC(wp);SetTextColor(dc,lp==LPARAM(status)?muted:text);SetBkColor(dc,lp==LPARAM(output)?card:bg);return LRESULT(lp==LPARAM(output)?panel:background);}
 if(message==WM_PAINT){PAINTSTRUCT ps;HDC dc=BeginPaint(window,&ps);SetBkMode(dc,TRANSPARENT);SelectObject(dc,title_font);SetTextColor(dc,text);TextOutW(dc,28,26,L"BDO VISION",10);SelectObject(dc,body_font);SetTextColor(dc,RGB(187,145,255));TextOutW(dc,28,70,L"NATIVE READER LAB  /  READ-ONLY PREVIEW",39);SetTextColor(dc,muted);const wchar_t* detail=L"Custom recognition. One executable. No separate installations.";TextOutW(dc,28,101,detail,int(wcslen(detail)));const wchar_t* label=L"VISIBLE ROWS · NOT RECORDED LOOT OR SESSION TOTALS";TextOutW(dc,28,205,label,int(wcslen(label)));EndPaint(window,&ps);return 0;}
 if(message==WM_CLOSE){DestroyWindow(window);return 0;}if(message==WM_DESTROY){{std::lock_guard lock(work_mutex);stopping=true;running=false;}changed.notify_one();PostQuitMessage(0);return 0;}
 return DefWindowProcW(window,message,wp,lp);
}
}
int WINAPI wWinMain(HINSTANCE instance,HINSTANCE,LPWSTR,int show){
 SetProcessDPIAware();background=CreateSolidBrush(bg);panel=CreateSolidBrush(card);body_font=CreateFontW(-16,0,0,0,400,FALSE,FALSE,FALSE,DEFAULT_CHARSET,0,0,CLEARTYPE_QUALITY,0,L"Segoe UI");title_font=CreateFontW(-32,0,0,0,700,FALSE,FALSE,FALSE,DEFAULT_CHARSET,0,0,CLEARTYPE_QUALITY,0,L"Segoe UI");
 WNDCLASSW wc{};wc.hInstance=instance;wc.lpfnWndProc=window_proc;wc.lpszClassName=L"BDOVisionNativeLab";wc.hbrBackground=background;wc.hCursor=LoadCursor(nullptr,IDC_ARROW);RegisterClassW(&wc);wc.lpfnWndProc=picker;wc.lpszClassName=L"BDOVisionAreaPicker";wc.hbrBackground=HBRUSH(GetStockObject(BLACK_BRUSH));wc.hCursor=LoadCursor(nullptr,IDC_CROSS);RegisterClassW(&wc);
 main_window=CreateWindowW(L"BDOVisionNativeLab",L"BDO Vision · Native lab 01",WS_OVERLAPPEDWINDOW,CW_USEDEFAULT,CW_USEDEFAULT,820,680,nullptr,nullptr,instance,nullptr);if(!main_window)return 1;
 int argc=0;LPWSTR* argv=CommandLineToArgvW(GetCommandLineW(),&argc);if(argv&&argc==3&&(!wcscmp(argv[1],L"--smoke")||!wcscmp(argv[1],L"--image"))){smoke=!wcscmp(argv[1],L"--smoke");pending_image=true;image_path=argv[2];}if(argv)LocalFree(argv);
 worker=std::thread(work);ShowWindow(main_window,smoke?SW_HIDE:show);MSG message;while(GetMessageW(&message,nullptr,0,0)>0){TranslateMessage(&message);DispatchMessageW(&message);}worker.join();while(PeekMessageW(&message,nullptr,ResultMessage,ResultMessage,PM_REMOVE))delete reinterpret_cast<Delivery*>(message.lParam);DeleteObject(body_font);DeleteObject(title_font);DeleteObject(background);DeleteObject(panel);return 0;
}
