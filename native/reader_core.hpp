#pragma once
#define NOMINMAX
#include <windows.h>
#include <wincodec.h>
#include <psapi.h>
#include <algorithm>
#include <array>
#include <bit>
#include <chrono>
#include <cmath>
#include <cstdint>
#include <cstdio>
#include <cstring>
#include <fstream>
#include <limits>
#include <string>
#include <vector>
#pragma comment(lib,"user32.lib")
#pragma comment(lib,"gdi32.lib")
#pragma comment(lib,"ole32.lib")
#pragma comment(lib,"windowscodecs.lib")
#pragma comment(lib,"psapi.lib")
struct Image { int w=0,h=0;std::vector<uint32_t> pixels; };
static Image load_image(const wchar_t* path){
    Image image;IWICImagingFactory* factory=nullptr;IWICBitmapDecoder* decoder=nullptr;IWICBitmapFrameDecode* frame=nullptr;IWICFormatConverter* converter=nullptr;
    HRESULT hr=CoCreateInstance(CLSID_WICImagingFactory,nullptr,CLSCTX_INPROC_SERVER,IID_PPV_ARGS(&factory));
    if(SUCCEEDED(hr))hr=factory->CreateDecoderFromFilename(path,nullptr,GENERIC_READ,WICDecodeMetadataCacheOnDemand,&decoder);
    if(SUCCEEDED(hr))hr=decoder->GetFrame(0,&frame);
    if(SUCCEEDED(hr))hr=factory->CreateFormatConverter(&converter);
    if(SUCCEEDED(hr))hr=converter->Initialize(frame,GUID_WICPixelFormat32bppBGRA,WICBitmapDitherTypeNone,nullptr,0,WICBitmapPaletteTypeCustom);
    UINT w=0,h=0;if(SUCCEEDED(hr))hr=converter->GetSize(&w,&h);
    if(SUCCEEDED(hr)&&w>0&&h>0&&w<=8192&&h<=8192&&uint64_t(w)*h<=16000000){image.w=int(w);image.h=int(h);image.pixels.resize(size_t(w)*h);hr=converter->CopyPixels(nullptr,w*4,UINT(image.pixels.size()*4),reinterpret_cast<BYTE*>(image.pixels.data()));}
    else hr=E_INVALIDARG;
    if(converter)converter->Release();if(frame)frame->Release();if(decoder)decoder->Release();if(factory)factory->Release();
    if(FAILED(hr))image={};return image;
}
struct Mask {
 int w=0,h=0,blocks=0;std::vector<uint8_t> p;std::vector<uint32_t> packed;
 bool at(int x,int y)const{return x>=0&&y>=0&&x<w&&y<h&&p[size_t(y)*w+x];}
 uint32_t column(int x,int y,int height=32)const{
  if(x<0||x>=w||height<=0||y>=h||y<=-32)return 0;
  if(y<0)return column(x,0,height+y)<<(-y);
  int block=y/32,shift=y%32;size_t i=size_t(x)*blocks+block;
  uint32_t value=packed[i]>>shift;if(shift&&block+1<blocks)value|=packed[i+1]<<(32-shift);
  return height>=32?value:value&((uint32_t(1)<<height)-1);
 }
};
static Mask text_mask(const Image& im,bool color){
 Mask m;m.w=im.w;m.h=im.h;m.blocks=(im.h+31)/32+1;m.p.resize(im.pixels.size());m.packed.resize(size_t(m.w)*m.blocks);
 auto peak=[&](int x,int y){if(x<0||y<0||x>=im.w||y>=im.h)return 255;uint32_t c=im.pixels[size_t(y)*im.w+x];return std::max({int(c&255),int((c>>8)&255),int((c>>16)&255)});};
 for(int y=0;y<im.h;y++)for(int x=0;x<im.w;x++){
  uint32_t c=im.pixels[size_t(y)*im.w+x];int r=(c>>16)&255,g=(c>>8)&255,b=c&255,lo=std::min({r,g,b}),hi=std::max({r,g,b});bool on=lo>80&&hi-lo<18;
  bool rarity=(r>g*1.7&&r>b*1.7&&r-g>65)||(b>r*1.2&&b>g*1.05)||(g>r*1.15&&g>b*1.3)||(r>130&&g>120&&b<std::min(r,g)*.6&&r>g*.8&&r<g*1.2);
  if(!on&&color&&rarity&&hi>100&&hi-lo>45){int nearby=255;for(auto [dx,dy]:std::array<std::pair<int,int>,8>{{{-2,0},{2,0},{0,-2},{0,2},{-1,-1},{1,1},{-1,1},{1,-1}}})nearby=std::min(nearby,peak(x+dx,y+dy));on=nearby<100&&hi-nearby>60;}
  m.p[size_t(y)*im.w+x]=uint8_t(on);if(on)m.packed[size_t(x)*m.blocks+y/32]|=uint32_t(1)<<(y%32);
 }
 return m;
}
struct Band {int top=0,bottom=0;};
static std::vector<Band> bands(const Mask& m){std::vector<Band> out;int start=-1,last=-1;for(int y=0;y<m.h;y++){int n=0;for(int x=5;x<std::min(128,m.w);x++)n+=m.at(x,y);if(n>=4){if(start<0)start=y;last=y;}else if(start>=0&&y-last>2){if(last-start>=5&&last-start<30)out.push_back({start,last+1});start=-1;}}if(start>=0&&last-start>=5)out.push_back({start,last+1});return out;}
struct Glyph {char c=0;int advance=0,height=0;std::vector<uint32_t> columns,expanded;int ink=0;};
struct Profile {std::wstring face;int height=14,weight=400;bool italic=false;int x=0,y=0;double error=999;int prefix_width=0;};
class Raster {
 HDC dc=nullptr;HBITMAP bitmap=nullptr,previous=nullptr;HFONT font=nullptr;HGDIOBJ previous_font=nullptr;uint32_t* data=nullptr;
public:
 Raster(){dc=CreateCompatibleDC(nullptr);BITMAPINFO bi{};bi.bmiHeader.biSize=sizeof(BITMAPINFOHEADER);bi.bmiHeader.biWidth=512;bi.bmiHeader.biHeight=-40;bi.bmiHeader.biPlanes=1;bi.bmiHeader.biBitCount=32;bi.bmiHeader.biCompression=BI_RGB;bitmap=CreateDIBSection(dc,&bi,DIB_RGB_COLORS,reinterpret_cast<void**>(&data),nullptr,0);previous=(HBITMAP)SelectObject(dc,bitmap);SetBkMode(dc,TRANSPARENT);SetTextColor(dc,RGB(255,255,255));}
 ~Raster(){if(font){SelectObject(dc,previous_font);DeleteObject(font);}SelectObject(dc,previous);DeleteObject(bitmap);DeleteDC(dc);}
 void select(const Profile& p){if(font){SelectObject(dc,previous_font);DeleteObject(font);}font=CreateFontW(-p.height,0,0,0,p.weight,p.italic,FALSE,FALSE,DEFAULT_CHARSET,OUT_TT_PRECIS,CLIP_DEFAULT_PRECIS,ANTIALIASED_QUALITY,DEFAULT_PITCH,p.face.c_str());previous_font=SelectObject(dc,font);}
 Glyph draw(const std::wstring& text,char c=0){std::fill(data,data+512*40,0);TextOutW(dc,0,0,text.data(),int(text.size()));GdiFlush();SIZE size{};GetTextExtentPoint32W(dc,text.data(),int(text.size()),&size);Glyph g;TEXTMETRICW tm{};GetTextMetricsW(dc,&tm);g.height=std::min(32,int(tm.tmHeight));g.c=c;g.advance=std::max(1,int(size.cx));g.columns.resize(std::min(510,g.advance+2));for(int x=0;x<int(g.columns.size());x++)for(int y=0;y<g.height;y++)if((data[y*512+x]&255)>100){g.columns[x]|=uint32_t(1)<<y;g.ink++;}g.expanded.resize(g.columns.size());for(size_t x=0;x<g.columns.size();x++){uint32_t v=g.columns[x];g.expanded[x]=v|(v<<1)|(v>>1)|(x?g.columns[x-1]:0)|(x+1<g.columns.size()?g.columns[x+1]:0);}return g;}
};
static double template_error(const Mask& m,const Glyph& g,int x,int y){
 int missing=0,extra=0,exact=0;
 for(int col=0;col<g.advance;col++){
  uint32_t want=g.columns[col],have=m.column(x+col,y,g.height);
  uint32_t expanded=have|m.column(x+col-1,y,g.height)|m.column(x+col+1,y,g.height)|m.column(x+col,y-1,g.height)|m.column(x+col,y+1,g.height);
  missing+=std::popcount(want&~expanded);extra+=std::popcount(have&~g.expanded[col]);exact+=std::popcount(want^have);
 }
 return (missing+.7*extra+.1*exact)/std::max(1,g.ink);
}
static std::wstring only_face;static int only_height=0,only_weight=0;static bool use_color=false;
static Profile calibrate(const Mask& neutral,const std::vector<Band>& rows){
 Profile best;Raster raster;if(rows.empty())return best;
 std::array<const wchar_t*,8> faces{L"Verdana",L"Times New Roman",L"Segoe UI",L"Georgia",L"Arial",L"Tahoma",L"Calibri",L"Trebuchet MS"};
 for(auto face:faces)for(int italic=0;italic<2;italic++)for(int weight:{400,700})for(int height=11;height<=18;height++){
  if((!only_face.empty()&&only_face!=face)||(only_height&&height!=only_height)||(only_weight&&weight!=only_weight))continue;
  Profile p{face,height,weight,bool(italic)};raster.select(p);auto glyph=raster.draw(L"You have obtained");
  for(int y=rows[0].top-8;y<=rows[0].top+1;y++)for(int x=4;x<=12;x++){
   double e=template_error(neutral,glyph,x,y);if(e<best.error){best=p;best.error=e;best.x=x;best.y=y;best.prefix_width=glyph.advance;}
  }
 }
 return best;
}
struct Span{int start=0,end=0;char c=0;};
struct Read {std::string text;double cost=0;std::vector<Span> spans;};
static Read decode(const Mask& m,const std::vector<Glyph>& atlas,int x0,int y,int limit=-1){
 int end=limit<0?m.w:std::min(m.w,limit);while(end>x0+1&&std::popcount(m.column(end-1,y,atlas.front().height))<2)end--;
 int width=end-x0;if(width<=0)return {};std::vector<double> costs(width+1,1e15);std::vector<int> back(width+1,-1);std::vector<char> chars(width+1,0);costs[0]=0;
 // All glyphs in this atlas share one text height. Build the observed columns
 // once per row rather than performing five packed-mask lookups per glyph.
 std::vector<uint32_t> observed(width+2),expanded_row(width+2);
 for(int i=0;i<width+2;i++){
  uint32_t have=m.column(x0+i,y,atlas.front().height);observed[i]=have;
  expanded_row[i]=have|m.column(x0+i-1,y,atlas.front().height)|m.column(x0+i+1,y,atlas.front().height)|m.column(x0+i,y-1,atlas.front().height)|m.column(x0+i,y+1,atlas.front().height);
 }
 for(int x=0;x<width;x++)if(costs[x]<1e14){
  for(auto& g:atlas){
   int missing=0,extra=0,exact=0,ink=0;
   for(int col=0;col<std::min(g.advance+1,width-x);col++){
    uint32_t want=col<int(g.columns.size())?g.columns[col]:0,have=observed[x+col];
    uint32_t expanded=expanded_row[x+col];
    uint32_t expected=col<int(g.expanded.size())?g.expanded[col]:0;
    missing+=std::popcount(want&~expanded);extra+=std::popcount(have&~expected);exact+=std::popcount(want^have);ink+=std::popcount(have);
    int advance=col+1,delta=advance-g.advance;if(delta < -1)continue;
   if(g.c==' '&&ink>2)continue;
   double cost=costs[x]+missing*1.2+extra*2+.25*exact+std::abs(delta)*2.2+(g.c==' '?0:4.0);
   if(cost<costs[x+advance]){costs[x+advance]=cost;back[x+advance]=x;chars[x+advance]=g.c;}
   }
  }
 }
 Read r;r.cost=costs[width];for(int x=width;x>0&&back[x]>=0;x=back[x]){r.text.push_back(chars[x]);r.spans.push_back({x0+back[x],x0+x,chars[x]});}std::reverse(r.text.begin(),r.text.end());std::reverse(r.spans.begin(),r.spans.end());return r;
}
static std::string utf8(const std::wstring& s){int n=WideCharToMultiByte(CP_UTF8,0,s.data(),int(s.size()),nullptr,0,nullptr,nullptr);std::string out(n,0);WideCharToMultiByte(CP_UTF8,0,s.data(),int(s.size()),out.data(),n,nullptr,nullptr);return out;}
static std::string escape(const std::string& s){std::string out;for(unsigned char c:s){if(c=='"'||c=='\\'){out+='\\';out+=char(c);}else if(c=='\n')out+="\\n";else if(c>=32)out+=char(c);}return out;}
#include "catalog.hpp"
