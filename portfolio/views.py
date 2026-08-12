import math
from datetime import datetime

from django.shortcuts import render, redirect
import pandas as pd
from sklearn.linear_model import LinearRegression

# Create your views here.
def index(request):
    return render(request, 'index.html')

def evaluate_ngas(request):
    raw_in_dates = [
        request.GET.get('input-date-1'),
        request.GET.get('input-date-2'),
        request.GET.get('input-date-3'),
    ]
    raw_out_dates = [
        request.GET.get('output-date-1'),
        request.GET.get('output-date-2'),
        request.GET.get('output-date-3'),
    ]

    def parse_form_date(date_string):
        return datetime.strptime(date_string, '%Y-%m-%d').date()

    in_dates_contract = []
    out_dates_contract = []
    error_message = None

    for in_date, out_date in zip(raw_in_dates, raw_out_dates):
        if in_date and out_date:
            parsed_in = parse_form_date(in_date)
            parsed_out = parse_form_date(out_date)
            if parsed_in >= parsed_out:
                error_message = f'Injection date must be earlier than withdrawal date for pair {in_date} / {out_date}.'
                break
            in_dates_contract.append(parsed_in)
            out_dates_contract.append(parsed_out)
        elif in_date or out_date:
            error_message = 'Each injection date must have a matching withdrawal date.'
            break

    if error_message:
        return render(request, 'index.html', {
            'show_ngas': True,
            'ngas_error': error_message,
            'in_dates': [],
            'output_dates': [],
            'predicted_in_prices': [],
            'predicted_out_prices': [],
            'contract_value': None,
        })

    # Make sure we never pass empty contract dates into the prediction model.
    if not in_dates_contract or not out_dates_contract:
        return render(request, 'index.html', {
            'show_ngas': True,
            'in_dates': [],
            'output_dates': [],
            'predicted_in_prices': [],
            'predicted_out_prices': [],
            'contract_value': None,
        })

    df = pd.read_csv('C:/Users/reidj/Desktop/Portfolio2.0/main/portfolio/static/files/Nat_Gas.csv', parse_dates=['Dates'], index_col='Dates')
    df["Days"] = (df.index - df.index.min()).days

    # Define feature (X) and target (y) for simple linear regression
    X = df[['Days']]
    y = df['Prices']

    # Initialize and train a simple Linear Regression model
    lr_model = LinearRegression()
    lr_model.fit(X, y)

    # Make predictions for the entire dataset
    lr_predictions = lr_model.predict(X)

    # Determine the last date in your existing DataFrame
    last_date = df.index.max()

    # Generate a range of future dates for the next 12 months (e.g., monthly)
    # We'll use 'MS' for Month Start frequency to align with the data's monthly nature
    future_dates = pd.date_range(start=last_date + pd.DateOffset(days=1),
                                periods=12,
                                freq='MS')

    # Create a DataFrame for future predictions
    future_df = pd.DataFrame(index=future_dates)

    # Calculate 'Days' for these future dates, relative to the original start date
    future_df['Days'] = (future_df.index - df.index.min()).days

    # Use the trained model to predict prices for these future 'Days'
    future_predictions = lr_model.predict(future_df[['Days']])

    # Add predictions to the future_df
    future_df['Predicted Prices'] = future_predictions

    # The price_contract function as provided by the user
    def price_contract(in_dates, in_prices, out_dates, out_prices, rate, storage_cost_rate, total_vol, injection_withdrawal_cost_rate):
        volume = 0
        buy_cost = 0
        cash_in = 0

        # Ensure dates are in sequence
        all_dates = sorted(list(set(in_dates + out_dates)))

        for i in range(len(all_dates)):
            start_date = all_dates[i]
            if start_date in in_dates:
                # Inject on these dates and sum up cash flows
                if volume <= total_vol - rate:
                    volume += rate
                    # Cost to purchase gas
                    buy_cost += rate * in_prices[in_dates.index(start_date)]
                    # Injection cost
                    injection_cost = rate * injection_withdrawal_cost_rate
                    buy_cost += injection_cost
                    print('Injected gas on %s at a price of %s' % (start_date, in_prices[in_dates.index(start_date)]))
                else:
                    # We do not want to inject when rate is greater than total volume minus volume
                    print('Injection is not possible on date %s as there is insufficient space in the storage facility' % start_date)
            elif start_date in out_dates:
                #Withdraw on these dates and sum cash flows
                if volume >= rate:
                    volume -= rate
                    cash_in += rate * out_prices[out_dates.index(start_date)]
                    # Withdrawal cost
                    withdrawal_cost = rate * injection_withdrawal_cost_rate
                    cash_in -= withdrawal_cost
                    print('Extracted gas on %s at a price of %s' % (start_date, out_prices[out_dates.index(start_date)]))
                else:
                    # we cannot withdraw more gas than is actually stored
                    print('Extraction is not possible on date %s as there is insufficient volume of gas stored' % start_date)

        # Calculate storage cost for the duration of the contract
        # Ensure min(in_dates) and max(out_dates) are handled correctly if lists are empty.
        # Using a try-except block or checking list emptiness before accessing min/max is safer.
        # For this example, assuming in_dates and out_dates are not empty.
        if in_dates and out_dates:
            duration_in_months = math.ceil((max(out_dates) - min(in_dates)).days / 30.0)
            store_cost = duration_in_months * storage_cost_rate
        else:
            store_cost = 0 # No storage cost if no in/out dates

        return cash_in - store_cost - buy_cost


    print("### Contract Valuation with Linear Regression Predicted Prices ###")

    # Convert contract dates to datetime objects for 'Days' calculation
    def get_predicted_prices(dates_list, model, df_min_date):
        if not dates_list:
            return []
        dt_dates = [datetime(d.year, d.month, d.day) if not isinstance(d, datetime) else d for d in dates_list]

        temp_df = pd.DataFrame(index=pd.to_datetime(dt_dates))
        temp_df['Days'] = (temp_df.index - df_min_date).days

        predicted_prices = model.predict(temp_df[['Days']])
        return [round(float(price), 2) for price in predicted_prices]

    # Get prices for injection and withdrawal dates using the linear regression model
    # Ensure df.index.min() is available from previous cells
    contract_in_prices = get_predicted_prices(in_dates_contract, lr_model, df.index.min())
    contract_out_prices = get_predicted_prices(out_dates_contract, lr_model, df.index.min())

    # Contract parameters
    if request.session.get('rate'): rate = int(request.session.get('rate')) 
    else: rate = 100000  # rate of gas in cubic feet per day
    if request.session.get('storage_cost_rate'): storage_cost_rate = int(request.session.get('storage_cost_rate'))
    else: storage_cost_rate = 10000  # total volume in cubic feet (per month)
    if request.session.get('injection_withdrawal_cost_rate'): injection_withdrawal_cost_rate = float(request.session.get('injection_withdrawal_cost_rate'))
    else: injection_withdrawal_cost_rate = 0.0005  # $/cf
    if request.session.get('max_storage_volume'): max_storage_volume = int(request.session.get('max_storage_volume'))
    else: max_storage_volume = 500000 # maximum storage capacity of the storage facility

    print("\n--- Contract Details ---")
    print(f"Injection Dates: {in_dates_contract}")
    print(f"Predicted Injection Prices: {[f'{p:.2f}' for p in contract_in_prices]}")
    print(f"Withdrawal Dates: {out_dates_contract}")
    print(f"Predicted Withdrawal Prices: {[f'{p:.2f}' for p in contract_out_prices]}")

    # Calculate the contract value
    result = round(price_contract(
        in_dates_contract, contract_in_prices,
        out_dates_contract, contract_out_prices,
        rate, storage_cost_rate,
        max_storage_volume, injection_withdrawal_cost_rate
    ), 2)

    request.session['evaluate_ngas'] = True  # Store the result in the session
    return render(request, 'index.html', {
        'in_dates': in_dates_contract,
        'output_dates': out_dates_contract,
        'predicted_in_prices': contract_in_prices,
        'predicted_out_prices': contract_out_prices,
        'contract_value': result,
        'show_ngas': True,
    })

def set_ngas_fees(request):
    if request.method == 'POST':
        if request.POST.get('reset_fees'):
            for fee_key in ('rate', 'storage_cost_rate', 'injection_withdrawal_cost_rate'):
                request.session.pop(fee_key, None)
        else:
            if request.POST.get('rate') is not None:
                request.session['rate'] = request.POST.get('rate')
            if request.POST.get('storage_cost_rate') is not None:
                request.session['storage_cost_rate'] = request.POST.get('storage_cost_rate')
            if request.POST.get('injection_withdrawal_cost_rate') is not None:
                request.session['injection_withdrawal_cost_rate'] = request.POST.get('injection_withdrawal_cost_rate')
    #return redirect(request.META.get('HTTP_REFERER', '/'))
    return render(request, 'index.html',{'show_ngas': True})
