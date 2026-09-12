from flask import Flask, jsonify, request
from flask_cors import CORS
import os, io, csv, random, threading
from datetime import datetime, timedelta

application = Flask(__name__)
CORS(application, resources={r"/*": {"origins": "*"}})
application.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'sales_2025.csv')

_lock = threading.Lock()
_current_rows = None
_current_source = None
_current_name = None

DATE_ALIASES = ['date','order_date','order date','timestamp','time','ds','day',
                'datetime','date_time','transaction_date','invoice_date','created_at','created']
SALES_ALIASES = ['total_sales_inr','total_sales','total sales','sales_amount',
                 'sales amount','sales','amount','revenue','total','price','sales_inr','income','value']

def parse_date(s):
    if s is None: return None
    s = str(s).strip()
    if not s: return None
    for fmt in ['%Y-%m-%d','%d-%m-%Y','%m/%d/%Y','%d/%m/%Y','%Y/%m/%d',
                '%Y-%m-%d %H:%M:%S','%d-%m-%Y %H:%M:%S','%Y-%m-%dT%H:%M:%S',
                '%d %b %Y','%b %d, %Y']:
        try: return datetime.strptime(s, fmt)
        except ValueError: continue
    try: return datetime.fromisoformat(s.replace('Z',''))
    except: return None

def to_float(v):
    if v is None: return None
    try: return float(str(v).replace(',','').replace('₹','').replace('$','').strip())
    except: return None

def read_csv(file_obj):
    try:
        text = file_obj.read()
        if isinstance(text, bytes):
            try: text = text.decode('utf-8')
            except UnicodeDecodeError: text = text.decode('latin-1')
        return list(csv.DictReader(io.StringIO(text)))
    except Exception as e:
        print("CSV error:", e); return []

def detect_columns(rows):
    if not rows: return None, None
    cols = list(rows[0].keys())
    cl = {c.lower().strip(): c for c in cols if c}
    date_col = next((cl[a] for a in DATE_ALIASES if a in cl), None)
    if not date_col:
        for c in cols:
            for r in rows[:20]:
                if r.get(c) and parse_date(r[c]): date_col = c; break
            if date_col: break
    sales_col = None
    for a in SALES_ALIASES:
        if a in cl:
            cand = cl[a]; good = sum(1 for r in rows[:50] if to_float(r.get(cand)) is not None)
            if good / max(len(rows[:50]),1) >= 0.7: sales_col = cand; break
    if not sales_col:
        for c in cols:
            if c == date_col: continue
            vals = [to_float(r.get(c)) for r in rows[:50]]
            good = sum(1 for v in vals if v is not None)
            if good / max(len(vals),1) >= 0.7 and len(set(v for v in vals if v is not None)) > 1:
                sales_col = c; break
    if not sales_col:
        q = p = None
        for c in cols:
            l = c.lower().strip()
            if not q and ('quantity' in l or l in ('qty','units','count')): q = c
            if not p and ('unit_price' in l or l in ('unit price','price')): p = c
        if q and p: sales_col = ('MULTIPLY', q, p)
    return date_col, sales_col

def normalize(rows, dc, sc):
    out = []
    if isinstance(sc, tuple):
        _, q, p = sc
        for r in rows:
            d = parse_date(r.get(dc)); qv = to_float(r.get(q)); pv = to_float(r.get(p))
            if d and qv is not None and pv is not None: out.append({'Date':d,'sales':qv*pv})
    else:
        for r in rows:
            d = parse_date(r.get(dc)); sv = to_float(r.get(sc))
            if d and sv is not None: out.append({'Date':d,'sales':sv})
    return out

def get_rows():
    global _current_rows, _current_source, _current_name
    with _lock:
        if _current_rows is not None: return _current_rows
        if os.path.exists(DATA_PATH):
            try:
                with open(DATA_PATH,'rb') as f: rows = read_csv(f)
                if rows:
                    dc, sc = detect_columns(rows)
                    if dc and sc:
                        norm = normalize(rows, dc, sc)
                        if norm:
                            _current_rows = norm; _current_source = 'default'
                            _current_name = 'sales_2025.csv'; return norm
            except Exception as e: print("Default load failed:", e)
        rows = []; base = datetime.now() - timedelta(days=99)
        for i in range(100):
            rows.append({'Date': base + timedelta(days=i), 'sales': 1000 + random.random()*4000 + i*5})
        _current_rows = rows; _current_source = 'fallback'
        _current_name = 'generated_sample.csv'
        return rows

def set_rows(rows, src, name):
    global _current_rows, _current_source, _current_name
    with _lock: _current_rows = rows; _current_source = src; _current_name = name

def reset_rows():
    global _current_rows, _current_source, _current_name
    with _lock: _current_rows = None; _current_source = None; _current_name = None

def linear_forecast(values, periods=30):
    n = len(values)
    if n == 0: return [0.0]*periods
    if n == 1: return [round(float(values[0]),2)]*periods
    xs = list(range(n)); mx = sum(xs)/n; my = sum(values)/n
    num = sum((x-mx)*(y-my) for x,y in zip(xs,values))
    den = sum((x-mx)**2 for x in xs)
    if den == 0: return [round(my,2)]*periods
    slope = num/den; inter = my - slope*mx
    return [round(max(slope*(n+i)+inter, 0.0), 2) for i in range(periods)]

# ---------- ROUTES ----------

@application.route('/api/health')
def health():
    r = get_rows()
    return jsonify({'status':'healthy','rows':len(r) if r else 0,'source':_current_source,
                    'time':datetime.now().isoformat()})

@application.route('/api/data-status')
def data_status():
    r = get_rows()
    info = {'source':_current_source or 'none','name':_current_name or 'none',
            'rows':len(r) if r else 0}
    if r:
        ds = [x['Date'] for x in r]
        info['date_range'] = {'start':min(ds).strftime('%Y-%m-%d'),'end':max(ds).strftime('%Y-%m-%d')}
        info['total_sales'] = sum(x['sales'] for x in r)
    return jsonify(info)

@application.route('/api/dashboard-data')
def dashboard_data():
    r = get_rows()
    if not r: return jsonify({'error':'No data'}), 500
    sales = [x['sales'] for x in r]
    total = sum(sales); avg = total/len(sales); mn = min(sales); mx = max(sales)
    std = (sum((v-avg)**2 for v in sales)/(len(sales)-1))**0.5 if len(sales)>1 else 0.0
    sr = sorted(r, key=lambda x: x['Date']); h = len(sr)//2
    fh = sr[:h]; sh = sr[h:]
    fa = sum(x['sales'] for x in fh)/len(fh) if fh else 0
    sa = sum(x['sales'] for x in sh)/len(sh) if sh else 0
    trend = ((sa-fa)/fa*100) if fa>0 else 0.0
    analytics = {'total':round(total,2),'average':round(avg,2),'min':round(mn,2),
                 'max':round(mx,2),'std_dev':round(std,2),'total_records':len(r),
                 'trend_percentage':round(trend,2)}
    daily = {}
    for x in sr: daily[x['Date'].date()] = daily.get(x['Date'].date(),0) + x['sales']
    dl = sorted(daily.items())[-180:]
    history = [{'ds':str(d),'y':round(v,2)} for d,v in dl]
    recent = [v for _,v in dl[-60:]] or [avg]
    fvals = linear_forecast(recent, 30)
    today = datetime.now().date()
    fdates = [str(today+timedelta(days=i)) for i in range(1,31)]
    return jsonify({'data_type':'sales','analytics':analytics,
                    'forecast':{'dates':fdates,'forecast':fvals},
                    'data':history,'total_records':len(r),'source_name':_current_name})

@application.route('/api/insights')
def insights():
    r = get_rows()
    if not r: return jsonify({'insights':[]})
    sales = [x['sales'] for x in r]; total = sum(sales)
    out = [{'category':'Performance','title':'Total Sales Volume',
            'description':'Recorded {:,.0f} across {:,.0f} records'.format(total,len(r)),
            'impact':'Medium'}]
    ds = [x['Date'] for x in r]
    span = (max(ds)-min(ds)).days
    out.append({'category':'Data Quality','title':'Date Range: {} days'.format(span+1),
                'description':'From {} to {}'.format(min(ds).strftime('%Y-%m-%d'),max(ds).strftime('%Y-%m-%d')),
                'impact':'Low'})
    sr = sorted(r, key=lambda x: x['Date']); h = len(sr)//2
    if h > 0:
        fa = sum(x['sales'] for x in sr[:h])/h
        sa = sum(x['sales'] for x in sr[h:])/(len(sr)-h)
        if fa > 0:
            chg = (sa-fa)/fa*100
            out.append({'category':'Growth',
                        'title':'Trend: {:.1f}% {}'.format(abs(chg),'increase' if chg>=0 else 'decrease'),
                        'description':'Second half vs first half avg',
                        'impact':'High' if abs(chg)>10 else 'Medium'})
    if len(r) > 2:
        avg = sum(sales)/len(sales)
        if avg > 0:
            std = (sum((v-avg)**2 for v in sales)/(len(sales)-1))**0.5
            cv = std/avg*100
            out.append({'category':'Performance','title':'Volatility: {:.1f}%'.format(cv),
                        'description':'Coefficient of variation',
                        'impact':'High' if cv>100 else 'Low'})
    return jsonify({'insights':out,'total_insights':len(out)})

@application.route('/api/live')
def live():
    r = get_rows()
    recent_avg = total = avg = 0.0
    if r:
        daily = {}
        for x in r: daily[x['Date'].date()] = daily.get(x['Date'].date(),0) + x['sales']
        dl = sorted(daily.items()); recent = [v for _,v in dl[-7:]]
        recent_avg = sum(recent)/len(recent) if recent else 0
        total = sum(x['sales'] for x in r); avg = total/len(r)
    tick = round(recent_avg*random.uniform(0.92,1.08), 2)
    now = datetime.now()
    return jsonify({'timestamp':now.strftime('%H:%M:%S'),'tick_value':tick,
                    'recent_avg':round(recent_avg,2),'total':round(total,2),
                    'average':round(avg,2),'active_users':random.randint(120,480),
                    'orders_per_min':random.randint(8,42),
                    'conversion_rate':round(random.uniform(2.5,8.5),2),
                    'response_ms':random.randint(45,180),'cpu':random.randint(15,70),
                    'memory':random.randint(30,85),'status':'operational'})

@application.route('/api/upload', methods=['POST'])
def upload():
    if 'file' not in request.files: return jsonify({'error':'No file'}), 400
    f = request.files['file']
    if not f.filename: return jsonify({'error':'Empty filename'}), 400
    if not f.filename.lower().endswith('.csv'): return jsonify({'error':'Only .csv allowed'}), 400
    try:
        raw = f.read()
        if not raw: return jsonify({'error':'File empty'}), 400
        rows = read_csv(io.BytesIO(raw))
        if not rows: return jsonify({'error':'Could not parse CSV'}), 400
        dc, sc = detect_columns(rows)
        if not dc: return jsonify({'error':'No date column found','columns_found':list(rows[0].keys())}), 400
        if not sc: return jsonify({'error':'No sales column found','columns_found':list(rows[0].keys())}), 400
        norm = normalize(rows, dc, sc)
        if not norm: return jsonify({'error':'No valid rows'}), 400
        set_rows(norm, 'uploaded', f.filename)
        ds = [x['Date'] for x in norm]
        sd = sc if isinstance(sc, str) else '{} × {}'.format(sc[1], sc[2])
        return jsonify({'success':True,'filename':f.filename,'rows':len(norm),
                        'columns_detected':{'date':dc,'sales':sd},
                        'date_range':{'start':min(ds).strftime('%Y-%m-%d'),'end':max(ds).strftime('%Y-%m-%d')},
                        'total_sales':sum(x['sales'] for x in norm)})
    except Exception as e:
        return jsonify({'error':str(e)}), 500

@application.route('/api/reset-data', methods=['POST'])
def reset():
    reset_rows(); r = get_rows()
    return jsonify({'success':True,'rows':len(r) if r else 0})

if __name__ == '__main__':
    application.run(debug=False, host='127.0.0.1', port=5000)
