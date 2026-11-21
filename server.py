import os, sqlite3, json, secrets, hmac, time
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
DB=Path(__file__).with_name('shop.db')
STEPS=['Дар интизори тасдиқ','Пардохт тасдиқ шуд','Ҷамъоварӣ мешавад','Дар роҳ','Расонида шуд']
CANCEL='Бекор карда шуд'
HITS={}
def limited(key,maxn,window):
 now=time.time(); l=[t for t in HITS.get(key,[]) if now-t<window]; HITS[key]=l
 if len(l)>=maxn: return True
 l.append(now); return False
def db():
 c=sqlite3.connect(DB,timeout=10); c.row_factory=sqlite3.Row; return c
with db() as c:
 c.executescript('CREATE TABLE IF NOT EXISTS products(id INTEGER PRIMARY KEY,name TEXT,price REAL,photo TEXT,stock REAL); CREATE TABLE IF NOT EXISTS orders(id INTEGER PRIMARY KEY,token TEXT,body TEXT,status TEXT);')
class H(BaseHTTPRequestHandler):
 def ip(self): return self.headers.get('X-Forwarded-For',self.client_address[0]).split(',')[0].strip()
 def send(self,data,status=200,typ='application/json'):
  b=json.dumps(data,ensure_ascii=False).encode() if typ=='application/json' else data
  self.send_response(status); self.send_header('Content-Type',typ); self.send_header('Cache-Control','no-store')
  self.send_header('X-Content-Type-Options','nosniff'); self.send_header('X-Frame-Options','DENY'); self.send_header('Referrer-Policy','no-referrer')
  self.end_headers(); self.wfile.write(b)
 def auth(self):
  key=os.getenv('ADMIN_KEY','')
  if not key: return False
  if limited('auth'+self.ip(),10,600): return False
  ok=hmac.compare_digest(self.headers.get('X-Key','').encode(),key.encode())
  if ok: HITS['auth'+self.ip()]=[]
  return ok
 def do_GET(self):
  if self.path in ['/manifest.webmanifest','/sw.js','/icon-192.png','/icon-512.png']:
   name=self.path[1:]; return self.send(Path(__file__).with_name(name).read_bytes(),typ={'manifest.webmanifest':'application/manifest+json','sw.js':'application/javascript'}.get(name,'image/png'))
  if self.path=='/': return self.send(Path(__file__).with_name('index.html').read_bytes(),typ='text/html; charset=utf-8')
  with db() as c:
   if self.path=='/products': return self.send([dict(r) for r in c.execute('SELECT * FROM products')])
   if self.path=='/orders' and self.auth(): return self.send([dict(r) for r in c.execute('SELECT * FROM orders ORDER BY id DESC')])
   if self.path.startswith('/track/'):
    if limited('trk'+self.ip(),60,600): return self.send({'error':'Лимит'},429)
    r=c.execute('SELECT id,status FROM orders WHERE token=?',(self.path.split('/')[-1],)).fetchone(); return self.send(dict(r) if r else {},200 if r else 404)
  self.send({},404)
 def do_POST(self):
  try:
   n=int(self.headers.get('Content-Length',0)); assert 0<n<8000000; x=json.loads(self.rfile.read(n))
   with db() as c:
    if self.path=='/order':
     if limited('ord'+self.ip(),10,3600): return self.send({'error':'Лимит фармоиш. Баъдтар кӯшиш кунед'},429)
     c.execute('BEGIN IMMEDIATE'); items=[]; total=20
     assert isinstance(x['items'],dict) and len(x['items'])<=50
     for k,v in x['items'].items():
      q=float(v); assert 0<q<=100; p=c.execute('SELECT * FROM products WHERE id=?',(int(k),)).fetchone(); assert p and p['stock']>=q
      total+=q*p['price']; items.append([p['name'],q,p['price'],p['id']]); c.execute('UPDATE products SET stock=stock-? WHERE id=?',(q,int(k)))
     assert items and x['phone'].strip() and x['address'].strip() and len(x['phone'])<40 and len(x['address'])<300 and x['payment'] in ['cash','alif','dc']
     assert x['payment']=='cash' or x.get('receipt','').startswith('data:image/')
     token=secrets.token_urlsafe(24); body={k:x[k] for k in ['phone','address','payment']}; body.update(items=items,total=round(total,2),receipt=x.get('receipt','') if x['payment']!='cash' else '')
     cur=c.execute('INSERT INTO orders(token,body,status) VALUES(?,?,?)',(token,json.dumps(body,ensure_ascii=False),STEPS[0])); return self.send({'id':cur.lastrowid,'token':token,'total':round(total,2)})
    if not self.auth(): return self.send({'error':'Дастрасӣ нест'},403)
    if self.path=='/product':
     assert float(x['price'])>=0 and float(x['stock'])>=0 and x['name'].strip()
     c.execute('INSERT INTO products(id,name,price,photo,stock) VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET name=excluded.name,price=excluded.price,photo=excluded.photo,stock=excluded.stock',(x.get('id') or None,x['name'],float(x['price']),x.get('photo',''),float(x['stock']))); return self.send({'ok':True})
    if self.path=='/delete':
     c.execute('DELETE FROM products WHERE id=?',(int(x['id']),)); return self.send({'ok':True})
    if self.path=='/status':
     c.execute('BEGIN IMMEDIATE'); r=c.execute('SELECT body,status FROM orders WHERE id=?',(int(x['id']),)).fetchone(); assert r
     b=json.loads(r['body']); cur_s=r['status']; t=x['status']; assert cur_s not in (STEPS[4],CANCEL)
     if t==CANCEL:
      for it in b['items']:
       if len(it)>3: c.execute('UPDATE products SET stock=stock+? WHERE id=?',(it[1],it[3]))
     else:
      cu=STEPS.index(cur_s); ta=STEPS.index(t); assert ta==cu+1 or (cu==0 and ta==2 and b['payment']=='cash')
     c.execute('UPDATE orders SET status=? WHERE id=?',(t,int(x['id']))); return self.send({'ok':True})
   self.send({},404)
  except Exception: self.send({'error':'Маълумот нодуруст аст ё маҳсулот намерасад'},400)
if __name__=='__main__': ThreadingHTTPServer(('0.0.0.0',int(os.getenv('PORT','8000'))),H).serve_forever()
