#pragma once
// Row recognition caching and event identity are deliberately separate.
// The first visible feed establishes a baseline; it is not new session loot.
struct FeedEvent {
 std::string item;int quantity=0;
 bool known()const{return !item.empty()&&quantity>0;}
 bool operator==(const FeedEvent&)const=default;
};
struct FeedUpdate {std::vector<FeedEvent> fresh;bool ambiguous=false;};
class FeedSnapshots {
 std::vector<FeedEvent> previous;std::vector<bool> pending;bool initialized=false;
public:
 FeedUpdate ingest(const std::vector<FeedEvent>& rows){
  FeedUpdate result;
  if(rows.size()>32){result.ambiguous=true;return result;}
  if(std::none_of(rows.begin(),rows.end(),[](auto& r){return r.known();}))return result;
  if(!initialized){previous=rows;pending.assign(rows.size(),false);initialized=true;return result;}
  size_t overlap=0,minimum=std::min({size_t(3),previous.size(),rows.size()});
  for(size_t size=std::min(previous.size(),rows.size());size>=minimum&&size>0;--size){
   size_t known=0;bool agrees=true;
   for(size_t i=0;i<size;i++){auto& a=previous[previous.size()-size+i];auto& b=rows[i];if(a.known()&&b.known()){known++;if(a!=b){agrees=false;break;}}}
   if(agrees&&known>=minimum){overlap=size;break;}
  }
  if(!overlap){previous=rows;pending.assign(rows.size(),false);result.ambiguous=true;return result;}
  std::vector<bool> flags(rows.size(),true);std::vector<FeedEvent> retained(rows.size());
  for(size_t i=0;i<overlap;i++){flags[i]=pending[previous.size()-overlap+i];retained[i]=previous[previous.size()-overlap+i];}
  for(size_t i=0;i<rows.size();i++){
   if(rows[i].known()){retained[i]=rows[i];if(flags[i]){result.fresh.push_back(rows[i]);flags[i]=false;}}
  }
  previous=std::move(retained);pending=std::move(flags);return result;
 }
};
