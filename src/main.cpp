// TESSITURA — Laboratorio de trajetorias e relacoes socioecologicas
// C++26 | nucleo minimo local-first | nunca promove inferencias automaticamente.
#define BOOST_JSON_NO_LIB
#include <boost/json/src.hpp>
#include <boost/asio.hpp>
#include <boost/beast.hpp>
#include <sqlite3.h>
#include <openssl/sha.h>
#include <algorithm>
#include <array>
#include <charconv>
#include <cctype>
#include <filesystem>
#include <fstream>
#include <iostream>
#include <memory>
#include <optional>
#include <regex>
#include <stdexcept>
#include <string>
#include <string_view>
#include <vector>

namespace fs = std::filesystem;
namespace json = boost::json;
namespace asio = boost::asio;
namespace beast = boost::beast;
namespace http = beast::http;
using tcp = asio::ip::tcp;
using Obj = json::object;
using Arr = json::array;

static std::string read_text(const fs::path& p) {
    std::ifstream f(p, std::ios::binary);
    if (!f) throw std::runtime_error("Arquivo nao encontrado: " + p.string());
    return std::string(std::istreambuf_iterator<char>(f), {});
}
static std::string sha256hex(std::string_view text) {
    std::array<unsigned char, SHA256_DIGEST_LENGTH> digest{};
    SHA256(reinterpret_cast<const unsigned char*>(text.data()), text.size(), digest.data());
    constexpr char hex[] = "0123456789abcdef";
    std::string out; out.reserve(digest.size() * 2);
    for (auto b : digest) { out.push_back(hex[b >> 4]); out.push_back(hex[b & 15]); }
    return out;
}
static std::string field(const Obj& o, std::string_view key, std::size_t max = 2000) {
    auto it = o.find(key);
    if (it == o.end() || it->value().is_null()) return {};
    if (!it->value().is_string()) throw std::invalid_argument("Campo deve ser texto: " + std::string(key));
    std::string result = it->value().as_string().c_str();
    if (result.size() > max) throw std::invalid_argument("Campo excede tamanho permitido: " + std::string(key));
    return result;
}
static std::string required(const Obj& o, std::string_view key, std::size_t max = 2000) {
    auto s = field(o, key, max);
    if (s.empty()) throw std::invalid_argument("Campo obrigatorio: " + std::string(key));
    return s;
}
static void choice(const std::string& value, std::initializer_list<std::string_view> allowed, std::string_view name) {
    for (auto a: allowed) if (a == value) return;
    throw std::invalid_argument("Valor nao permitido para " + std::string(name));
}
static void temporal(const std::string& s, std::string_view name) {
    if (s.empty()) return;
    static const std::regex iso(R"(^\d{4}-\d{2}-\d{2}($|T\d{2}:\d{2}:\d{2}(\.\d{1,6})?(Z|[+-]\d{2}:\d{2})$))");
    if (!std::regex_match(s, iso)) throw std::invalid_argument("Data precisa ser ISO-8601: " + std::string(name));
}
static bool is_sha256(const std::string& s) {
    return s.empty() || (s.size() == 64 && std::all_of(s.begin(),s.end(),[](unsigned char c){return std::isxdigit(c) != 0;}));
}
static int64_t id_from(std::string_view s) {
    int64_t n = 0;
    auto [end,ec]=std::from_chars(s.data(), s.data()+s.size(), n);
    if(ec!=std::errc{} || end!=s.data()+s.size() || n<1) throw std::invalid_argument("Identificador invalido");
    return n;
}
static std::string text_col(sqlite3_stmt* stmt, int c) {
    const auto* p = reinterpret_cast<const char*>(sqlite3_column_text(stmt,c));
    return p ? std::string(p) : std::string();
}
class SqlStmt {
    sqlite3_stmt* st_{};
    sqlite3* db_{};
public:
    SqlStmt(sqlite3* db, const char* sql):db_(db){
        if(sqlite3_prepare_v2(db,sql,-1,&st_,nullptr)!=SQLITE_OK) throw std::runtime_error(sqlite3_errmsg(db));
    }
    ~SqlStmt(){sqlite3_finalize(st_);}
    SqlStmt(const SqlStmt&)=delete;
    SqlStmt& operator=(const SqlStmt&)=delete;
    void bind(int idx, const std::string& v){
        if(sqlite3_bind_text(st_,idx,v.c_str(),-1,SQLITE_TRANSIENT)!=SQLITE_OK) throw std::runtime_error(sqlite3_errmsg(db_));
    }
    void bind(int idx, int64_t v){
        if(sqlite3_bind_int64(st_,idx,v)!=SQLITE_OK) throw std::runtime_error(sqlite3_errmsg(db_));
    }
    bool next(){int r=sqlite3_step(st_);if(r==SQLITE_ROW)return true;if(r==SQLITE_DONE)return false;throw std::runtime_error(sqlite3_errmsg(db_));}
    sqlite3_stmt* raw(){return st_;}
};
class Store {
    sqlite3* db_{};
    void exec(const std::string& sql){
        char* err=nullptr;
        if(sqlite3_exec(db_,sql.c_str(),nullptr,nullptr,&err)!=SQLITE_OK){
            std::string message=err?err:"SQLite error";sqlite3_free(err);throw std::runtime_error(message);
        }
    }
    void audit(const std::string& action,const std::string& type,int64_t id){
        SqlStmt stmt(db_,"INSERT INTO audit_log(action,subject_type,subject_id) VALUES(?,?,?)");
        stmt.bind(1,action);stmt.bind(2,type);stmt.bind(3,id);stmt.next();
    }
    bool exists(const char* table,int64_t id){
        const std::string sql=std::string("SELECT id FROM ")+table+" WHERE id=?";
        SqlStmt st(db_,sql.c_str());st.bind(1,id);return st.next();
    }
    void transaction_begin(){exec("BEGIN IMMEDIATE");}
    void transaction_commit(){exec("COMMIT");}
    void transaction_rollback() noexcept {sqlite3_exec(db_,"ROLLBACK",nullptr,nullptr,nullptr);}
public:
    Store(const fs::path& db_path,const fs::path& project_root){
        fs::create_directories(db_path.parent_path());
        if(sqlite3_open_v2(db_path.c_str(),&db_,SQLITE_OPEN_READWRITE|SQLITE_OPEN_CREATE|SQLITE_OPEN_FULLMUTEX,nullptr)!=SQLITE_OK){
            std::string why=db_?sqlite3_errmsg(db_):"Erro ao abrir SQLite";sqlite3_close(db_);db_=nullptr;throw std::runtime_error(why);
        }
        try {
            sqlite3_busy_timeout(db_,3000);
            exec("PRAGMA foreign_keys=ON");exec("PRAGMA journal_mode=WAL");
            exec("CREATE TABLE IF NOT EXISTS schema_migrations(version TEXT PRIMARY KEY, sha256 TEXT NOT NULL, applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')))");
            const auto migration=project_root/"db/migrations/001_foundation.sql";
            const auto content=read_text(migration);
            const auto digest=sha256hex(content);
            SqlStmt st(db_,"SELECT sha256 FROM schema_migrations WHERE version='001_foundation'");
            if(st.next()) {
                if(text_col(st.raw(),0)!=digest) throw std::runtime_error("Migracao 001 alterada apos aplicacao; restaurar versao anterior");
            } else {
                transaction_begin();
                try {
                    exec(content);
                    SqlStmt ins(db_,"INSERT INTO schema_migrations(version,sha256) VALUES('001_foundation',?)");
                    ins.bind(1,digest);ins.next();transaction_commit();
                } catch(...) {transaction_rollback();throw;}
            }
        }catch(...){sqlite3_close(db_);db_=nullptr;throw;}
    }
    ~Store(){if(db_)sqlite3_close(db_);}
    Store(const Store&)=delete;
    Store& operator=(const Store&)=delete;
    Obj summary(){
        Obj o;
        for(auto [name,table]:std::vector<std::pair<std::string,std::string>>{{"evidence","evidence"},{"investigations","investigations"},{"links","evidence_links"},{"journal","journal"}}){
            auto sql="SELECT COUNT(*) FROM "+table;SqlStmt st(db_,sql.c_str());st.next();o[name]=sqlite3_column_int64(st.raw(),0);
        }
        o["version"]="0.1.0";
        return o;
    }
    static Obj evidence_row(sqlite3_stmt* s){
        return {{"id",sqlite3_column_int64(s,0)},{"kind",text_col(s,1)},{"source_name",text_col(s,2)},
        {"source_ref",text_col(s,3)},{"statement",text_col(s,4)},{"location_ref",text_col(s,5)},
        {"valid_start",text_col(s,6)},{"valid_end",text_col(s,7)},{"observed_at",text_col(s,8)},
        {"provenance_uri",text_col(s,9)},{"source_sha256",text_col(s,10)},
        {"validation_status",text_col(s,11)},{"inserted_at",text_col(s,12)},
        {"record_fingerprint",text_col(s,13)}};
    }
    Arr evidence_list(){
        SqlStmt st(db_,"SELECT id,kind,source_name,source_ref,statement,location_ref,valid_start,valid_end,observed_at,provenance_uri,source_sha256,validation_status,inserted_at,record_fingerprint FROM evidence ORDER BY id DESC LIMIT 100");
        Arr a;while(st.next())a.emplace_back(evidence_row(st.raw()));return a;
    }
    Obj evidence_add(const Obj& o){
        std::array<std::string,11> v = {
            required(o,"kind",80),required(o,"source_name",160),required(o,"source_ref",512),
            required(o,"statement",4000),field(o,"location_ref",200),field(o,"valid_start",32),
            field(o,"valid_end",32),field(o,"observed_at",32),field(o,"provenance_uri",1000),
            field(o,"source_sha256",64),std::string("not_validated")};
        choice(v[0],{"meteorological_alert","instrument_measurement","documentary_report","derived_indicator","land_cover_classification","other"},"kind");
        temporal(v[5],"valid_start");temporal(v[6],"valid_end");temporal(v[7],"observed_at");
        if(!v[5].empty()&&!v[6].empty()&&v[5].size()==v[6].size()&&v[5]>v[6])throw std::invalid_argument("Intervalo temporal invertido");
        if(!is_sha256(v[9]))throw std::invalid_argument("source_sha256 deve conter 64 caracteres hexadecimais");
        std::string payload;
        for(const auto& s:v){payload+=std::to_string(s.size());payload+=':';payload+=s;payload+=';';}
        const auto fingerprint=sha256hex(payload);
        transaction_begin();
        try {
            SqlStmt st(db_,"INSERT OR IGNORE INTO evidence(record_fingerprint,kind,source_name,source_ref,statement,location_ref,valid_start,valid_end,observed_at,provenance_uri,source_sha256) VALUES(?,?,?,?,?,?,?,?,?,?,?)");
            st.bind(1,fingerprint);for(int i=0;i<10;i++)st.bind(i+2,v[i]);st.next();
            bool created=sqlite3_changes(db_)>0;
            SqlStmt find(db_,"SELECT id FROM evidence WHERE record_fingerprint=?");find.bind(1,fingerprint);find.next();
            auto id=sqlite3_column_int64(find.raw(),0);
            if(created)audit("evidence_registered","evidence",id);
            transaction_commit();
            return {{"id",id},{"created",created},{"validation_status","not_validated"},{"record_fingerprint",fingerprint}};
        }catch(...){transaction_rollback();throw;}
    }
    static Obj investigation_row(sqlite3_stmt* s){
        return {{"id",sqlite3_column_int64(s,0)},{"title",text_col(s,1)},{"question",text_col(s,2)},
                {"location_ref",text_col(s,3)},{"valid_start",text_col(s,4)},
                {"valid_end",text_col(s,5)},{"state",text_col(s,6)},{"created_at",text_col(s,7)}};
    }
    Arr investigations(){
        SqlStmt st(db_,"SELECT id,title,question,location_ref,valid_start,valid_end,state,created_at FROM investigations ORDER BY id DESC LIMIT 100");
        Arr a;while(st.next())a.emplace_back(investigation_row(st.raw()));return a;
    }
    Obj investigation_add(const Obj& o){
        auto title=required(o,"title",160), question=required(o,"question",4000);
        auto location=field(o,"location_ref",200),start=field(o,"valid_start",32),end=field(o,"valid_end",32);
        temporal(start,"valid_start");temporal(end,"valid_end");
        if(!start.empty()&&!end.empty()&&start.size()==end.size()&&start>end)throw std::invalid_argument("Intervalo temporal invertido");
        transaction_begin();
        try{
            SqlStmt st(db_,"INSERT INTO investigations(title,question,location_ref,valid_start,valid_end) VALUES(?,?,?,?,?)");
            st.bind(1,title);st.bind(2,question);st.bind(3,location);st.bind(4,start);st.bind(5,end);st.next();
            auto id=sqlite3_last_insert_rowid(db_);audit("investigation_opened","investigation",id);
            transaction_commit();return {{"id",id},{"created",true},{"state","open"}};
        }catch(...){transaction_rollback();throw;}
    }
    Obj investigation_get(int64_t id){
        SqlStmt st(db_,"SELECT id,title,question,location_ref,valid_start,valid_end,state,created_at FROM investigations WHERE id=?");
        st.bind(1,id);if(!st.next())throw std::out_of_range("Investigacao nao encontrada");
        Obj item=investigation_row(st.raw());
        SqlStmt links(db_,"SELECT l.id,l.evidence_id,l.relation,l.justification,l.created_at,e.kind,e.source_name,e.statement,e.validation_status FROM evidence_links l JOIN evidence e ON e.id=l.evidence_id WHERE l.investigation_id=? ORDER BY l.id");links.bind(1,id);
        Arr evidences;while(links.next()){
            auto s=links.raw();evidences.emplace_back(Obj{{"id",sqlite3_column_int64(s,0)},{"evidence_id",sqlite3_column_int64(s,1)},
            {"relation",text_col(s,2)},{"justification",text_col(s,3)},{"created_at",text_col(s,4)},
            {"kind",text_col(s,5)},{"source_name",text_col(s,6)},
            {"statement",text_col(s,7)},{"validation_status",text_col(s,8)}});
        }
        item["evidence_links"]=std::move(evidences);
        SqlStmt journal(db_,"SELECT id,kind,content,author_label,created_at FROM journal WHERE investigation_id=? ORDER BY id");journal.bind(1,id);
        Arr j;while(journal.next()){auto s=journal.raw();j.emplace_back(Obj{{"id",sqlite3_column_int64(s,0)},{"kind",text_col(s,1)},
        {"content",text_col(s,2)},{"author_label",text_col(s,3)},{"created_at",text_col(s,4)}});}
        item["journal"]=std::move(j);
        return item;
    }
    Obj link_add(int64_t investigation_id,const Obj& o){
        int64_t evidence_id=0;
        auto it=o.find("evidence_id");
        if(it!=o.end()&&it->value().is_int64())evidence_id=it->value().as_int64();
        if(evidence_id<1)throw std::invalid_argument("evidence_id deve ser inteiro positivo");
        auto relation=required(o,"relation",50),justification=field(o,"justification",4000);
        choice(relation,{"contextualizes","supports","contradicts","questions"},"relation");
        if(!exists("investigations",investigation_id)||!exists("evidence",evidence_id))throw std::out_of_range("Investigacao ou evidencia nao encontrada");
        transaction_begin();
        try{
            SqlStmt st(db_,"INSERT OR IGNORE INTO evidence_links(investigation_id,evidence_id,relation,justification) VALUES(?,?,?,?)");
            st.bind(1,investigation_id);st.bind(2,evidence_id);st.bind(3,relation);st.bind(4,justification);st.next();bool created=sqlite3_changes(db_)>0;
            SqlStmt q(db_,"SELECT id FROM evidence_links WHERE investigation_id=? AND evidence_id=? AND relation=? AND justification=?");
            q.bind(1,investigation_id);q.bind(2,evidence_id);q.bind(3,relation);q.bind(4,justification);q.next();auto id=sqlite3_column_int64(q.raw(),0);
            if(created)audit("evidence_linked","link",id);
            transaction_commit();return {{"id",id},{"created",created}};
        }catch(...){transaction_rollback();throw;}
    }
    Obj journal_add(int64_t investigation_id,const Obj& o){
        if(!exists("investigations",investigation_id))throw std::out_of_range("Investigacao nao encontrada");
        auto kind=required(o,"kind",50),content=required(o,"content",4000),author=field(o,"author_label",80),key=field(o,"request_key",120);
        choice(kind,{"question","hypothesis","objection","decision","note"},"kind");
        if(author.empty())author="pesquisador-local";
        transaction_begin();
        try{
            if(!key.empty()){
                SqlStmt prior(db_,"SELECT id,investigation_id,kind,content,author_label FROM journal WHERE request_key=?");prior.bind(1,key);
                if(prior.next()){
                    auto st=prior.raw();auto id=sqlite3_column_int64(st,0);
                    if(sqlite3_column_int64(st,1)!=investigation_id||text_col(st,2)!=kind||text_col(st,3)!=content||text_col(st,4)!=author)throw std::invalid_argument("request_key reutilizada com conteudo divergente");
                    transaction_commit();return {{"id",id},{"created",false}};
                }
            }
            SqlStmt st(db_,"INSERT INTO journal(investigation_id,kind,content,author_label,request_key) VALUES(?,?,?,?,?)");
            st.bind(1,investigation_id);st.bind(2,kind);st.bind(3,content);st.bind(4,author);
            if(key.empty())sqlite3_bind_null(st.raw(),5);else st.bind(5,key);
            st.next();auto id=sqlite3_last_insert_rowid(db_);audit("journal_entry_added","journal",id);
            transaction_commit();return {{"id",id},{"created",true}};
        }catch(...){transaction_rollback();throw;}
    }
    Arr audit_log(){
        SqlStmt st(db_,"SELECT id,action,subject_type,subject_id,created_at FROM audit_log ORDER BY id DESC LIMIT 50");
        Arr a;while(st.next()){auto s=st.raw();a.emplace_back(Obj{{"id",sqlite3_column_int64(s,0)},{"action",text_col(s,1)},
        {"subject_type",text_col(s,2)},{"subject_id",sqlite3_column_int64(s,3)},{"created_at",text_col(s,4)}});}return a;
    }
};

using Request=http::request<http::string_body>;
using Response=http::response<http::string_body>;
static Response response(http::status status, std::string body, std::string type="application/json; charset=utf-8"){
    Response res{status,11};res.set(http::field::server,"TESSITURA/0.1.0");
    res.set(http::field::content_type,type);res.set(http::field::cache_control,"no-store");
    res.set("X-Content-Type-Options","nosniff");
    res.set("X-Frame-Options","DENY");
    res.set("Content-Security-Policy","default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'");
    res.body()=std::move(body);res.keep_alive(false);res.prepare_payload();return res;
}
static Response json_response(http::status status,json::value v){return response(status,json::serialize(v));}
static Response bad(http::status status,const std::string& code,const std::string& detail){
    return json_response(status,Obj{{"error",code},{"detail",detail}});
}
static Obj parse_body(const Request& req){
    if(req.body().size()>65536)throw std::invalid_argument("Corpo excede 64 KiB");
    auto value=json::parse(req.body());if(!value.is_object())throw std::invalid_argument("Esperado objeto JSON");
    return value.as_object();
}
static std::vector<std::string> split_path(std::string_view path){
    std::vector<std::string> result;std::size_t pos=0;
    while(pos<path.size()){
        while(pos<path.size() && path[pos]=='/')pos++;
        if(pos>=path.size())break;
        auto end=path.find('/',pos);if(end==std::string_view::npos)end=path.size();
        result.emplace_back(path.substr(pos,end-pos));pos=end;
    }return result;
}
static Response route(const Request& req,Store& store,const fs::path& root,const std::string& bind_address){
    const auto method=req.method();
    std::string target=req.target();auto q=target.find('?');if(q!=std::string::npos)target.resize(q);
    if(method==http::verb::get){
        std::string filename;
        if(target=="/")filename="index.html";
        else if(target=="/style.css")filename="style.css";
        else if(target=="/app.js")filename="app.js";
        if(!filename.empty())return response(http::status::ok,read_text(root/"web"/filename),filename.ends_with(".css")?"text/css; charset=utf-8":filename.ends_with(".js")?"application/javascript; charset=utf-8":"text/html; charset=utf-8");
        if(target=="/api/health")return json_response(http::status::ok,Obj{{"system","tessitura"},{"version","0.1.0"},{"status","ok"},{"bind",bind_address}});
        if(target=="/api/v1/capabilities")return json_response(http::status::ok,Obj{{"evidence_registration",true},{"append_only",true},{"investigations",true},{"manual_evidence_linking",true},{"research_journal",true},{"automated_inference",false},{"external_connectors",false},{"scientific_validation",false},{"authentication",false},{"exposure",bind_address=="127.0.0.1"||bind_address=="::1"?"local_only":"local_network"}});
        if(target=="/api/v1/summary")return json_response(http::status::ok,store.summary());
        if(target=="/api/v1/evidence")return json_response(http::status::ok,Obj{{"items",store.evidence_list()}});
        if(target=="/api/v1/investigations")return json_response(http::status::ok,Obj{{"items",store.investigations()}});
        if(target=="/api/v1/audit")return json_response(http::status::ok,Obj{{"items",store.audit_log()}});
    }
    if(method==http::verb::post){
        if(target=="/api/v1/evidence")return json_response(http::status::created,store.evidence_add(parse_body(req)));
        if(target=="/api/v1/investigations")return json_response(http::status::created,store.investigation_add(parse_body(req)));
    }
    const auto p=split_path(target);
    if(p.size()>=4&&p[0]=="api"&&p[1]=="v1"&&p[2]=="investigations"){
        const auto id=id_from(p[3]);
        if(method==http::verb::get && p.size()==4)return json_response(http::status::ok,store.investigation_get(id));
        if(method==http::verb::post && p.size()==5){
            if(p[4]=="links")return json_response(http::status::created,store.link_add(id,parse_body(req)));
            if(p[4]=="journal")return json_response(http::status::created,store.journal_add(id,parse_body(req)));
        }
    }
    return bad(http::status::not_found,"not_found","Rota indisponivel");
}
static Response safe_route(const Request& req,Store& s,const fs::path& root,const std::string& bind_address){
    try{return route(req,s,root,bind_address);}
    catch(const std::invalid_argument& e){return bad(http::status::bad_request,"invalid_input",e.what());}
    catch(const boost::system::system_error& e){return bad(http::status::bad_request,"invalid_json",e.what());}
    catch(const std::out_of_range& e){return bad(http::status::not_found,"not_found",e.what());}
    catch(const std::exception& e){std::cerr<<"[ERROR] "<<e.what()<<"\n";return bad(http::status::internal_server_error,"internal_error","Falha interna; consulte os logs locais");}
}
int main(int argc,char** argv){
    try{
        fs::path root=fs::current_path(),db_path;std::string host="127.0.0.1";int port=18871;bool doctor=false;
        for(int i=1;i<argc;i++){
            std::string a=argv[i];
            if(a=="--root"&&i+1<argc)root=fs::absolute(argv[++i]);
            else if(a=="--db"&&i+1<argc)db_path=fs::absolute(argv[++i]);
            else if(a=="--host"&&i+1<argc)host=argv[++i];
            else if(a=="--port"&&i+1<argc){
                std::string val=argv[++i];unsigned p=0;
                auto [end,ec]=std::from_chars(val.data(),val.data()+val.size(),p);
                if(ec!=std::errc{}||end!=val.data()+val.size()||p<1024||p>65535)throw std::invalid_argument("Porta precisa estar entre 1024 e 65535");
                port=int(p);
            }
            else if(a=="--doctor")doctor=true;
            else throw std::invalid_argument("Argumento desconhecido: "+a);
        }
        root=fs::canonical(root);
        if(db_path.empty())db_path=root/"var/tessitura.sqlite3";
        Store store(db_path,root);
        if(doctor){std::cout<<json::serialize(store.summary())<<"\n";return 0;}
        asio::io_context io(1);
        const auto address=asio::ip::make_address(host);
        tcp::acceptor acceptor(io,{address,static_cast<unsigned short>(port)});
        std::cout<<"TESSITURA v0.1.0 | http://"<<host<<":"<<port<<" | "<<db_path<<std::endl;
        for(;;){
            tcp::socket sock(io);acceptor.accept(sock);
            try{
                beast::flat_buffer buffer;
                Request request;
                http::read(sock,buffer,request);
                auto res=safe_route(request,store,root,host);
                http::write(sock,res);
            }catch(const std::exception& e){std::cerr<<"[HTTP] "<<e.what()<<"\n";}
            beast::error_code ec;sock.shutdown(tcp::socket::shutdown_both,ec);
        }
    }catch(const std::exception& e){std::cerr<<"TESSITURA: "<<e.what()<<"\n";return 1;}
}
