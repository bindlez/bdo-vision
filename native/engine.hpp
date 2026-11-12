#pragma once
#include "reader_core.hpp"
struct Observation {std::string item;int quantity=0;bool cached=false;int name_votes=0,quantity_votes=0;std::string raw;};
struct FrameRead {std::vector<Observation> rows;double milliseconds=0;int cache_hits=0;double header_error=999;bool calibrated=false;};
class NativeReader {
 struct Model{Profile p;std::vector<Glyph> atlas,digits;};
 struct Cached {std::vector<uint32_t> mask;Observation result;uint64_t hash=0;};
 std::vector<Model> models;std::vector<Cached> cache;Catalog catalog;Profile header;Glyph header_glyph;int width=0,height=0;bool ready=false;
 static Model make_model(const Mask& mask,const std::vector<Band>& rows,const wchar_t* face,int size,int weight){
  only_face=face;only_height=std::clamp(size,11,18);only_weight=weight;Model m;m.p=calibrate(mask,rows);Raster raster;raster.select(m.p);for(char c=32;c<=126;c++){auto g=raster.draw(std::wstring(1,wchar_t(c)),c);if((c>='0'&&c<='9')||c==' '||c=='.'||c==',')m.digits.push_back(g);m.atlas.push_back(std::move(g));}return m;
 }
 Event read_model(const Mask& mask,const Model& model,int top,std::string& raw){
  int y=model.p.y+top;auto r=decode(mask,model.atlas,model.p.x+model.p.prefix_width,y);
  for(size_t z=r.spans.size();z>0;z--)if(r.spans[z-1].c=='x'||r.spans[z-1].c=='X'){
   auto n=decode(mask,model.digits,r.spans[z-1].end,y,r.spans.back().end);r.text=r.text.substr(0,z)+n.text;break;
  }
  raw=r.text;return extract(r.text,catalog);
 }
 static Observation vote(const std::vector<Event>& evidence){
  std::vector<std::pair<std::string,int>> names;std::vector<std::pair<int,int>> counts;
  for(auto& e:evidence){if(!e.item.empty()){auto f=std::find_if(names.begin(),names.end(),[&](auto& n){return n.first==e.item;});if(f==names.end())names.push_back({e.item,1});else ++f->second;}if(e.quantity>0){auto f=std::find_if(counts.begin(),counts.end(),[&](auto& n){return n.first==e.quantity;});if(f==counts.end())counts.push_back({e.quantity,1});else ++f->second;}}
  auto order=[](auto& a,auto& b){return a.second>b.second;};std::sort(names.begin(),names.end(),order);std::sort(counts.begin(),counts.end(),order);
  Observation r;if(!names.empty())r.name_votes=names[0].second;if(!counts.empty())r.quantity_votes=counts[0].second;
  if(names.empty()||counts.empty()||r.name_votes<2||r.quantity_votes<2||(names.size()>1&&names[1].second==r.name_votes)||(counts.size()>1&&counts[1].second==r.quantity_votes))return r;
  r.item=names[0].first;r.quantity=counts[0].first;return r;
 }
public:
 FrameRead recognize(const Image& image){
  auto start=std::chrono::steady_clock::now();FrameRead result;auto neutral=text_mask(image,false);auto lines=bands(neutral);auto colored=text_mask(image,true);
  if(lines.empty()){result.milliseconds=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();return result;}
  if(!ready||image.w!=width||image.h!=height){
   only_face.clear();only_height=0;only_weight=0;header=calibrate(neutral,lines);models.clear();cache.clear();width=image.w;height=image.h;
   if(header.error>.22){result.header_error=header.error;result.milliseconds=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();return result;}
   Raster raster;raster.select(header);header_glyph=raster.draw(L"You have obtained");
   double scale=double(header.height)/14;models.push_back(make_model(neutral,lines,L"Times New Roman",int(std::round(15*scale)),400));models.push_back(make_model(neutral,lines,L"Arial",int(std::round(14*scale)),400));models.push_back(make_model(neutral,lines,L"Trebuchet MS",int(std::round(13*scale)),400));
   ready=true;
  }
  result.header_error=header.error;result.calibrated=true;
  for(auto& band:lines){
   if(template_error(neutral,header_glyph,header.x,header.y+band.top-lines[0].top)>.24){result.rows.push_back({});continue;}
   std::vector<uint32_t> patch;patch.reserve(size_t(image.w)*2);uint64_t hash=1469598103934665603ull;
   for(int x=0;x<image.w;x++){uint32_t a=neutral.column(x,band.top-4,28),b=colored.column(x,band.top-4,28);patch.push_back(a);patch.push_back(b);hash=(hash^a)*1099511628211ull;hash=(hash^b)*1099511628211ull;}
   auto prior=std::find_if(cache.begin(),cache.end(),[&](auto& c){return c.hash==hash&&c.mask==patch;});
   if(prior!=cache.end()){auto old=prior->result;old.cached=true;result.cache_hits++;result.rows.push_back(std::move(old));continue;}
   std::vector<Event> evidence;std::string raw;for(int i=0;i<3;i++)evidence.push_back(read_model(neutral,models[i],band.top-lines[0].top,raw));Observation row=vote(evidence);
   if(row.item.empty()){
    if(models.size()==3){double scale=double(header.height)/14;models.push_back(make_model(neutral,lines,L"Georgia",int(std::round(13*scale)),400));models.push_back(make_model(neutral,lines,L"Verdana",int(std::round(12*scale)),400));models.push_back(make_model(neutral,lines,L"Tahoma",int(std::round(12*scale)),700));models.push_back(make_model(neutral,lines,L"Segoe UI",int(std::round(13*scale)),400));models.push_back(make_model(neutral,lines,L"Calibri",int(std::round(14*scale)),700));}
    for(size_t i=3;i<models.size();i++)evidence.push_back(read_model(colored,models[i],band.top-lines[0].top,raw));row=vote(evidence);
   }
   row.raw=raw;if(cache.size()>=16)cache.erase(cache.begin());cache.push_back({std::move(patch),row,hash});result.rows.push_back(std::move(row));
  }
  result.milliseconds=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-start).count();return result;
 }
};
