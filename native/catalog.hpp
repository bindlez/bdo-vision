// Embedded public item identities. The table is read-only executable data.
#pragma pack(push,1)
struct CatalogEntry {uint32_t name,key,length;uint64_t fingerprint;};
#pragma pack(pop)
struct Match {std::string name;double score=0,margin=0;};
class Catalog {
 const CatalogEntry* entries=nullptr;const char* blob=nullptr;uint32_t count=0;
 struct CachedMatch {std::string key;Match result;};
 mutable std::vector<CachedMatch> recent_matches;
 static char fold(char c){if(c=='5')return 's';if(c=='0'||c=='o'||c=='g'||c=='6')return 'o';if(c=='i'||c=='l'||c=='1'||c=='j')return 'i';if(c=='m'||c=='n')return 'n';if(c=='u'||c=='v')return 'u';return c;}
 static uint64_t signature(const std::string& s){uint64_t v=0;for(size_t i=1;i<s.size();i++)v|=uint64_t(1)<<((uint8_t(fold(s[i-1]))*37+uint8_t(fold(s[i]))*17)%64);return v;}
 static float substitution(char a,char b){if(a==b)return 0;if((a=='0'&&b=='o')||(a=='o'&&b=='0')||(a=='i'&&b=='l')||(a=='l'&&b=='i'))return .15f;if((a=='5'&&b=='s')||(a=='s'&&b=='5'))return .2f;if((a=='e'&&b=='s')||(a=='s'&&b=='e'))return .3f;if((a=='6'&&b=='g')||(a=='g'&&b=='6'))return .2f;if((a=='0'&&b=='g')||(a=='g'&&b=='0')||(a=='m'&&b=='n')||(a=='n'&&b=='m')||(a=='u'&&b=='v')||(a=='v'&&b=='u')||(a=='b'&&b=='h')||(a=='h'&&b=='b'))return .35f;return 1;}
 static float distance(const std::string& a,const char* b,size_t n){
  std::array<float,128> before{},after{};for(size_t j=0;j<=n;j++)before[j]=float(j);
  for(size_t i=1;i<=a.size();i++){after[0]=i<=3?float(i)*.25f:float(i)-2.25f;for(size_t j=1;j<=n;j++){after[j]=std::min({before[j]+1,after[j-1]+1,before[j-1]+substitution(a[i-1],b[j-1])});if(j>=2&&a[i-1]=='0'&&b[j-2]=='i'&&b[j-1]=='l')after[j]=std::min(after[j],before[j-2]+.35f);}std::swap(before,after);}return !a.empty()&&(a.back()=='l'||a.back()=='i'||a.back()=='r')?std::min(before[n],after[n]+.25f):before[n];
 }
public:
 static std::string normalize(const std::string& s){std::string key;for(unsigned char c:s)if((c>='a'&&c<='z')||(c>='0'&&c<='9'))key+=char(c);else if(c>='A'&&c<='Z')key+=char(c+32);else if(c=='!')key+='i';return key;}
 Catalog(){HRSRC res=FindResourceW(nullptr,MAKEINTRESOURCEW(101),RT_RCDATA);if(!res)return;DWORD size=SizeofResource(nullptr,res);auto ptr=(const uint8_t*)LockResource(LoadResource(nullptr,res));if(size<12||std::memcmp(ptr,"BVL1",4))return;uint32_t n=0,offset=0;std::memcpy(&n,ptr+4,4);std::memcpy(&offset,ptr+8,4);if(n>100000||offset!=12+n*sizeof(CatalogEntry)||offset>=size)return;entries=(const CatalogEntry*)(ptr+12);blob=(const char*)ptr+offset;count=n;for(uint32_t i=0;i<count;i++)if(entries[i].name>=size-offset||entries[i].key>=size-offset||entries[i].length>100){count=0;break;}}
 Match resolve(const std::string& raw)const{
  std::string q=normalize(raw);if(q.size()<3||q.size()>110||!count)return {};
  auto cached=std::find_if(recent_matches.begin(),recent_matches.end(),[&](auto& c){return c.key==q;});
  if(cached!=recent_matches.end())return cached->result;
  auto result=resolve_key(q);if(recent_matches.size()>=256)recent_matches.erase(recent_matches.begin());recent_matches.push_back({std::move(q),result});return result;
 }
 Match resolve_key(const std::string& q)const{
  Match result;
  struct Candidate{float rank=-1e9f;uint32_t index=0;};std::array<Candidate,128> candidates;uint64_t sig=signature(q);int qbits=std::popcount(sig);const char* exact=nullptr;bool ambiguous_exact=false;
  for(uint32_t i=0;i<count;i++){
   auto& e=entries[i];int len=std::abs(int(q.size())-int(e.length));if(len>6)continue;
   if(q==blob+e.key){if(exact&&std::strcmp(exact,blob+e.name))ambiguous_exact=true;exact=blob+e.name;continue;}
   if(q.size()<8)continue;
   int common=std::popcount(sig&e.fingerprint),different=std::popcount(sig^e.fingerprint);if(common<std::max(2,qbits-16))continue;
   float rank=float(common)-different*.35f-len*.65f;
   if(rank>candidates.back().rank){size_t pos=candidates.size()-1;while(pos&&rank>candidates[pos-1].rank){candidates[pos]=candidates[pos-1];--pos;}candidates[pos]={rank,i};}
  }
  if(exact)return ambiguous_exact?Match{}:Match{exact,1,1};
  double best=-1,next=-1;
  for(auto& c:candidates){if(c.rank<-1e8)continue;auto& e=entries[c.index];float d=distance(q,blob+e.key,e.length);double score=1-double(d)/std::max(q.size(),size_t(e.length));if(score>best){next=best;best=score;result.name=blob+e.name;}else if(score>next)next=score;}
  result.score=std::max(0.0,best);result.margin=best-next;if(best<.72||result.margin<.045||(best<.78&&(q.size()<11||result.margin<.10)))result.name.clear();return result;
 }
 uint32_t size()const{return count;}
};
struct Event {std::string item;int quantity=0;double score=0,margin=0;};
// Parse the entire token, never a numeric suffix of a malformed count.
static int quantity_token(const std::string& token){
 if(token.empty()||token.size()>9)return 0;
 int value=0,group=0,groups=0;
 for(char c:token){
  if(c==','){if(!group||(!groups&&group>3)||(groups&&group!=3))return 0;groups++;group=0;continue;}
  if(c<'0'||c>'9'||++group>7)return 0;
  value=value*10+c-'0';if(value>1000000)return 0;
 }
 return value>0&&(!groups||group==3)?value:0;
}
static Event extract(const std::string& raw,const Catalog& catalog){
 size_t end=raw.size();while(end&&raw[end-1]==' ')--end;
 if(end&&raw[end-1]=='.')--end; // BDO's sentence terminator, once only.
 while(end&&raw[end-1]==' ')--end;
 size_t begin=end;while(begin&&((raw[begin-1]>='0'&&raw[begin-1]<='9')||raw[begin-1]==','))--begin;
 if(begin==end){
  if(end&&raw[end-1]==']'){size_t opening=raw.rfind('[',end-1);if(opening!=std::string::npos&&opening+1<end-1){auto match=catalog.resolve(raw.substr(opening+1,end-opening-2));if(!match.name.empty()&&match.score>=.86&&match.margin>=.10)return {match.name,1,match.score,match.margin};}}
  return {};
 }
 size_t mark=begin;while(mark&&raw[mark-1]==' ')--mark;if(!mark||(raw[mark-1]!='x'&&raw[mark-1]!='X'))return {};
 int quantity=quantity_token(raw.substr(begin,end-begin));if(!quantity)return {};
 std::string name=raw.substr(0,mark-1);size_t bracket=name.find('[');if(bracket!=std::string::npos)name=name.substr(bracket+1);
 size_t closing=name.rfind(']');if(closing!=std::string::npos){if(name.find_first_not_of(' ',closing+1)!=std::string::npos)return {};name.resize(closing);}
 auto match=catalog.resolve(name);return {match.name,quantity,match.score,match.margin};
}
