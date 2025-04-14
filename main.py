from utils.db_init import init_db

from flask import Flask, render_template, request, session, redirect, url_for, send_file
from utils.astro_utils import generate_natal_chart
from utils.gpt_utils import generate_forecast, ask_astro_gpt
from datetime import datetime

app = Flask(__name__)
app.secret_key = "astrogpt-secret-key"

chart_data = ""

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        session['email'] = request.form['email']
        return redirect('/profile')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/')

@app.route('/profile')
def profile():
    if 'email' not in session:
        return redirect('/login')
    return render_template('profile.html')

@app.route('/chart', methods=['POST'])
def chart():
    global chart_data
    name = request.form['name']
    dob = datetime.strptime(request.form['dob'], '%Y-%m-%d')
    tob = datetime.strptime(request.form['tob'], '%H:%M')
    place = request.form['place']
    chart_data = generate_natal_chart(name, dob, tob, place)
    return render_template('chart.html', chart_summary=chart_data)

@app.route('/forecast')
def forecast():
    global chart_data
    forecast_text = generate_forecast(chart_data, area='Career, Finance, Love')
    return render_template('forecast.html', forecast=forecast_text)

@app.route('/chat', methods=['GET', 'POST'])
def chat():
    global chart_data
    response = ''
    if request.method == 'POST':
        question = request.form['question']
        response = ask_astro_gpt(chart_data, question)
    return render_template('chat.html', response=response)

@app.route('/calendar')
def calendar():
    calendar_data = [("April 15", "Venus conjunct Jupiter - Great for love"), 
                     ("April 18", "Mars square Saturn - Low energy day")]
    return render_template('calendar.html', events=calendar_data)

init_db()

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/history')
def history():
    import sqlite3
    conn = sqlite3.connect('astro.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    c.execute("SELECT * FROM users WHERE email = ?", (session.get('email'),))
    user = c.fetchone()
    if not user:
        return redirect('/login')

    user_id = user['id']
    c.execute("SELECT * FROM charts WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    charts = c.fetchall()
    c.execute("SELECT * FROM forecasts WHERE user_id = ? ORDER BY timestamp DESC", (user_id,))
    forecasts = c.fetchall()
    conn.close()

    return render_template('history.html', charts=charts, forecasts=forecasts)

@app.route('/download_forecast')
def download_forecast():
    import sqlite3
    from fpdf import FPDF
    conn = sqlite3.connect('astro.db')
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email = ?", (session.get('email'),))
    user = c.fetchone()
    if not user:
        return redirect('/login')
    c.execute("SELECT * FROM forecasts WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (user['id'],))
    forecast = c.fetchone()
    conn.close()
    if not forecast:
        return "No forecast found"
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, forecast['forecast_text'])
    filepath = "forecast.pdf"
    pdf.output(filepath)
    return send_file(filepath, as_attachment=True)
