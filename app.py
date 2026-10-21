import streamlit as st
import pandas as pd
from datetime import date
from database import initialize_database, save_orders, load_orders, get_order_count, get_overdue_orders, get_order_value_by_status, get_high_value_pending_orders, get_pending_value_by_customer
initialize_database()
st.set_page_config(
    page_title="Business Blind-Spot Detector",
    page_icon="🔎",
    layout="wide"
)

REQUIRED_COLUMNS = [
    "order_id",
    "customer",
    "expected_delivery_date",
    "status",
    "order_value"
]


COLUMN_ALIASES = {
    "order_id": [
        "order_id", "orderid", "order_number", "order_no",
        "invoice_id", "invoice_number", "transaction_id",
        "reference_number", "id"
    ],
    "customer": [
        "customer", "customer_name", "client", "buyer",
        "client_name", "customer_id", "account_name"
    ],
    "order_date": [
        "order_date", "date", "purchase_date",
        "transaction_date", "sales_date", "invoice_date",
        "created_at", "booking_date"
    ],
    "expected_delivery_date": [
        "expected_delivery_date", "delivery_due",
        "due_date", "delivery_date", "expected_date",
        "promised_delivery_date"
    ],
    "status": [
        "status", "order_status", "delivery_status",
        "payment_status", "shipment_status"
    ],
    "order_value": [
        "order_value", "sales_amount", "revenue",
        "total_sales", "amount", "net_sales",
        "turnover", "total_amount", "invoice_amount",
        "total_revenue", "gross_sales"
    ],
    "product": [
        "product", "product_name", "item", "item_name",
        "product_title", "sku_name", "product_category",
        "category", "description"
    ],
    "region": [
        "region", "location", "area", "territory",
        "branch", "branch_name", "city", "state",
        "district", "country", "sales_region"
    ],
    "quantity": [
        "quantity", "qty", "units_sold", "units",
        "unit_sold", "sales_quantity", "volume",
        "number_of_items"
    ],
    "price": [
        "price", "unit_price", "selling_price",
        "sale_price", "product_price", "average_price"
    ],
    "marketing_spend": [
        "marketing_spend", "ad_spend", "advertising_cost",
        "marketing_cost", "campaign_spend", "ad_cost"
    ],
    "profit": [
        "profit", "net_profit", "gross_profit",
        "profit_amount", "earnings"
    ],
    "cost": [
        "cost", "unit_cost", "product_cost",
        "cost_price", "total_cost", "expenses"
    ],
    "employee": [
        "employee", "employee_name", "staff",
        "staff_name", "employee_id", "worker"
    ],
    "department": [
        "department", "team", "division", "business_unit"
    ],
    "salary": [
        "salary", "annual_salary", "monthly_salary",
        "wage", "pay", "compensation"
    ]
}


def standardize_columns(df):
    """Recognise common column names and standardise them."""
    df = df.copy()

    # Normalise column names first
    df.columns = (
        df.columns.astype(str)
        .str.strip()
        .str.lower()
        .str.replace(r"[\s\-]+", "_", regex=True)
    )

    rename_map = {}
    used_columns = set()

    for standard_name, aliases in COLUMN_ALIASES.items():
        normalized_aliases = {
            str(alias).strip().lower().replace(" ", "_").replace("-", "_")
            for alias in aliases
        }

        for column in df.columns:
            if (
                column in normalized_aliases
                and standard_name not in used_columns
            ):
                rename_map[column] = standard_name
                used_columns.add(standard_name)
                break

    return df.rename(columns=rename_map)
    
def profile_dataset(df):
    """Generate a general-purpose profile for any tabular dataset."""
    profile = {
        "rows": len(df),
        "columns": len(df.columns),
        "missing_values": int(df.isna().sum().sum()),
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric_columns": df.select_dtypes(include="number").columns.tolist(),
        "text_columns": df.select_dtypes(include=["object", "string", "category"]).columns.tolist(),
        "date_columns": [],
    }

    # Identify columns that appear to contain dates.
    for column in df.columns:
        name = str(column).lower()
        if any(word in name for word in ["date", "time", "created", "updated"]):
            profile["date_columns"].append(column)

    return profile


def detect_overdue_orders(orders, today=None):
    """Identify pending orders whose delivery deadlines have passed."""

    if today is None:
        today = date.today()

    data = orders.copy()
    data_issues = []

    missing_columns = [
        col for col in REQUIRED_COLUMNS
        if col not in data.columns
    ]

    if missing_columns:
        return pd.DataFrame(), [
            f"Missing required columns: {', '.join(missing_columns)}"
        ]

    # Clean and validate dates
    data["expected_delivery_date"] = pd.to_datetime(
        data["expected_delivery_date"], errors="coerce"
    )

    invalid_dates = data["expected_delivery_date"].isna()
    if invalid_dates.any():
        data_issues.append(
            f"{int(invalid_dates.sum())} record(s) have missing or invalid "
            "expected delivery dates and were excluded from detection."
        )

    # Clean and validate order values
    data["order_value"] = pd.to_numeric(
        data["order_value"], errors="coerce"
    )

    invalid_values = data["order_value"].isna()
    if invalid_values.any():
        data_issues.append(
            f"{int(invalid_values.sum())} record(s) have missing or invalid "
            "order values."
        )

    # Identify pending orders past their delivery deadline
    pending = (
        data["status"].astype("string").str.strip().str.casefold()
        == "pending"
    )

    overdue = (
        pending
        & data["expected_delivery_date"].notna()
        & (data["expected_delivery_date"].dt.date < today)
    )

    findings = data.loc[overdue].copy()

    findings["days_overdue"] = (
        pd.Timestamp(today)
        - findings["expected_delivery_date"].dt.normalize()
    ).dt.days

    findings["priority"] = findings["days_overdue"].apply(
        lambda days: (
            "High" if days >= 7
            else "Medium" if days >= 3
            else "Low"
        )
    )

    findings["finding"] = "Delivery deadline has passed"

    findings["recommended_action"] = (
        "Verify delivery status and contact the responsible person"
    )

    # Show the most urgent orders first
    priority_rank = {"High": 1, "Medium": 2, "Low": 3}

    findings["priority_rank"] = findings["priority"].map(priority_rank)

    findings = findings.sort_values(
        ["priority_rank", "days_overdue"],
        ascending=[True, False]
    )

    return findings, data_issues

    
def detect_large_pending_orders(orders):
    """Flag pending orders in the top 10% by order value."""

    data = orders.copy()

    data["status"] = (
        data["status"].astype("string").str.strip().str.casefold()
    )
    data["order_value"] = pd.to_numeric(
        data["order_value"], errors="coerce"
    )

    valid_values = data["order_value"].dropna()

    if valid_values.empty:
        return pd.DataFrame(), None

    threshold = valid_values.quantile(0.90)

    findings = data[
        (data["status"] == "pending")
        & (data["order_value"] >= threshold)
    ].copy()

    findings["finding"] = "High-value pending order"
    findings["recommended_action"] = (
        "Review the order value, delivery status, and expected completion."
    )

    return findings.sort_values("order_value", ascending=False), threshold



st.title("🔎 Business Blind-Spot Detector")

st.write(
    "Upload business records to identify operational risks "
    "and receive actionable recommendations."
)

st.divider()

st.header("1. Upload Business Records")

uploaded_file = st.file_uploader(
    "Choose a CSV file",
    type=["csv"]
)

if uploaded_file is not None:
    try:
        df = pd.read_csv(uploaded_file)

        
        # Standardize column names and recognise common aliases
        df = standardize_columns(df)
        profile = profile_dataset(df)

       # Automatically identify the dataset type
        column_names = [str(col).lower() for col in df.columns]

        dataset_types = {
            "Sales / Revenue": [
                "revenue", "sales", "sales_amount", "order_value",
                "price", "quantity", "units_sold"
            ],
            "Inventory / Stock": [
                "stock", "inventory", "warehouse", "reorder_level",
                "available_quantity", "stock_quantity"
            ],
            "Employee / HR": [
                "employee", "employee_id", "salary", "department",
                "designation", "performance_rating"
            ],
            "Customer / Marketing": [
                "customer", "customer_id", "marketing_spend",
                "campaign", "conversion_rate", "lead_source"
            ],
            "Orders / Operations": [
                "order_id", "order_date", "expected_delivery_date",
                "delivery_date", "order_status", "status"
            ],
        } 

        type_scores = {
           dataset_type: sum(
                1 for keyword in keywords
                if any(keyword in column for column in column_names)
            )
            for dataset_type, keywords in dataset_types.items()
        }
 
        best_type = max(type_scores, key=type_scores.get)

        if type_scores[best_type] == 0:
            detected_type = "General / Other Dataset"
        else:
           highest_score = type_scores[best_type]
           matching_types = [
               name for name, score in type_scores.items()
               if score == highest_score
           ]

           detected_type = (
               matching_types[0]
               if len(matching_types) == 1
               else "Mixed Business Dataset"
           )

        st.subheader("Automatic Dataset Detection")
        st.info(f"Detected dataset type: **{detected_type}**")

        
        # Automatic Business Insights
        st.subheader("Automatic Business Insights")
        
        
        
        if detected_type == "Sales / Revenue":
            st.write("Sales dataset detected. Analysing sales performance.")

            numeric_cols = df.select_dtypes(include="number").columns.tolist()

            if numeric_cols:
                for col in numeric_cols:
                    total = df[col].sum()
                    average = df[col].mean()

                    st.write(
                        f"**{col}** — Total: {total:,.2f} | "
                        f"Average: {average:,.2f}"
                    )

                # Identify a likely product column.
                product_col = next(
                    (
                        col for col in df.columns
                        if any(word in col.lower() for word in
                               ["product", "item", "product_name", "sku"])
                    ),
                    None,
                )

                # Identify a likely sales or revenue column.
                sales_col = next(
                    (
                        col for col in numeric_cols
                        if any(word in col.lower() for word in
                               ["sales", "revenue", "amount", "total"])
                    ),
                    None,
                )

                if product_col and sales_col:
                    product_sales = (
                        df.groupby(product_col, dropna=False)[sales_col]
                        .sum()
                        .sort_values(ascending=False)
                    )

                    st.subheader("Top-Performing Products")
                    st.dataframe(
                        product_sales.head(5).rename("Total Sales").reset_index(),
                        use_container_width=True,
                    )

                    st.subheader("Potentially Low-Selling Products")

                    if len(product_sales) >= 2:
                        low_sales = product_sales[
                            product_sales < product_sales.median()
                        ]

                        if not low_sales.empty:
                            st.dataframe(
                                low_sales.rename("Total Sales").reset_index(),
                                use_container_width=True,
                            )
                        else:
                            st.write(
                                "No products fall below the median sales value."
                            )
                    else:
                        st.write(
                            "Not enough distinct products to compare sales."
                        )

                    st.caption(
                        "Low-selling products are flagged relative to the "
                        "dataset median, not as proof of poor performance."
                    )
                else:
                    st.info(
                        "Product-level analysis requires a recognisable "
                        "product column and a numeric sales/revenue column. "
                        "Your numeric summaries are still available above."
                    )
            else:
                st.info("No numeric columns were found for sales analysis.")

        
        elif detected_type == "Inventory / Stock":
            st.write("Inventory dataset detected. Checking stock levels.")

            numeric_cols = df.select_dtypes(include="number").columns.tolist()

            stock_col = next(
                (
                    col for col in numeric_cols
                    if any(word in col.lower() for word in
                           ["stock_quantity", "stock_qty", "quantity",
                            "qty", "inventory_level", "units_in_stock"])
                ),
                None,
            )

            item_col = next(
                (
                    col for col in df.columns
                    if any(word in col.lower() for word in
                           ["product", "item", "sku", "product_name"])
                ),
                None,
            )

            if stock_col:
                stock_values = pd.to_numeric(df[stock_col], errors="coerce")

                st.write(f"**Stock column detected:** {stock_col}")
                st.metric(
                    "Total recorded stock",
                    f"{stock_values.sum(skipna=True):,.0f}",
                )

                
                reorder_col = next(
                    (
                        col for col in df.columns
                        if "reorder" in col.lower()
                        and "level" in col.lower()
                    ),
                    None,
                )

                if reorder_col:
                    reorder_values = pd.to_numeric(
                        df[reorder_col], errors="coerce"
                    )

                    low_stock = df.loc[
                        stock_values.notna()
                        & reorder_values.notna()
                        & (stock_values <= reorder_values)
                    ].copy()

                    threshold = None
                    st.write(
                        f"**Reorder-level column detected:** {reorder_col}"
                    )
                    st.write(
                        f"**Products at or below reorder level:** "
                        f"{len(low_stock)}"
                    )
                else:
                    threshold = stock_values.quantile(0.25)

                    low_stock = df.loc[
                        stock_values.notna()
                        & (stock_values <= threshold)
                    ].copy()

                    st.write(
                        "No reorder-level column found. Using the "
                        "relative low-stock threshold instead."
                    )


                if threshold is not None:
                    st.write(
                        f"**Relative low-stock threshold:** {threshold:,.2f}"
                    )

                if not low_stock.empty:
                    st.subheader("Items to Review for Replenishment")

                    display_cols = (
                        [item_col, stock_col]
                        if item_col and item_col != stock_col
                        else [stock_col]
                    )

                    st.dataframe(
                        low_stock[display_cols].sort_values(
                            by=stock_col, ascending=True
                        ),
                        use_container_width=True,
                    )
                else:
                    st.write("No low-stock items were identified.")

                st.caption(
                    "This is a relative indicator based on the dataset's "
                    "lower stock values, not a confirmed reorder requirement. "
                    "Use reorder points and supplier lead times when available."
                )
            else:
                st.info(
                    "No recognisable stock-quantity column was found. "
                    "Look for columns such as quantity, stock_qty, or "
                    "units_in_stock. Other dataset analyses remain available."
                )

        
        
        elif detected_type == "Employee / HR":
            st.write(
                "Employee dataset detected. "
                "Review workforce distribution and numeric measures."
            )

        
        
        elif detected_type == "Customer / Marketing":
            st.write("Customer or marketing dataset detected.")

            numeric_cols = df.select_dtypes(include="number").columns.tolist()

            spend_col = next(
                (
                    col for col in numeric_cols
                    if any(word in col.lower() for word in [
                        "marketing_spend", "ad_spend", "advertising_cost",
                        "campaign_cost", "marketing_cost", "ad_cost"
                    ])
                ),
                None,
            )

            conversion_col = next(
                (
                    col for col in numeric_cols
                    if any(word in col.lower() for word in [
                        "conversion", "conversions", "purchases"
                    ])
                ),
                None,
            )

            if spend_col:
                spend = pd.to_numeric(df[spend_col], errors="coerce")

                st.metric("Total Marketing Spend", f"{spend.sum():,.2f}")
                st.metric("Average Marketing Spend", f"{spend.mean():,.2f}")

                if conversion_col:
                    conversions = pd.to_numeric(
                        df[conversion_col], errors="coerce"
                    )
                    total_conversions = conversions.sum()
                    total_spend = spend.sum()

                    st.metric("Total Conversions", f"{total_conversions:,.0f}")

                    if total_conversions > 0:
                        st.metric(
                            "Cost per Conversion",
                            f"{total_spend / total_conversions:,.2f}",
                        )
                    else:
                        st.info(
                            "No positive conversions were recorded, "
                            "so cost per conversion cannot be calculated."
                        )
                else:
                    st.info(
                        "No recognisable conversion column was found. "
                        "Marketing spend was analysed independently."
                    )
            else:
                st.info(
                    "No recognisable marketing-spend column was found. "
                    "General dataset analysis remains available."
                )

        
        elif detected_type == "Orders / Operations":
            st.write(
                "Orders dataset detected. "
                "Review order statuses, delivery dates, and pending orders."
            )
            
        
        else:
            st.write(
                "General dataset detected. Generating useful findings "
                "from the available data."
            )

            numeric_cols = df.select_dtypes(include="number").columns.tolist()

            if numeric_cols:
                st.subheader("Key Numeric Findings")

                numeric_totals = df[numeric_cols].sum(numeric_only=True)
                numeric_totals = numeric_totals[
                    numeric_totals.notna()
                ]

                if not numeric_totals.empty:
                    highest_total_col = numeric_totals.idxmax()

                    st.write(
                        f"**Largest numeric total:** {highest_total_col} "
                        f"({numeric_totals[highest_total_col]:,.2f})"
                    )

                for col in numeric_cols:
                    values = pd.to_numeric(df[col], errors="coerce").dropna()

                    if values.empty:
                        continue

                    average = values.mean()
                    minimum = values.min()
                    maximum = values.max()

                    if values.nunique() <= 1:
                        st.write(
                            f"**{col}:** This column has no variation "
                            "in its non-missing values."
                        )
                    elif minimum < average * 0.5 and average > 0:
                        st.write(
                            f"**{col}:** Some values are substantially "
                            "below the average. Review the lowest values."
                        )
                    elif maximum > average * 2 and average > 0:
                        st.write(
                            f"**{col}:** Some values are substantially "
                            "above the average. Check whether these are "
                            "expected or unusual."
                        )
            else:
                st.info(
                    "No numeric columns are available. Review text columns "
                    "and data quality findings to understand this dataset."
                )


  

        st.subheader("Automatic Dataset Profile")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Rows", profile["rows"])
        col2.metric("Columns", profile["columns"])
        col3.metric("Missing Values", profile["missing_values"])
        col4.metric("Duplicate Rows", profile["duplicate_rows"])

        st.write("Numeric columns:", profile["numeric_columns"])
        st.write("Text columns:", profile["text_columns"])
        st.write("Potential date columns:", profile["date_columns"])
        st.subheader("Data Quality Checks")

        quality_results = pd.DataFrame({
        "Column": df.columns,
        "Data Type": df.dtypes.astype(str).values,
        "Missing Values": df.isna().sum().values,
        "Missing (%)": (df.isna().mean().values * 100).round(2),
        "Unique Values": df.nunique().values,
        })

        st.dataframe(quality_results, use_container_width=True)
        if profile["numeric_columns"]:
            st.subheader("Automatic Numeric Analysis")

            numeric_summary = df[profile["numeric_columns"]].describe().T
            numeric_summary = numeric_summary.round(2)
            st.dataframe(numeric_summary, use_container_width=True)

            
            st.subheader("Business Recommendations")

            recommendations = []

            for col in profile["numeric_columns"]:
                values = pd.to_numeric(df[col], errors="coerce").dropna()

                if values.empty:
                    continue

                if values.nunique() <= 1:
                    recommendations.append(
                        f"Review '{col}': all available values are identical. "
                        "Confirm whether this is expected."
                    )
                    continue

                average = values.mean()
                minimum = values.min()
                maximum = values.max()

                if average > 0 and maximum > average * 2:
                    recommendations.append(
                        f"Investigate unusually high values in '{col}'. "
                        "Check whether they represent genuine activity or data errors."
                    )

                if average > 0 and minimum < average * 0.5:
                    recommendations.append(
                        f"Review unusually low values in '{col}' to determine "
                        "whether they indicate underperformance or normal variation."
                    )

            if recommendations:
                for recommendation in recommendations:
                    st.write(f"- {recommendation}")
            else:
                st.write(
                    "No obvious numeric patterns requiring review were detected "
                    "using these basic checks."
                )


            st.subheader("Automatic Data Visualizations")

            for column in profile["numeric_columns"][:4]:
                st.write(f"Distribution of {column}")
                st.bar_chart(df[column].dropna().reset_index(drop=True))

        else:
            st.info("No numeric columns were detected in this dataset.")

        
        # Automatic Business Insights
        st.subheader("Automatic Business Insights")

        column_lookup = {str(col).lower(): col for col in df.columns}

        revenue_col = next(
            (column_lookup[name] for name in ["revenue", "sales", "total_sales", "sales_amount", "total_revenue", "amount", "order_amount", "selling_price","net_sales", "gross_sales", "total_amount"]
             if name in column_lookup),
            None
        )
        product_col = next(
            (column_lookup[name] for name in ["product", "product_name", "item", "category"]
             if name in column_lookup),
            None
        )
        region_col = next(
            (column_lookup[name] for name in ["region", "location", "area", "territory"]
             if name in column_lookup),
            None
        )
        quantity_col = next(
            (column_lookup[name] for name in ["units_sold", "quantity", "qty", "units"]
             if name in column_lookup),
            None
        )

        if revenue_col and pd.api.types.is_numeric_dtype(df[revenue_col]):
            st.metric("Total Revenue / Sales", f"{df[revenue_col].sum():,.2f}")

            if product_col:
                product_summary = (
                    df.groupby(product_col, dropna=False)[revenue_col]
                    .sum()
                    .sort_values(ascending=False)
                    .head(5)
                    .reset_index()
                )
                st.write("Top 5 products or categories by revenue")
                st.dataframe(product_summary, use_container_width=True)

            if region_col:
                region_summary = (
                    df.groupby(region_col, dropna=False)[revenue_col]
                    .sum()
                    .sort_values(ascending=False)
                    .head(5)
                    .reset_index()
                )
                st.write("Top 5 regions by revenue")
                st.dataframe(region_summary, use_container_width=True)

        if quantity_col and pd.api.types.is_numeric_dtype(df[quantity_col]):
            st.metric("Total Units / Quantity", f"{df[quantity_col].sum():,.2f}")

        if not revenue_col and not quantity_col:
            st.info(
                "No recognised revenue, sales, or quantity column was found. "
                "Use the dataset profile and numeric analysis above to explore this dataset."
            )
        st.success("File uploaded successfully!")


        # Check for duplicate order IDs
        if "order_id" in df.columns:
            duplicate_count = int(
                df["order_id"].duplicated().sum()
            )

            if duplicate_count > 0:
                st.warning(
                    f"{duplicate_count} duplicate order ID(s) found. "
                    "Review these records before acting on the findings."
                )
            else:
                st.success("No duplicate order IDs detected.")

        col1, col2 = st.columns(2)

        col1.metric("Total Records", len(df))
        col2.metric("Total Columns", len(df.columns))

        st.subheader("2. Preview Business Records")
        st.dataframe(df.head(10), use_container_width=True)

        if all(col in df.columns for col in REQUIRED_COLUMNS):
            save_orders(df)
            st.success(f"SQLite database contains {get_order_count()} orders.")
        else:
            st.info(
                "This dataset is not compatible with order-specific SQL analysis. "
                "Generic dataset analysis and Automatic Business Insights remain available."
            )
    

        st.subheader("3. Business Blind Spots")
        if not all(col in df.columns for col in REQUIRED_COLUMNS):
            st.subheader("Universal Business Findings")

                        # Dataset Summary: descriptive statistics, not findings
            st.markdown("### Dataset Summary")
            numeric_cols = df.select_dtypes(include="number").columns

            if len(numeric_cols) > 0:
                summary_rows = []

                for col in numeric_cols:
                    values = df[col].dropna()
                    if not values.empty:
                        summary_rows.append({
                            "Column": col,
                            "Count": int(values.count()),
                            "Total": round(float(values.sum()), 2),
                            "Average": round(float(values.mean()), 2),
                            "Minimum": round(float(values.min()), 2),
                            "Maximum": round(float(values.max()), 2)
                        })

                st.dataframe(
                    pd.DataFrame(summary_rows),
                    use_container_width=True,
                    hide_index=True
                )
            else:
                st.info("No numeric columns were found in this dataset.")

            # Findings: only report detected issues
            st.markdown("### Data Quality Findings")
            findings_list = []

            missing_cells = int(df.isna().sum().sum())
            duplicate_rows = int(df.duplicated().sum())

            if missing_cells > 0:
                missing_rate = missing_cells / max(df.size, 1) * 100
                priority = "High" if missing_rate >= 20 else "Medium"

                findings_list.append({
                    "Priority": priority,
                    "Finding": (
                        f"{missing_cells} missing cell(s) detected "
                        f"({missing_rate:.1f}% of all cells)."
                    ),
                    "Recommended Action": (
                        "Review missing values and decide whether to fill, "
                        "correct, or exclude affected records."
                    )
                })

            if duplicate_rows > 0:
                duplicate_rate = duplicate_rows / max(len(df), 1) * 100
                priority = "High" if duplicate_rate >= 20 else "Medium"

                findings_list.append({
                    "Priority": priority,
                    "Finding": (
                        f"{duplicate_rows} duplicate row(s) detected "
                        f"({duplicate_rate:.1f}% of rows)."
                    ),
                    "Recommended Action": (
                        "Inspect duplicate records before removing them; "
                        "some repeated rows may be legitimate."
                    )
                })

            # Flag potential numeric outliers using the IQR rule
            for col in numeric_cols:
                values = df[col].dropna()

                if len(values) >= 8 and values.nunique() > 4:
                    q1 = values.quantile(0.25)
                    q3 = values.quantile(0.75)
                    iqr = q3 - q1

                    if iqr > 0:
                        outlier_count = int(
                            ((values < q1 - 1.5 * iqr) |
                             (values > q3 + 1.5 * iqr)).sum()
                        )

                        if outlier_count > 0:
                            findings_list.append({
                                "Priority": "Medium",
                                "Finding": (
                                    f"{outlier_count} potential outlier(s) "
                                    f"found in '{col}' using the IQR rule."
                                ),
                                "Recommended Action": (
                                    "Inspect these values in context. "
                                    "Outliers are not automatically errors."
                                )
                            })

                        # Analyse categorical columns for useful business insights
            st.markdown("### Category Analysis")

            categorical_cols = df.select_dtypes(
                include=["object", "category", "string"]
            ).columns

            for col in categorical_cols:
                unique_count = df[col].nunique(dropna=True)

                if 2 <= unique_count <= 30:
                    category_summary = (
                        df.groupby(col, dropna=False)
                        .size()
                        .reset_index(name="Record Count")
                        .sort_values("Record Count", ascending=False)
                    )

                    st.write(f"Record distribution by **{col}**")
                    st.dataframe(
                        category_summary.head(10),
                        use_container_width=True,
                        hide_index=True
                    )

                        # Compare categories by sales or revenue
            st.markdown("### Sales and Revenue by Category")

            value_aliases = [
                "revenue", "sales", "total_sales",
                "sales_amount", "order_value", "amount"
            ]

            value_lookup = {
                str(col).strip().lower().replace(" ", "_"): col
                for col in df.columns
            }

            value_col = next(
                (
                    value_lookup[name]
                    for name in value_aliases
                    if name in value_lookup
                    and pd.api.types.is_numeric_dtype(df[value_lookup[name]])
                ),
                None
            )

            if value_col is not None:
                for col in categorical_cols:
                    if 2 <= df[col].nunique(dropna=True) <= 30:
                        value_summary = (
                            df.groupby(col, dropna=False)[value_col]
                            .sum()
                            .sort_values(ascending=False)
                            .head(10)
                            .reset_index()
                        )

                        st.write(
                            f"**{value_col} by {col}** "
                            "(highest values first)"
                        )
                        st.dataframe(
                            value_summary,
                            use_container_width=True,
                            hide_index=True
                        )
            else:
                st.info(
                    "No recognised numeric sales or revenue column was "
                    "found. Category counts are still available above."
                )


            
            if findings_list:
                findings_df = pd.DataFrame(findings_list)

                st.dataframe(
                    findings_df,
                    use_container_width=True,
                    hide_index=True
                )
            else:
                findings_df = pd.DataFrame(
                    columns=["Priority", "Finding", "Recommended Action"]
                )

                st.success(
                    "No missing cells, duplicate rows, or qualifying "
                    "numeric outliers were detected."
                )

            st.download_button(
                label="Download Data Quality Findings (CSV)",
                data=findings_df.to_csv(index=False),
                file_name="universal_business_findings.csv",
                mime="text/csv"
            )

            st.stop()

        if all(col in df.columns for col in REQUIRED_COLUMNS):
            findings, data_issues = detect_overdue_orders(df)

            for issue in data_issues:
                st.warning(issue)
        else:
            findings = pd.DataFrame()
            data_issues = []
            
        large_orders = pd.DataFrame()

        if len(findings.columns) == 0:
            st.info(
                "This CSV does not contain enough recognised order-related "
                "columns for overdue-order analysis. Generic dataset analysis "
                "is available above."
            )

        else:
            total_overdue = len(findings)
            
            sql_overdue_orders = get_overdue_orders()
            st.write("Overdue orders retrieved using SQL:", len(sql_overdue_orders))

            # SQL Analysis: Order Value by Status
            st.subheader("SQL Analysis: Order Value by Status")

            status_summary = get_order_value_by_status()
            st.dataframe(status_summary, use_container_width=True)

            # SQL Analysis: Highest-Value Pending Orders
            st.subheader("SQL Analysis: Highest-Value Pending Orders")

            high_value_pending = get_high_value_pending_orders()
            st.dataframe(high_value_pending, use_container_width=True)

            # SQL Analysis: Customers with Highest Pending Value
            st.subheader("SQL Analysis: Customers with Highest Pending Value")

            customer_pending_summary = get_pending_value_by_customer()
            st.dataframe(customer_pending_summary, use_container_width=True)

            
            # Business health summary
            total_orders = len(df)

            if total_orders > 0:
                overdue_rate = (total_overdue / total_orders) * 100
            else:
                overdue_rate = 0

            st.subheader("Business Health Summary")

            if total_overdue == 0:
                st.success(
                    "No potentially overdue pending orders were detected. "
                    "Continue monitoring delivery deadlines."
                )
            elif overdue_rate >= 20:
                st.error(
                    f"Attention needed: {total_overdue} of {total_orders} "
                    f"orders ({overdue_rate:.1f}%) are potentially overdue. "
                    "Review delivery delays and contact responsible staff."
                )
            else:
                st.warning(
                    f"{total_overdue} of {total_orders} orders "
                    f"({overdue_rate:.1f}%) are potentially overdue. "
                    "Review the highest-priority orders first."
                )

            overdue_value = findings["order_value"].sum()

            high_count = (findings["priority"] == "High").sum()
            medium_count = (findings["priority"] == "Medium").sum()
            low_count = (findings["priority"] == "Low").sum()

            st.subheader("Analytics Dashboard")

            priority_data = pd.DataFrame({
                "Priority": ["High", "Medium", "Low"],
                "Orders": [
                    int(high_count),
                    int(medium_count),
                    int(low_count)
                ]
            })

            st.markdown("**Overdue Orders by Priority**")
            st.bar_chart(
                priority_data.set_index("Priority")
            )

            c1, c2, c3 = st.columns(3)

            c1.metric("Potentially Overdue Orders", total_overdue)
            c2.metric("Total Order Value", f"₹{overdue_value:,.2f}")
            c3.metric("High-Priority Orders", int(high_count))

            
            st.metric(
                "Overdue Order Value to Review",
                f"₹{overdue_value:,.2f}",
                help="Total recorded value of potentially overdue orders; "
                     "this is not necessarily lost revenue."
            )


            st.write(
                f"**Priority breakdown:** High: {high_count} | "
                f"Medium: {medium_count} | Low: {low_count}"
            )

            if findings.empty:
                st.success(
                    "No potentially overdue pending orders were detected."
                )
            else:
                st.warning(
                    f"{total_overdue} potentially overdue order(s) "
                    "need attention."
                )

                st.dataframe(
                    findings.drop(columns=["priority_rank"]),
                    use_container_width=True,
                    hide_index=True
                )

                
                # Detect high-value pending orders
                st.subheader("4. High-Value Pending Orders")

                large_orders, threshold = detect_large_pending_orders(df)

                if threshold is None:
                    st.info("No valid order values available for analysis.")
                else:
                    st.write(
                        f"High-value threshold: ₹{threshold:,.2f}"
                    )

                    if large_orders.empty:
                        st.success(
                            "No high-value pending orders were detected."
                        )
                    else:
                        st.warning(
                            f"{len(large_orders)} high-value pending "
                            "order(s) may need review."
                        )

                        st.dataframe(
                            large_orders[
                                [
                                    "order_id",
                                    "customer",
                                    "status",
                                    "order_value",
                                    "finding",
                                    "recommended_action"
                                ]
                            ],
                            use_container_width=True,
                            hide_index=True
                        )


                st.subheader("Recommended Actions")

                for _, row in findings.iterrows():
                    st.markdown(
                        f"**{row['priority']} priority — "
                        f"Order {row['order_id']}**"
                    )
                    st.write(
                        f"Customer: {row['customer']} | "
                        f"Days overdue: {row['days_overdue']}"
                    )
                    st.write(row["recommended_action"])


            # Compare the two types of business blind spots
            st.subheader("Findings by Type")

            findings_comparison = pd.DataFrame({
                "Finding Type": [
                    "Overdue Orders",
                    "High-Value Pending Orders"
                ],
                "Count": [
                    len(findings),
                    len(large_orders)
                ]
            })

            st.bar_chart(
                findings_comparison.set_index("Finding Type")
            )



          
              
            # Combine overdue and high-value findings
            overdue_report = findings.copy()
            overdue_report["blind_spot_type"] = "Overdue Order"

            large_orders_report = large_orders.copy()
            large_orders_report["blind_spot_type"] = (
                "High-Value Pending Order"
            )

            combined_report = pd.concat(
                [overdue_report, large_orders_report],
                ignore_index=True,
                sort=False
            )

            combined_report = combined_report.drop(
                columns=["priority_rank"], errors="ignore"
            )

            report_csv = combined_report.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="Download Complete Findings Report (CSV)",
                data=report_csv,
                file_name="business_findings_report.csv",
                mime="text/csv"
            )


    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as e:
        st.error(f"Unable to analyse this CSV file: {e}")
    
    except Exception as e:
        st.error(f"Unexpected analysis error: {e}")


else:
    st.info("Upload a CSV file to begin analysing your business records.")
