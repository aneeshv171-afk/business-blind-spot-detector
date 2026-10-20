# Business Blind-Spot Detector

A Python, SQL, and Streamlit application that analyses business order data to identify operational risks and provide actionable insights for small businesses.

## Business Problem

Small businesses may struggle to identify overdue orders, monitor high-value pending orders, and understand where their outstanding order value is concentrated. This application turns order records into useful operational insights.

## Live Demo

**Try the application here:** [Business Blind-Spot Detector](https://business-blind-spot-detector-d6xfsrodlghqkw8x7eyvux.streamlit.app/)

Upload a CSV file containing business order records to explore overdue-order detection, SQL analysis, customer insights, and downloadable reports.

**Source Code:** [View the GitHub Repository](https://github.com/aneeshv171-afk/business-blind-spot-detector)

## Features

- Upload business order data through CSV files.
- Preview and validate uploaded records.
- Detect potentially overdue orders and assign priorities.
- Flag high-value pending orders.
- Display business summary metrics and charts.
- Generate downloadable findings reports.
- Store and retrieve orders using SQLite.
- Analyse overdue orders using SQL queries.
- Summarise order counts and total order value by status.
- Identify the highest-value pending orders.
- Rank customers by total pending order value.

## SQL Analysis

The application uses SQL queries to generate four types of insights:

1. **Overdue orders:** Retrieve orders past their expected delivery date, excluding delivered and cancelled orders.
2. **Order value by status:** Calculate order counts and total order value for each status.
3. **Highest-value pending orders:** Rank individual pending orders by order value.
4. **Customer pending value:** Identify customers with the largest combined value of pending orders.

## Technology Stack

- Python
- pandas
- SQLite
- SQL
- Streamlit
- GitHub
- Streamlit Community Cloud

  ## Application Screenshots

### 1. Analytics Dashboard
![Analytics Dashboard](Screenshot%202026-10-20%20123536.png)

### 2. SQL Analysis and Customer Insights
![SQL Analysis](Screenshot%202026-10-20%20123558.png)

### 3. Recommended Actions
![Recommended Actions](Screenshot%202026-10-20%20123633.png)

### 4. Findings and Downloadable Report
![Findings and Downloadable Report](Screenshot%202026-10-20%20123645.png)

## Dataset Requirements

The uploaded CSV should contain these columns:

- `order_id`
- `customer`
- `order_date`
- `expected_delivery_date`
- `status`
- `order_value`

A synthetic sample dataset is used for testing. Replace it with authorised business data when applying the application to a real business.

## Run Locally

1. Install Python.
2. Clone this repository.
3. Install the required libraries:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the application:

   ```bash
   streamlit run app.py
   ```

5. Open the local URL displayed in the terminal.

## Limitations

- The application uses rule-based checks rather than a trained machine-learning model.
- Results depend on the accuracy and completeness of the uploaded data.
- Overdue and high-value flags indicate records for review; they do not independently prove financial loss.
- SQLite storage on a cloud deployment may not persist across restarts or redeployments unless persistent storage is configured.
- Synthetic sample data is intended for testing, not for drawing conclusions about a real business.

## Future Improvements

- Add customer-level and product-level performance analysis.
- Introduce automated alerts for overdue orders.
- Add authentication and business-specific data access.
- Configure persistent cloud database storage.
- Add forecasting and predictive analytics after collecting suitable historical data.
