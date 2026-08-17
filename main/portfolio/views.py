import math
from datetime import datetime

from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.conf import settings
import pandas as pd
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_curve, roc_auc_score
from .models import ContactMessage

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

    df = pd.read_csv('staticfiles/files/Nat_Gas.csv', parse_dates=['Dates'], index_col='Dates')
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

def evaluate_default(request):
    # Read incoming GET parameters (if present)
    try:
        credit_lines_outstanding = request.GET.get('credit_lines_outstanding')
        loan_amt_outstanding = request.GET.get('loan_amt_outstanding')
        total_debt_outstanding = request.GET.get('total_debt_outstanding')
        years_employed = request.GET.get('years_employed')
        income = request.GET.get('income')
        fico_score = request.GET.get('fico_score')
        loan_inputs = {
            'credit_lines_outstanding': credit_lines_outstanding,
            'loan_amt_outstanding': loan_amt_outstanding,
            'total_debt_outstanding': total_debt_outstanding,
            'years_employed': years_employed,
            'income': income,
            'fico_score': fico_score,
        }

        # Convert to numeric where provided, otherwise keep None
        def to_num(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return None

        credit_lines_outstanding_n = to_num(credit_lines_outstanding)
        loan_amt_outstanding_n = to_num(loan_amt_outstanding)
        total_debt_outstanding_n = to_num(total_debt_outstanding)
        years_employed_n = to_num(years_employed)
        income_n = to_num(income)
        fico_score_n = to_num(fico_score)

        # compute derived ratios for the user input if possible
        payment_to_income_n = None
        debt_to_income_n = None
        if loan_amt_outstanding_n is not None and income_n and income_n != 0:
            payment_to_income_n = loan_amt_outstanding_n / income_n
        if total_debt_outstanding_n is not None and income_n and income_n != 0:
            debt_to_income_n = total_debt_outstanding_n / income_n

        if None in (credit_lines_outstanding_n, loan_amt_outstanding_n, total_debt_outstanding_n, years_employed_n, income_n, fico_score_n) or income_n <= 0:
            return render(request, 'index.html', {
                'show_loan_df': True,
                'loan_error': 'Complete every field and use an income greater than zero.',
                'loan_inputs': loan_inputs,
            })

        user_input = [[
            credit_lines_outstanding_n,
            debt_to_income_n,
            payment_to_income_n,
            years_employed_n,
            fico_score_n
        ]]
    except Exception:
        return render(request, 'index.html', {
            'show_loan_df': True,
            'loan_error': 'Invalid input values.',
            'loan_inputs': request.GET,
        })

    # Load dataset and prepare training data
    df = pd.read_csv('portfolio/static/files/Task 3 and 4_Loan_Data.csv')
    # derived features
    df['payment_to_income'] = df['loan_amt_outstanding'] / df['income']
    df['debt_to_income'] = df['total_debt_outstanding'] / df['income']

    features = ['credit_lines_outstanding', 'debt_to_income', 'payment_to_income', 'years_employed', 'fico_score']
    X = df[features]
    y = df['default']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    CLF = LogisticRegression(random_state=0, solver='liblinear', tol=1e-5, max_iter=10000)
    CLF.fit(X_train, y_train)

    y_prob = CLF.predict_proba(X_test)[:, 1]

    fpr, tpr, thresholds = roc_curve(y_test, y_prob)
    accuracy = (CLF.predict(X_test) == y_test).mean()
    ROCAUC = roc_auc_score(y_test, y_prob)

    df_test = X_test.copy()
    df_test['actual_default'] = y_test.values
    df_test['predicted_pd'] = y_prob

    # Create PD bins and summary
    df_test['pd_bin'] = pd.qcut(df_test['predicted_pd'], q=10, duplicates='drop')
    summary = (
        df_test.groupby('pd_bin', observed=True)
        .agg(predicted_pd=('predicted_pd', 'mean'), actual_default_rate=('actual_default', 'mean'), count=('actual_default', 'size'))
        .reset_index()
    )

    # Convert summary to records so template can iterate
    summary_records = summary.to_dict(orient='records')

    context = {
        'show_loan_df': True,
        'loan_inputs': loan_inputs,
        'coeficient': CLF.coef_.tolist(),
        'intercept': float(CLF.intercept_[0]) if hasattr(CLF.intercept_, '__len__') else float(CLF.intercept_),
        'accuracy': float(accuracy),
        'ROCAUC': float(ROCAUC),
        'summary': summary_records,
    }

    if user_input is not None:
        pred = CLF.predict(user_input)
        pred_proba = CLF.predict_proba(user_input)
        context['result'] = int(pred[0])
        context['result_probability'] = pred_proba[0].tolist()
        context['default_probability'] = float(pred_proba[0][1] * 100)

    return render(request, 'index.html', context)

def evaluate_car(request):
    try:
        Buying_Price = request.GET.get('Buying_Price')
        Maintenance_Cost = request.GET.get('Maintenance_Cost')
        Number_of_Persons = request.GET.get('Number_of_Persons')
        Number_of_Doors = request.GET.get('Number_of_Doors')
        Luggage_Boot_Size = request.GET.get('Luggage_Boot_Size')
        Safety = request.GET.get('Safety')
        car_inputs = {
            'Buying_Price': Buying_Price,
            'Maintenance_Cost': Maintenance_Cost,
            'Number_of_Persons': Number_of_Persons,
            'Number_of_Doors': Number_of_Doors,
            'Luggage_Boot_Size': Luggage_Boot_Size,
            'Safety': Safety,
        }
    except Exception:
            return render(request, 'index.html', {
                'show_car_eval': True,
                'car_eval_input_error': 'Invalid input values.',
                'car_inputs': request.GET,
            })

    cols = ['Buying', 'maint', 'doors', 'persons', 'lug_boot', 'safety', 'class']
    df = pd.read_csv("portfolio/static/files/car.data", names=cols)

    # Define mappings for ordinal features
    buying_maint_map = {'vhigh': 4, 'high': 3, 'med': 2, 'low': 1}
    doors_persons_map = {'2': 2, '3': 3, '4': 4, '5more': 5, 'more': 5}
    lug_boot_map = {'small': 1, 'med': 2, 'big': 3}
    safety_map = {'low': 1, 'med': 2, 'high': 3}
    class_map = {'unacc': 0, 'acc': 1, 'good': 2, 'vgood': 3}

    # Apply mappings to convert categorical features to numerical
    df['Buying'] = df['Buying'].map(buying_maint_map)
    df['maint'] = df['maint'].map(buying_maint_map)
    df['doors'] = df['doors'].map(doors_persons_map)
    df['persons'] = df['persons'].map(doors_persons_map)
    df['lug_boot'] = df['lug_boot'].map(lug_boot_map)
    df['safety'] = df['safety'].map(safety_map)

    # Convert the target variable 'class' to numerical
    df['class'] = df['class'].map(class_map)

    # Separate features (X) and target (y)
    X = df.drop('class', axis=1)
    y = df['class']

    import xgboost as xgb
    from sklearn.model_selection import train_test_split, GridSearchCV
    from sklearn.metrics import accuracy_score, precision_score, f1_score, recall_score, confusion_matrix
    import numpy as np # Added for np.unique

    # Split the data into training and testing sets
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    best_xgb_model = xgb.XGBClassifier()
    best_xgb_model.load_model('portfolio/static/files/car_eval_xgboost')

    # Fit GridSearchCV to the training data
    best_xgb_y_pred = best_xgb_model.predict(X_test)

    Buying_Price =buying_maint_map.get(Buying_Price)
    Maintenance_Cost = buying_maint_map.get(Maintenance_Cost)
    Number_of_Doors = doors_persons_map.get(Number_of_Doors)
    Number_of_Persons = doors_persons_map.get(Number_of_Persons)
    Luggage_Boot_Size = lug_boot_map.get(Luggage_Boot_Size)
    Safety = safety_map.get(Safety)

    to_predict = pd.DataFrame({'Buying': [Buying_Price],
    'maint': [Maintenance_Cost],
    'doors': [Number_of_Doors],
    'persons': [Number_of_Persons],
    'lug_boot': [Luggage_Boot_Size],
    'safety': [Safety]})

    class_map = {0:'Unacceptable' , 1:'Acceptable', 2:'Good', 3:'Very Good'}

    result = best_xgb_model.predict(to_predict)
    result = class_map[int(result[0])]

    accuracy = accuracy_score(y_test, best_xgb_y_pred)
    f1 = f1_score(y_test, best_xgb_y_pred, average='weighted')
    precision = precision_score(y_test, best_xgb_y_pred, average='weighted')
    recall = recall_score(y_test, best_xgb_y_pred, average='weighted')
    
    return render(request, 'index.html', {'accuracy':accuracy, 'f1':f1, 'precision':precision, 'recall':recall, 'result':result, 'show_car_eval':True, 'car_inputs': request.GET})

def contact(request):
    contact_message = None
    contact_success = False

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        subject = request.POST.get("subject", "").strip()
        message = request.POST.get("message", "").strip()

        if not all([name, email, subject, message]):
            contact_message = "All fields are required."

        else:
            try:
                # Save to database
                ContactMessage.objects.create(
                    name=name,
                    email=email,
                    subject=subject,
                    message=message
                )

                # Send message to you
                send_mail(
                    subject=f"New Contact Form Submission: {subject}",
                    message=(
                        f"Name: {name}\n"
                        f"Email: {email}\n\n"
                        f"Message:\n{message}"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=["jameskarlsilpao@gmail.com"],
                    fail_silently=False,
                )

                # Confirmation to visitor
                send_mail(
                    subject="We received your message",
                    message=(
                        f"Hi {name},\n\n"
                        "Thank you for reaching out! "
                        "I've received your message and will get back to you soon.\n\n"
                        "Best regards,\n"
                        "James"
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[email],
                    fail_silently=False,
                )

                contact_message = (
                    "Thank you for your message! "
                    "I'll get back to you soon."
                )
                contact_success = True

            except Exception as e:
                print("EMAIL ERROR:", e)
                contact_message = (
                    "Error sending message. Please try again."
                )

        return render(
            request,
            "index.html",
            {
                "contact_message": contact_message,
                "contact_success": contact_success,
            },
        )

    return redirect("index")