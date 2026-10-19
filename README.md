# Business Blind-Spot Detector

A Python and Streamlit application that analyses business order records
to identify potential operational risks.

## Features

- Upload business order records using CSV
- Preview uploaded data
- Detect potentially overdue pending orders
- Flag unusually high-value pending orders
- Assign priorities to overdue orders
- Display summary metrics and visual charts
- Download a combined findings report
- Validate required columns and flag invalid dates

## Technology Stack

- Python
- pandas
- Streamlit

## Required CSV Columns

- order_id
- customer
- order_date
- expected_delivery_date
- status
- order_value

## Run Locally

1. Install Python.
2. Install the required libraries:

   pip install -r requirements.txt

3. Start the application:

   streamlit run app.py

4. Open the local URL displayed in the terminal.

## Limitations

The application uses rule-based checks, not a trained machine-learning model.
High-value orders and overdue orders are flagged for review and are not
automatically proof of business losses.

The sample data is synthetic and intended for testing only.
