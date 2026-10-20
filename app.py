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
    "order_id": ["order_id", "orderid", "order_number", "order_no"],
    "customer": ["customer", "customer_name", "client", "buyer"],
    "order_date": ["order_date", "date", "purchase_date"],
    "expected_delivery_date": [
        "expected_delivery_date",
        "delivery_due",
        "due_date",
        "delivery_date",
    ],
    "status": ["status", "order_status", "delivery_status"],
    "order_value": [
        "order_value",
        "sales_amount",
        "revenue",
        "total_sales",
        "amount",
    ],
    "product": ["product", "product_name", "item", "item_name"],
    "region": ["region", "location", "area", "territory"],
    "quantity": ["quantity", "qty", "units_sold", "units"],
    "price": ["price", "unit_price", "selling_price"],
    "marketing_spend": ["marketing_spend", "ad_spend", "advertising_cost"],
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
        for column in df.columns:
            if column in aliases and standard_name not in used_columns:
                rename_map[column] = standard_name
                used_columns.add(standard_name)
                break

    return df.rename(columns=rename_map)

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

        save_orders(df)
        st.success(f"SQLite database contains {get_order_count()} orders.")

    

        st.subheader("3. Business Blind Spots")

        findings, data_issues = detect_overdue_orders(df)

        for issue in data_issues:
            st.warning(issue)

        if len(findings.columns) == 0:
            st.error(
                "Analysis could not run. Check that your CSV contains "
                "all required columns listed below."
            )
            st.write(REQUIRED_COLUMNS)

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
