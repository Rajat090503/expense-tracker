from flask import Flask, render_template, request, redirect
import csv
import os
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64
import calendar

app = Flask(__name__)

CSV_FILE = 'expenses.csv'

# Ensure CSV file exists and has header
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['Date', 'Category', 'Amount', 'Note'])


@app.route('/')
def index():
    return render_template('daily.html')  # Your form page

@app.route('/add', methods=['POST'])
def add_expense():
    date = request.form['date']
    category = request.form['category']
    amount = request.form['amount']
    note = request.form.get('note', '')

    with open(CSV_FILE, 'a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow([date, category, amount, note])

    return redirect('/')

@app.route('/monthly', methods=['GET', 'POST'])
def monthly_expense():
    # Load CSV
    df = pd.read_csv(CSV_FILE, parse_dates=['Date'])
    if df.empty:
        return "No expense data to show."

    # Default to latest month and year
    latest_date = df['Date'].max()
    selected_month = latest_date.month
    selected_year = latest_date.year

    if request.method == 'POST':
        selected_month = int(request.form.get('month', selected_month))
        selected_year = int(request.form.get('year', selected_year))
    else:
        if 'month' in request.args and 'year' in request.args:
            selected_month = int(request.args.get('month'))
            selected_year = int(request.args.get('year'))

    # Filter for selected month/year
    df_month = df[(df['Date'].dt.month == selected_month) & (df['Date'].dt.year == selected_year)]

    if df_month.empty:
        return f"No expenses found for {calendar.month_name[selected_month]} {selected_year}."

    df_month['Amount'] = pd.to_numeric(df_month['Amount'], errors='coerce').fillna(0)

    # Group by Category for pie chart
    summary = df_month.groupby('Category')['Amount'].sum()

    # Create pie chart (no total label)
    fig, ax = plt.subplots(figsize=(7,7))

    wedges, texts, autotexts = ax.pie(
        summary,
        labels=summary.index,           
        autopct='%1.1f%%',              
        startangle=90,
        textprops={'fontsize': 12, 'color': 'black'},  
        labeldistance=1.05              
    )

    ax.axis('equal') 
    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    image_base64 = base64.b64encode(buf.read()).decode('utf-8')
    plt.close(fig)

    # Prepare detailed expenses for table
    df_month = df_month.copy()
    df_month['Date'] = df_month['Date'].dt.strftime('%Y-%m-%d')

    detailed_expenses = df_month.to_dict(orient='records')

    month_names = list(calendar.month_name)[1:]  # January to December

    return render_template(
        'monthly.html',
        chart=image_base64,
        month=selected_month,
        year=selected_year,
        month_names=month_names,
        detailed_expenses=detailed_expenses
    )


@app.route('/yearly', methods=['GET', 'POST'])
def yearly_expense():
    df = pd.read_csv(CSV_FILE, parse_dates=['Date'])
    if df.empty:
        return "No expense data to show."

    years = sorted(df['Date'].dt.year.unique(), reverse=True)
    selected_year = years[0]

    if request.method == 'POST':
        selected_year = int(request.form.get('year', selected_year))
    else:
        if 'year' in request.args:
            selected_year = int(request.args.get('year'))

    df_year = df[df['Date'].dt.year == selected_year].copy()
    if df_year.empty:
        return f"No expenses found for {selected_year}."

    df_year['Amount'] = pd.to_numeric(df_year['Amount'], errors='coerce').fillna(0)
    df_year['Month'] = df_year['Date'].dt.month

    # Aggregate total expense by month
    monthly_sum = df_year.groupby('Month')['Amount'].sum().reindex(range(1,13), fill_value=0)

    # Bar chart: months on x-axis, total expenses on y-axis
    fig, ax = plt.subplots(figsize=(10,6))
    ax.bar(monthly_sum.index.map(lambda m: calendar.month_abbr[m]), monthly_sum.values, color='skyblue')
    ax.set_title(f'Total Expenses by Month - {selected_year}')
    ax.set_xlabel('Month')
    ax.set_ylabel('Total Expense (₹)')
    ax.grid(axis='y', linestyle='--', alpha=0.7)

    buf = io.BytesIO()
    plt.tight_layout()
    plt.savefig(buf, format='png')
    plt.close(fig)
    buf.seek(0)
    chart = base64.b64encode(buf.read()).decode('utf-8')

    # Find highest and lowest expense months and reasons
    max_month = monthly_sum.idxmax()
    min_month = monthly_sum.idxmin()

    max_expense = monthly_sum[max_month]
    min_expense = monthly_sum[min_month]

   
    max_month_data = df_year[df_year['Month'] == max_month]
    top_categories = max_month_data.groupby('Category')['Amount'].sum().sort_values(ascending=False).head(3).to_dict()

    
    min_month_data = df_year[df_year['Month'] == min_month]
    low_categories = min_month_data.groupby('Category')['Amount'].sum().sort_values(ascending=False).head(3).to_dict()

    
    df_year['Date'] = df_year['Date'].dt.strftime('%Y-%m-%d')
    detailed_expenses = df_year.to_dict(orient='records')

    return render_template(
        'yearly.html',
        chart=chart,
        year=selected_year,
        years=years,
        detailed_expenses=detailed_expenses,
        max_month=calendar.month_name[max_month],
        max_expense=max_expense,
        max_reasons=top_categories,
        min_month=calendar.month_name[min_month],
        min_expense=min_expense,
        min_reasons=low_categories
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

