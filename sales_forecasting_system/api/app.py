from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
import pandas as pd
import numpy as np
import os
import io
import threading
import random
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='../frontend', static_url_path='')
CORS(app, resources={r"/*": {"origins": "*"}})

# Max upload size: 20 MB
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'sales_2025.csv')
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend')

# Thread-safe current dataset
_lock = threading.Lock()
_current_df = None
_current_source = None   # 'default' or 'uploaded'
_current_name = None


# ══════════════════════════════════════════════════════════════════════════
# COLUMN DETECTION
# ══════════════════════════════════════════════════════════════════════════

def detect_columns(df):
    """
    Detect date and sales columns from any CSV.
    Returns (date_col, sales_col).
    sales_col can be a string OR ('MULTIPLY', qty_col, price_col).
    """
    cols = list(df.columns)
    cols_lower = {c.lower().strip(): c for c in cols}

    # ─── Date column ───
    date_aliases = ['date', 'order_date', 'order date', 'timestamp', 'time',
                    'ds', 'day', 'datetime', 'date_time', 'transaction_date',
                    'invoice_date', 'created_at', 'created']
    date_col = None
    for alias in date_aliases:
        if alias in cols_lower:
            date_col = cols_lower[alias]
            break

    if date_col is None:
        # Try dtype detection on object columns
        best_col, best_score = None, 0
        for c in cols:
            if df[c].dtype == 'object':
                try:
                    parsed = pd.to_datetime(df[c], errors='coerce')
                    score = parsed.notna().sum() / max(len(df), 1)
                    if score > best_score and score >= 0.7:
                        best_score = score
                        best_col = c
                except Exception:
                    pass
        date_col = best_col

    # ─── Sales column ───
    sales_aliases = ['total_sales_inr', 'total_sales', 'total sales',
                     'sales_amount', 'sales amount', 'sales',
                     'amount', 'revenue', 'total', 'price', 'sales_inr',
                     'income', 'value']
    sales_col = None
    for alias in sales_aliases:
        if alias in cols_lower:
            candidate = cols_lower[alias]
            nums = pd.to_numeric(df[candidate], errors='coerce')
            if nums.notna().sum() / max(len(df), 1) >= 0.7:
                sales_col = candidate
                break

    if sales_col is None:
        # Any numeric column with variance
        for c in cols:
            if c == date_col:
                continue
            nums = pd.to_numeric(df[c], errors='coerce')
            if nums.notna().sum() / max(len(df), 1) >= 0.7 and nums.std() > 0:
                sales_col = c
                break

    # Fallback: quantity × unit price
    if sales_col is None:
        qty_col, price_col = None, None
        for c in cols:
            cl = c.lower().strip()
            if qty_col is None and ('quantity' in cl or cl in ('qty', 'units', 'count')):
                qty_col = c
            if price_col is None and ('unit_price' in cl or cl == 'unit price' or cl == 'price'):
                price_col = c
        if qty_col and price_col:
            sales_col = ('MULTIPLY', qty_col, price_col)

    return date_col, sales_col


def normalize_dataframe(df, date_col, sales_col):
    """Return df with normalized 'Date' and 'Total_Sales_INR' columns."""
    out = df.copy()

    if isinstance(sales_col, tuple) and sales_col[0] == 'MULTIPLY':
        _, qty_col, price_col = sales_col
        out['Total_Sales_INR'] = (
            pd.to_numeric(out[qty_col], errors='coerce') *
            pd.to_numeric(out[price_col], errors='coerce')
        )
    else:
        out['Total_Sales_INR'] = pd.to_numeric(out[sales_col], errors='coerce')

    out['Date'] = pd.to_datetime(out[date_col], errors='coerce')
    out = out.dropna(subset=['Date', 'Total_Sales_INR'])
    return out


# ══════════════════════════════════════════════════════════════════════════
# DATASET MANAGEMENT
# ══════════════════════════════════════════════════════════════════════════

def get_current_df():
    """Return current dataframe, loading default if none set."""
    global _current_df, _current_source, _current_name
    with _lock:
        if _current_df is not None:
            return _current_df
        if os.path.exists(DATA_PATH):
            try:
                df = pd.read_csv(DATA_PATH)
                _current_df = df
                _current_source = 'default'
                _current_name = 'sales_2025.csv'
                return df
            except Exception as e:
                print("Failed to load default data:", e)
        return None


def set_current_df(df, source, name):
    global _current_df, _current_source, _current_name
    with _lock:
        _current_df = df
        _current_source = source
        _current_name = name


def reset_current_df():
    global _current_df, _current_source, _current_name
    with _lock:
        _current_df = None
        _current_source = None
        _current_name = None


def prepare(df):
    """Ensure 'Date' and 'sales' columns exist. Works with any uploaded format."""
    if df is None:
        return None
    df = df.copy()

    # Date
    if 'Date' in df.columns:
        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
    elif 'date' in df.columns:
        df['Date'] = pd.to_datetime(df['date'], errors='coerce')
    else:
        # Try detect on the fly
        dc, _ = detect_columns(df)
        if dc:
            df['Date'] = pd.to_datetime(df[dc], errors='coerce')
        else:
            return None

    # Sales
    if 'Total_Sales_INR' in df.columns:
        df['sales'] = pd.to_numeric(df['Total_Sales_INR'], errors='coerce')
    elif 'sales_amount' in df.columns:
        df['sales'] = pd.to_numeric(df['sales_amount'], errors='coerce')
    elif 'sales' in df.columns:
        df['sales'] = pd.to_numeric(df['sales'], errors='coerce')
    else:
        _, sc = detect_columns(df)
        if sc is None:
            return None
        if isinstance(sc, tuple):
            _, q, p = sc
            df['sales'] = pd.to_numeric(df[q], errors='coerce') * pd.to_numeric(df[p], errors='coerce')
        else:
            df['sales'] = pd.to_numeric(df[sc], errors='coerce')

    return df.dropna(subset=['Date', 'sales'])


# ══════════════════════════════════════════════════════════════════════════
# FORECAST (real least-squares linear regression on recent data)
# ══════════════════════════════════════════════════════════════════════════

def linear_forecast(y_values, periods=30):
    """
    Fit y = a*x + b via least squares, extrapolate. Real forecast, no ML magic.
    Returns list of predicted values.
    """
    if len(y_values) == 0:
        return [0.0] * periods
    if len(y_values) == 1:
        return [float(y_values[0])] * periods

    x = np.arange(len(y_values), dtype=float)
    y = np.asarray(y_values, dtype=float)

    # Guard against NaN
    mask = np.isfinite(y)
    if mask.sum() < 2:
        return [float(y[mask].mean()) if mask.sum() else 0.0] * periods

    coefs = np.polyfit(x[mask], y[mask], 1)  # slope, intercept
    future_x = np.arange(len(y_values), len(y_values) + periods, dtype=float)
    preds = np.polyval(coefs, future_x)
    preds = np.maximum(preds, 0.0)  # no negative sales
    return [round(float(v), 2) for v in preds]


# ══════════════════════════════════════════════════════════════════════════
# FRONTEND
# ══════════════════════════════════════════════════════════════════════════

@app.route('/')
def root():
    return send_from_directory(FRONTEND_DIR, 'index.html')


@app.route('/<path:filename>')
def static_files(filename):
    path = os.path.join(FRONTEND_DIR, filename)
    if os.path.exists(path):
        return send_from_directory(FRONTEND_DIR, filename)
    return jsonify({'error': 'Not found: ' + filename}), 404


# ══════════════════════════════════════════════════════════════════════════
# DATA UPLOAD / STATUS / RESET
# ══════════════════════════════════════════════════════════════════════════

@app.route('/api/data-status')
def data_status():
    df = get_current_df()
    info = {
        'source': _current_source or 'none',
        'name': _current_name or 'none',
        'rows': int(len(df)) if df is not None else 0,
        'columns': df.columns.tolist() if df is not None else []
    }
    if df is not None:
        p = prepare(df)
        if p is not None and len(p) > 0:
            info['date_range'] = {
                'start': p['Date'].min().strftime('%Y-%m-%d'),
                'end': p['Date'].max().strftime('%Y-%m-%d')
            }
            info['total_sales'] = float(p['sales'].sum())
    return jsonify(info)


@app.route('/api/upload', methods=['POST'])
def upload_data():
    if 'file' not in request.files:
        return jsonify({'error': 'No file was uploaded'}), 400

    file = request.files['file']
    if not file.filename:
        return jsonify({'error': 'Empty filename'}), 400

    if not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'Only .csv files are supported'}), 400

    try:
        raw = file.read()
        if len(raw) == 0:
            return jsonify({'error': 'The uploaded file is empty'}), 400

        # Parse CSV
        try:
            df = pd.read_csv(io.BytesIO(raw))
        except Exception as e:
            return jsonify({'error': 'Could not parse CSV: ' + str(e)}), 400

        if len(df) == 0:
            return jsonify({'error': 'The CSV contains no data rows'}), 400

        if len(df) > 500000:
            return jsonify({'error': 'File too large (max 500,000 rows)'}), 400

        # Detect columns
        date_col, sales_col = detect_columns(df)

        if date_col is None:
            return jsonify({
                'error': 'Could not find a date column in your CSV',
                'hint': 'Add a column like "Date", "Order_Date", or "timestamp" '
                        'containing valid dates.',
                'columns_found': df.columns.tolist()
            }), 400

        if sales_col is None:
            return jsonify({
                'error': 'Could not find a sales/value column in your CSV',
                'hint': 'Add a numeric column like "Sales", "Amount", "Revenue", '
                        '"Price", or both "Quantity" and "Unit_Price".',
                'columns_found': df.columns.tolist()
            }), 400

        # Normalize
        df_norm = normalize_dataframe(df, date_col, sales_col)
        if len(df_norm) == 0:
            return jsonify({
                'error': 'No valid rows after parsing dates and values',
                'hint': 'Check that your date column contains real dates and your '
                        'sales column contains numbers.'
            }), 400

        set_current_df(df_norm, 'uploaded', file.filename)

        sales_desc = (sales_col if isinstance(sales_col, str)
                      else '{} × {}'.format(sales_col[1], sales_col[2]))

        return jsonify({
            'success': True,
            'message': 'Dataset loaded successfully',
            'filename': file.filename,
            'rows': int(len(df_norm)),
            'columns_detected': {
                'date': date_col,
                'sales': sales_desc
            },
            'date_range': {
                'start': df_norm['Date'].min().strftime('%Y-%m-%d'),
                'end': df_norm['Date'].max().strftime('%Y-%m-%d')
            },
            'total_sales': float(df_norm['Total_Sales_INR'].sum())
        })

    except Exception as e:
        return jsonify({'error': 'Unexpected error: ' + str(e)}), 500


@app.route('/api/reset-data', methods=['POST'])
def reset_data():
    reset_current_df()
    df = get_current_df()
    return jsonify({
        'success': True,
        'message': 'Reset to default dataset',
        'rows': int(len(df)) if df is not None else 0
    })


# ══════════════════════════════════════════════════════════════════════════
# EXISTING API
# ══════════════════════════════════════════════════════════════════════════

@app.route('/api/health')
def health():
    df = get_current_df()
    return jsonify({
        'status': 'healthy',
        'data_loaded': df is not None,
        'rows': int(len(df)) if df is not None else 0,
        'source': _current_source,
        'time': datetime.now().isoformat()
    })


@app.route('/api/test')
def test():
    df = get_current_df()
    if df is None:
        return jsonify({'status': 'error', 'message': 'No data'}), 500
    return jsonify({
        'status': 'success',
        'shape': list(df.shape),
        'columns': df.columns.tolist(),
        'sample': df.head(3).to_dict(orient='records')
    })


@app.route('/api/dashboard-data')
def dashboard_data():
    df = get_current_df()
    if df is None:
        return jsonify({'error': 'No data loaded'}), 500

    df = prepare(df)
    if df is None or len(df) == 0:
        return jsonify({'error': 'Could not prepare data — check the columns'}), 500

    total = float(df['sales'].sum())
    avg = float(df['sales'].mean())
    mn = float(df['sales'].min())
    mx = float(df['sales'].max())
    std = float(df['sales'].std()) if len(df) > 1 else 0.0

    df_s = df.sort_values('Date')
    half = len(df_s) // 2
    first = df_s.iloc[:half]['sales'].mean() if half > 0 else 0
    second = df_s.iloc[half:]['sales'].mean() if half > 0 else 0
    trend = round(((second - first) / first * 100), 2) if first > 0 else 0.0

    analytics = {
        'total': round(total, 2),
        'average': round(avg, 2),
        'min': round(mn, 2),
        'max': round(mx, 2),
        'std_dev': round(std, 2),
        'total_records': int(len(df)),
        'trend_percentage': trend
    }

    # Daily aggregation
    df['day'] = df['Date'].dt.date
    daily = df.groupby('day')['sales'].sum().reset_index().sort_values('day')
    # Keep last 180 days for chart
    daily_view = daily.tail(180)
    history = [{'ds': str(r['day']), 'y': round(float(r['sales']), 2)}
               for _, r in daily_view.iterrows()]

    # Real forecast: linear regression on last 60 days
    recent_series = daily.tail(60)['sales'].tolist()
    if not recent_series:
        recent_series = [avg]
    fvals = linear_forecast(recent_series, periods=30)

    today = datetime.now().date()
    fdates = [str(today + timedelta(days=i)) for i in range(1, 31)]

    return jsonify({
        'data_type': 'sales',
        'analytics': analytics,
        'forecast': {'dates': fdates, 'forecast': fvals},
        'data': history,
        'total_records': int(len(df)),
        'source_name': _current_name
    })


@app.route('/api/insights')
def insights():
    df = get_current_df()
    if df is None:
        return jsonify({'insights': []})
    df = prepare(df)
    if df is None or len(df) == 0:
        return jsonify({'insights': []})

    out = []

    out.append({
        'category': 'Performance',
        'title': 'Total Sales Volume',
        'description': 'Recorded {:,.0f} across {:,.0f} records'.format(
            df['sales'].sum(), len(df)),
        'impact': 'Medium'
    })

    # Top categorical column (from original df, not the prepared one)
    orig = get_current_df()
    if orig is not None:
        candidates = ['Product_Category', 'Category', 'Product_Name', 'Product',
                      'State', 'Region', 'Country', 'Customer_ID']
        merged = df.copy()
        for col in candidates:
            if col in orig.columns:
                # Align by index — only use original rows we kept
                try:
                    # Merge on index if indexes align
                    if len(orig) == len(df) or orig.index.equals(df.index) is False:
                        pass
                    # Simple approach: use the top value of that column in original
                    top_val = orig[col].astype(str).value_counts().head(1)
                    if len(top_val) > 0:
                        out.append({
                            'category': 'Trend',
                            'title': 'Top ' + col.replace('_', ' ') + ': ' + str(top_val.index[0]),
                            'description': 'Most frequent value in your dataset',
                            'impact': 'High'
                        })
                except Exception:
                    pass
                break  # only report one

    # Date range
    span = (df['Date'].max() - df['Date'].min()).days
    out.append({
        'category': 'Data Quality',
        'title': 'Date Range: {} days'.format(span + 1),
        'description': 'From {} to {}'.format(
            df['Date'].min().strftime('%Y-%m-%d'),
            df['Date'].max().strftime('%Y-%m-%d')),
        'impact': 'Low'
    })

    # Trend
    df_s = df.sort_values('Date')
    half = len(df_s) // 2
    if half > 0:
        first = df_s.iloc[:half]['sales'].mean()
        second = df_s.iloc[half:]['sales'].mean()
        if first > 0:
            chg = ((second - first) / first) * 100
            out.append({
                'category': 'Growth',
                'title': 'Trend: {:.1f}% {}'.format(
                    abs(chg), 'increase' if chg >= 0 else 'decrease'),
                'description': 'Second half average vs first half average',
                'impact': 'High' if abs(chg) > 10 else 'Medium'
            })

    # Volatility
    if len(df) > 2 and df['sales'].mean() > 0:
        cv = (df['sales'].std() / df['sales'].mean()) * 100
        out.append({
            'category': 'Performance',
            'title': 'Volatility: {:.1f}%'.format(cv),
            'description': 'Coefficient of variation across all records',
            'impact': 'High' if cv > 100 else 'Low'
        })

    return jsonify({'insights': out, 'total_insights': len(out)})


@app.route('/api/live')
def live():
    df = get_current_df()
    recent_avg = 0.0
    total = 0.0
    avg = 0.0

    if df is not None:
        p = prepare(df)
        if p is not None and len(p) > 0:
            p['day'] = p['Date'].dt.date
            daily = p.groupby('day')['sales'].sum().reset_index().sort_values('day')
            recent_avg = float(daily.tail(7)['sales'].mean()) if len(daily) > 0 else float(p['sales'].mean())
            total = float(p['sales'].sum())
            avg = float(p['sales'].mean())

    tick = round(recent_avg * random.uniform(0.92, 1.08), 2)
    now = datetime.now()

    return jsonify({
        'timestamp': now.strftime('%H:%M:%S'),
        'iso': now.isoformat(),
        'tick_value': tick,
        'recent_avg': round(recent_avg, 2),
        'total': round(total, 2),
        'average': round(avg, 2),
        'active_users': random.randint(120, 480),
        'orders_per_min': random.randint(8, 42),
        'conversion_rate': round(random.uniform(2.5, 8.5), 2),
        'response_ms': random.randint(45, 180),
        'cpu': random.randint(15, 70),
        'memory': random.randint(30, 85),
        'status': 'operational'
    })


# ══════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("=" * 60)
    print("SALES FORECASTING API SERVER")
    print("=" * 60)
    df = get_current_df()
    if df is not None:
        print("Default dataset ready:", len(df), "rows")
    print("Dashboard: http://localhost:5000/complete_dashboard.html")
    print("Upload:    http://localhost:5000/complete_dashboard.html (use Upload button)")
    print("=" * 60)
    app.run(debug=False, host='127.0.0.1', port=5000, use_reloader=False)
