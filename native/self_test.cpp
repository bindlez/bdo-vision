#include "engine.hpp"
#include "snapshots.hpp"
#include <iostream>
int main(){
 CoInitializeEx(nullptr,COINIT_MULTITHREADED);int failed=0,checks=0;
 auto check=[&](bool ok,const char* label){checks++;if(!ok){failed++;std::cerr<<"FAIL: "<<label<<'\n';}};
 for(auto [token,value]:std::vector<std::pair<std::string,int>>{{"1",1},{"42",42},{"1,000",1000},{"1,000,000",1000000},{"1000000",1000000},{"",0},{"0",0},{"1,00",0},{"12,34",0},{"1,",0},{",123",0},{"1,,000",0},{"1.5",0},{"2/3",0},{"1000001",0},{"999999999999999999",0}})check(quantity_token(token)==value,token.c_str());
 Catalog catalog;check(catalog.size()>0,"embedded catalog");
 for(auto& token:std::vector<std::string>{"0","1,00","1,","1.5","2/3","4 x5","1000001","999999999999999999","?"})check(extract("[Black Stone] x"+token,catalog).item.empty(),token.c_str());
 auto good=extract("[Black Stone] x1,234.",catalog);check(good.item=="Black Stone"&&good.quantity==1234,"grouped count");
 check(extract("[Desert Seal x12 Reward Bundle] x17",catalog).quantity==17,"external count");
 auto implicit=extract("[Laila's Petal].",catalog);check(implicit.item=="Laila's Petal"&&implicit.quantity==1,"implicit one with intact closing bracket");
 check(extract("[Laila's Petal",catalog).item.empty(),"missing closing bracket does not imply one");
 check(extract("[Laila's Petal] x?",catalog).item.empty(),"unreadable explicit quantity does not imply one");
 // Blank, random background and unrelated chat must not produce accepted rows.
 for(int scenario=0;scenario<3;scenario++){
  Image image;image.w=400;image.h=190;image.pixels.resize(size_t(image.w)*image.h);uint32_t seed=87921;
  for(auto& pixel:image.pixels){seed=seed*1664525+1013904223;pixel=scenario==0?0xff101010:scenario==1?seed:0xff998866;}
  NativeReader reader;auto result=reader.recognize(image);check(std::none_of(result.rows.begin(),result.rows.end(),[](auto& r){return !r.item.empty();}),"negative image");
  check(result.milliseconds>0,"negative image reports elapsed time");
 }
 FeedSnapshots feed;std::vector<FeedEvent> rows;for(int i=0;i<8;i++)rows.push_back({"sample",i+1});
 check(feed.ingest(rows).fresh.empty(),"initial baseline");
 check(feed.ingest(rows).fresh.empty(),"retained feed");
 check(feed.ingest({}).fresh.empty(),"blocked feed");
 rows.erase(rows.begin());rows.push_back({});check(feed.ingest(rows).fresh.empty(),"new uncertain hole");
 rows.back()={"recovered",9};auto recovered=feed.ingest(rows);check(recovered.fresh.size()==1&&recovered.fresh[0].quantity==9,"recover newly arrived hole once");
 check(feed.ingest(rows).fresh.empty(),"recovered hole never duplicated");
 auto ambiguous=feed.ingest({{"unrelated",1},{"unrelated",2},{"unrelated",3},{"unrelated",4}});check(ambiguous.ambiguous&&ambiguous.fresh.empty(),"no overlap never commits");
 FeedSnapshots long_run;rows.clear();for(int i=0;i<8;i++)rows.push_back({"loot",i+1});long_run.ingest(rows);int recorded=0;
 for(int i=0;i<2000;i++){rows.erase(rows.begin());rows.push_back({"loot",i+9});auto update=long_run.ingest(rows);recorded+=int(update.fresh.size());check(!update.ambiguous,"scrolling overlap");check(long_run.ingest(rows).fresh.empty(),"repeat after scroll");}
 check(recorded==2000,"2000 scrolling events exactly once");
 std::cout<<checks<<" checks, "<<failed<<" failures\n";CoUninitialize();return failed?1:0;
}
