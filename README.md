Instamart Customer Intelligence & Support Copilot
A reproducible customer intelligence and support-copilot project covering data cleaning, SQL and pandas analysis, customer segmentation, lapse prediction, privacy-aware ticket triage, and customer-aware support routing.

All monetary values are reported in Indian Rupees (INR).
1. Project Overview
The project is organized into three completed parts, with a further agentic RAG workflow planned as Part D:
- Part A — Data Cleaning, SQL, and Pandas Analysis: Audits and cleans customer, product, and order data; creates a SQLite database; and performs SQL and pandas analysis.
- Part B — Customer Segmentation and Lapse Prediction: Builds RFM customer segments, predicts customer lapse, evaluates classification models, and creates a premium-customer retention list.
- Part C — Customer Support Ticket Triage: Redacts PII, classifies support tickets using zero-shot and few-shot prompts, validates model responses, enforces token budgets, and routes tickets to support teams.
- Part D — Policy RAG and ReAct Support Agent: Planned next stage; implementation and evaluation are not yet documented here.
2. Project Structure
instamart-copilot/
├── data/
│   ├── raw/
│   ├── clean/
│   ├── policies/
│   └── instamart.db
├── outputs/
│   ├── customers_audit.csv
│   ├── orders_audit.csv
│   ├── products_audit.csv
│   ├── city_summary.csv
│   ├── correlation_matrix.csv
│   ├── order_amount_distribution.csv
│   ├── revenue_pivot.csv
│   ├── sql_results.txt
│   ├── customer_segments.csv
│   ├── lapse_cohort.csv
│   ├── lapse_features.csv
│   ├── lapse_model.joblib
│   └── retention_list.csv
├── sql/
│   ├── queries.sql
│   └── analysis_queries.sql
├── src/
│   ├── raw_data_audit.py
│   ├── clean_data.py
│   ├── create_database.py
│   ├── cleaning_investigation.py
│   ├── detailed_audit.py
│   ├── part_a.py
│   ├── run_sql.py
│   ├── pandas_analysis.py
│   ├── validate_cleaning.py
│   ├── customer_segmentation.py
│   └── lapse_prediction.py
├── generate_data.py
├── mock_llm.py
├── requirements.txt
├── .gitignore
└── README.md
3. Environment Setup
Prerequisites
- Python
- Git
- Windows CMD, PowerShell, or a compatible terminal
Run commands from the project root directory.

Create and activate a virtual environment:
python -m venv .venv
.venv\Scripts\activate
Install dependencies:
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
4. Part A — Data Cleaning, SQL, and Pandas Analysis
4.1 Raw Data Audit
Run:
python src/raw_data_audit.py
The audit examines dimensions, data types, missing values, and data-quality issues.
Raw dataset summary
Dataset	Rows	Columns
Customers	1,200	5
Orders	13,084	9
Products	40	4


Important audit findings
Customers
- 61 missing age values.
- 30 missing gender values.
- 24 distinct raw city spellings.
- 10 distinct nonblank raw gender spellings.
- 6 nonmissing ages outside the valid 10–100 range.
Orders
- 119 exact duplicate rows.
- 656 pending-state snapshots.
- 12,309 distinct order IDs.
- 120 order-amount entries that cannot be converted to numeric values, including missing entries.
- 106 negative delivery-time values.
- 2,541 blank delivery-time values.
Products
- 40 product records.
Audit reports are saved in outputs/.
4.2 Data Cleaning
Run:
python src/clean_data.py
Cleaned datasets are saved in data/clean/.
Customer cleaning
- Standardizes city names.
- Normalizes gender values to male, female, or unknown.
- Converts invalid ages outside 10–100 to missing values.
- Imputes missing ages using the median age for the corresponding city.
- Converts signup dates to datetime.
- Checks customer ID uniqueness and missing values.
The cleaned customer dataset contains 1,200 records, six standardized cities, three normalized gender categories, and no missing ages.
Product cleaning
Checks product IDs and basic data integrity. The cleaned dataset contains 40 records.
Order cleaning
- Parses order timestamps.
- Removes 119 exact duplicate rows.
- Retains the latest timestamped record for each order ID.
- Converts order amounts to numeric values.
- Repairs invalid or missing amounts using:
  price_inr × quantity × (1 − discount_pct / 100)
- Replaces negative delivery times with missing values.
- Imputes missing completed-order delivery times using the completed-order median for the product category.
- Leaves cancelled-order delivery times missing.
Final order counts
Measure	Result
Raw order rows	13,084
Exact duplicate rows removed	119
Older order-state records removed	656
Final unique orders	12,309
Completed orders	11,110
Cancelled orders	1,199
Pending orders remaining	0
Missing order amounts after cleaning	0
Completed orders missing delivery time	0
Cancelled orders with missing delivery time	1,199
Completed-order revenue	INR 2,998,668.80


4.3 SQLite Database
Run:
python src/create_database.py
Database location:

data/instamart.db

Tables:
Table	Description
customers	Cleaned customer information
products	Cleaned product catalogue
orders	Cleaned order records


4.4 SQL Analysis
Run:
python src/run_sql.py
The seven SQL analyses cover:
1. High-value customer orders.
2. Revenue by city and product category.
3. Products priced above the catalogue average.
4. Customers without completed orders.
5. Customers with above-average completed-order spend.
6. Customer spend rankings using window functions.
7. Daily revenue and cumulative revenue.
Results are saved in outputs/sql_results.txt.
Key SQL results
- Completed-order revenue: INR 2,998,668.80.
- City-category revenue combinations: 30.
- Products above average catalogue price: 11.
- Customers without completed orders: 25.
- Customers above average completed-order spend: 550.
- Daily revenue records: 183.
- Final cumulative revenue: INR 2,998,668.80.
4.5 Pandas Analysis
Run:
python src/pandas_analysis.py
Outputs:
File	Description
revenue_pivot.csv	Completed-order revenue by city and category
city_summary.csv	Revenue, average order amount, and order count by city
order_amount_distribution.csv	Descriptive statistics and IQR analysis
correlation_matrix.csv	Correlations among numeric order variables


Key findings
- Mean order amount: INR 269.91.
- Median order amount: INR 135.00.
- First quartile: INR 64.80.
- Third quartile: INR 297.00.
- Skewness: approximately 4.61.
- Upper IQR outlier fence: INR 645.30.
- Orders above the upper fence: 897.
- Strongest absolute pairwise correlation: order amount and discount percentage, approximately −0.095.
The correlation is weak and does not establish a causal relationship.
4.6 Part A Validation
Run:
python src/validate_cleaning.py
A successful run ends with:
21 CHECKPOINTS PASSED
ALL CHECKPOINTS PASSED
5. Part B — Customer Segmentation and Lapse Prediction
5.1 RFM Customer Segmentation
Run:
python src/customer_segmentation.py
RFM features are calculated using completed orders as of 2025-10-01.
- Recency: Whole days since the customer's most recent completed order.
- Frequency: Number of distinct completed orders.
- Monetary: Total completed-order spend.
RFM summary
Measure	Result
Customers	1,175
Median recency	19 days
Minimum recency	0 days
Maximum recency	180 days
Mean frequency	9.46 orders
Maximum frequency	33 orders
Mean monetary value	INR 2,552.06
Maximum monetary value	INR 14,766.55


5.2 K-Means Clustering
RFM features are standardized using StandardScaler.

K-Means is evaluated for K values from 2 to 8 using:
- n_init=10
- random_state=42
- Silhouette score
- Inertia
Clustering evaluation
K	Inertia	Silhouette
2	1820.8	0.465
3	1268.2	0.445
4	743.1	0.526
5	617.4	0.481
6	503.2	0.482
7	408.5	0.416
8	366.5	0.412


K=4 was selected because it produced the highest silhouette score and a clear improvement in inertia.
Final customer segments
Segment	Customers
Occasional Customers	436
Loyal Customers	419
At-Risk Customers	182
Premium Customers	138
Total	1,175


Premium Customers have the highest average monetary value.
PCA
Principal Component Analysis was applied to the standardized RFM data.
Component	Explained variance ratio
PC1	0.634
PC2	0.218
Total	0.852


The first two principal components explain 85.2% of the variance.

Output:

outputs/customer_segments.csv

Columns:

customer_id, recency, frequency, monetary, segment_id, segment_name, is_premium
5.3 Lapse Cohort Definition
The lapse prediction task uses:
- Feature cutoff: 2025-09-01
- Label window: 2025-09-01 through 2025-09-30
- Eligible customers: customers with at least one completed order before the cutoff.
- Lapsed label: 1 if the customer made no completed order during the label window; otherwise 0.
Cohort results
Measure	Result
Eligible customers	1,156
Lapsed customers	443
Active customers	713
Lapse percentage	38.32%


Output:

outputs/lapse_cohort.csv
5.4 Historical Feature Engineering
All model features are calculated using information available before 2025-09-01.

The 11 features are:
Feature	Description
recency	Days since last completed order before cutoff
frequency	Distinct completed orders before cutoff
monetary	Total completed-order spend before cutoff
avg_discount_pct	Average discount on completed orders
cancellation_rate	Cancelled orders divided by all final-status orders
avg_delivery_minutes	Average delivery time for completed orders
favourite_category	Most frequently ordered completed-order category
city	Customer city
age	Customer age
gender	Customer gender
tenure_days	Customer tenure based on signup date and cutoff


The feature dataset contains 1,156 rows and 11 model features, with no missing feature values.

Output:

outputs/lapse_features.csv
5.5 Train/Test Split and Preprocessing
The data is split using:
- test_size=0.2
- random_state=42
- Stratification by the lapse label
Dataset	Rows
Training	924
Testing	232


Training class distribution:
Class	Customers
Active	570
Lapsed	354


Testing class distribution:
Class	Customers
Active	143
Lapsed	89


Preprocessing is implemented inside model pipelines:
- Numeric features: median imputation and standard scaling.
- Categorical features: most-frequent imputation and OneHotEncoder(drop="first", handle_unknown="ignore").
- Preprocessing is fitted on training data, not the held-out test data.
The baseline model predicts every customer as active:
- Accuracy: 61.64%.
- Lapsed-class F1: 0.00.
This demonstrates why accuracy alone is insufficient for the imbalanced lapse-prediction task.
5.6 Model Training and Hyperparameter Tuning
Two classifiers are evaluated.
Logistic Regression
- max_iter=1000
- C values: [0.01, 0.1, 1, 10, 100]
- 5-fold cross-validation
- Scoring: F1
Best parameters:

C = 0.1

Best cross-validation F1:

0.6392
Random Forest
- n_estimators=100
- random_state=42
- Maximum depth: [3, 5, 8]
- Minimum samples per leaf: [5, 10, 20]
- 5-fold cross-validation
- Scoring: F1
Best parameters:
- max_depth=3
- min_samples_leaf=5
Best cross-validation F1:

0.6748
Test-set evaluation
Metric	Logistic Regression	Random Forest
Precision	0.6545	0.6804
Recall	0.8090	0.7416
F1-score	0.7236	0.7097


Confusion matrices, with rows representing actual classes [active, lapsed] and columns representing predicted classes [active, lapsed]:

Logistic Regression
[[105  38]
 [ 17  72]]
Random Forest
[[112  31]
 [ 23  66]]
Both models exceed the target test F1 of 0.55.
Selected model
The original Logistic Regression model is selected as the primary model because it achieves a higher held-out test F1-score and higher recall than the Random Forest.

For lapse prevention, recall is important because failing to identify a customer who is about to lapse can mean missing an opportunity to retain them. Precision also matters because unnecessary retention outreach has a cost.
5.7 Minority-Class Oversampling
The training data is oversampled by duplicating minority-class lapsed customers with replacement.
- random_state=42
- Original training classes: 570 active and 354 lapsed.
- Balanced training classes: 570 active and 570 lapsed.
- The test set remains unchanged.
Comparison
Metric	Original Logistic Regression	Oversampled Logistic Regression
Precision	0.6545	0.5915
Recall	0.8090	0.9438
F1-score	0.7236	0.7273


Oversampling substantially improves recall but reduces precision. The original Logistic Regression remains the selected primary model; the oversampled version is retained as a comparison experiment.
5.8 Model Interpretation
Top five Random Forest features
Feature	Importance
Frequency	0.352171
Monetary	0.288692
Recency	0.114974
Cancellation rate	0.053057
Average discount percentage	0.040657


Frequency, monetary value, and recency are the three most important features in the fitted Random Forest.
Logistic Regression coefficients
Strongest positive coefficients:
Feature	Coefficient
Age	+0.087905
Average discount percentage	+0.066551
Favourite category: Personal Care	+0.056385


Strongest negative coefficients:
Feature	Coefficient
Frequency	−1.349948
Favourite category: Electronics	−0.329451
City: Delhi	−0.321887


Positive coefficients are associated with higher predicted lapse likelihood, while negative coefficients are associated with lower predicted lapse likelihood.

These results describe model associations and should not be interpreted as causal effects.
5.9 Model Persistence
The selected original Logistic Regression pipeline is saved using joblib:

outputs/lapse_model.joblib

The saved model is reloaded and its predictions are compared with the original model's predictions on the test set.

Validation result:
Predictions identical: True
Model save/load validation passed.
The saved pipeline includes its preprocessing steps, so new data must be supplied with the same input feature columns.
5.10 Premium-Customer Retention List
The saved model generates lapse probabilities for premium customers in the held-out test set.

The top 10 customers are ranked by predicted lapse probability.

Output:

outputs/retention_list.csv

Columns:
- customer_id
- lapse_probability
- actually_lapsed
Retention-list results
Measure	Result
Premium customers in test set	29
Customers selected	10
Actually lapsed among top 10	1
Highest predicted lapse probability	0.7170


This list is an illustrative prioritization output, not a separate model evaluation.
6. Part C — Customer Support Ticket Triage
6.1 Objective and Dataset
Part C implements a privacy-aware customer support ticket triage pipeline using the supplied local mock LLM.

Input file: data/raw/tickets.csv
- Total tickets: 164
- Empty tickets: 4
- Extremely long tickets: 4
- Eligible tickets for classification: 156
- Estimated total input tokens: 734
The pipeline classifies tickets into billing, delivery, technical, or fraud, validates responses, applies token-budget controls, and routes tickets to the appropriate team.
6.2 PII Detection and Redaction
Before ticket text is sent to the mock LLM, the pipeline replaces detected personally identifiable information (PII).
PII type	Replacement token	Replacements
Email addresses	[EMAIL]	55
Phone numbers	[PHONE]	91
Order IDs	[ORDER_ID]	132
Total		278


The redaction process is idempotent: running it again on already-redacted text produces zero additional replacements. Only the redacted ticket text is sent as the user message.
6.3 Input Guardrails
- Empty or whitespace-only tickets receive status skipped_empty.
- Tickets exceeding 400 estimated tokens receive status flagged_long.
- These tickets are not sent to the model and are routed for human review.
6.4 Prompt Strategies
Two prompt strategies are compared:

Zero-shot prompting
- Uses classification instructions without labelled examples.
- Requests one of four categories: billing, delivery, technical, or fraud.
- Requires JSON containing category and reason.
Few-shot prompting
- Uses the same classification instructions.
- Includes an EXAMPLES: section with at least two labelled examples, including fraud.
- Requires the same JSON response format.
6.5 Retry Logic and Response Validation
Transient model errors are handled with exponential backoff:
- Maximum retries: 3 per ticket.
- Wait formula: 0.05 * 2**n * random.uniform(0.9, 1.15).
- Retry number and wait duration are logged.
- The mock LLM is reset immediately before each independent run.
Responses are assigned one of these statuses:
1. classified_json — valid JSON containing an allowed category.
2. classified_keyword — invalid JSON, but exactly one allowed category word is detected using the specified word-matching rule.
3. flagged_invalid_output — response cannot be accepted through either validation method.
6.6 Zero-shot and Few-shot Evaluation
Accuracy is calculated over the 147 classified tickets; empty and long tickets are excluded.
Metric	Zero-shot	Few-shot
Valid JSON responses	135	135
Keyword-based classifications	12	12
Invalid outputs	9	9
Empty tickets skipped	4	4
Long tickets flagged	4	4
Classified tickets	147	147
Correct predictions	126	147
Accuracy	85.71%	100.00%
Total successful-response tokens	15,172	23,752
Tokens for classified tickets	14,276	22,361
Average tokens per classified ticket	97.12	152.12


The zero-shot confusion matrix, with rows and columns ordered as [billing, delivery, technical, fraud], was:
[[38,  0,  0,  0],
 [ 0, 36,  0,  0],
 [10,  0, 29,  0],
 [11,  0,  0, 23]]
The zero-shot run incorrectly classified 11 fraud tickets and 10 technical tickets as billing. The few-shot run correctly classified all 147 evaluated tickets.

Trade-off: Few-shot prompting achieved higher accuracy on this supplied evaluation set but used more tokens. Zero-shot prompting was more token-efficient but made more classification errors. The observed few-shot accuracy does not guarantee performance on unseen tickets.
6.7 Token-Budget Demonstration
A separate zero-shot run used TOKEN_BUDGET=6000.
Metric	Result
Model responses	62
JSON classifications	55
Keyword classifications	4
Invalid outputs	3
Empty tickets skipped	4
Long tickets flagged	4
Budget-exhausted tickets	94
Total recorded token usage	6,025


The recorded usage slightly exceeded the 6,000-token budget because the budget is checked before a model call. The final permitted call can therefore take the running total above the limit. Tickets not processed after budget exhaustion are marked budget_exhausted and routed to human review.
6.8 Final Ticket Routing
The final few-shot run used TOKEN_BUDGET=100000 and produced 164 output rows.

Routing rules:
- skipped_empty, flagged_long, flagged_invalid_output, and budget_exhausted → human_review, NORMAL priority.
- Fraud category → security_team, HIGH priority.
- Premium customer → premium_desk, HIGH priority.
- Other classified tickets → support_queue, NORMAL priority.
- Missing customer segment information is treated as non-premium.
Premium customer information is read from outputs/customer_segments.csv.
Route	Tickets
support_queue	102
security_team	34
human_review	17
premium_desk	11
Total	164


The final outputs/triage_results.csv contains these columns:

ticket_id, customer_id, status, category, segment_name, priority, route, tokens_used
6.9 Part C Output Files
File	Description
outputs/triage_zero_shot.csv	Zero-shot classification results
outputs/triage_few_shot.csv	Few-shot classification results
outputs/triage_prompt_comparison.csv	Prompt-strategy comparison
outputs/triage_budget_demo.csv	Limited-token-budget demonstration
outputs/triage_results.csv	Final classification and routing results


6.10 Reproducing Part C
Run from the project root after completing Parts A and B:
python src/ticket_triage.py
The pipeline uses the local mock LLM implementation. No external LLM API is required.
6.11 Limitations
- The evaluation uses a limited dataset of 164 tickets.
- The mock LLM does not represent the full variability of a production LLM.
- Few-shot accuracy is measured on the supplied evaluation dataset and does not guarantee the same accuracy on unseen tickets.
- Token-budget enforcement occurs before each model call, so a small overrun is possible.
- Automated classifications and routing should be monitored before production use.
- Tickets that cannot be confidently processed are routed to human review.
7. Reproducing the Project
Activate the virtual environment and install dependencies:
.venv\Scripts\activate
python -m pip install -r requirements.txt
Run Part A:
python src/raw_data_audit.py
python src/clean_data.py
python src/create_database.py
python src/run_sql.py
python src/pandas_analysis.py
python src/validate_cleaning.py
Run Part B:
python src/customer_segmentation.py
python src/lapse_prediction.py
The Part B script performs cohort creation, feature engineering, splitting, preprocessing, model tuning, evaluation, oversampling, interpretation, model persistence, and retention-list generation.

Run Part C:
python src/ticket_triage.py
This generates the zero-shot, few-shot, budget-demo, comparison, and final ticket-routing outputs.

Important: The supplied generate_data.py and mock_llm.py files must remain unchanged. Do not run generate_data.py during normal reproduction unless you intentionally want to generate a fresh raw dataset.
8. Limitations and Leakage Safeguards
1. Lapse prediction features are restricted to information available before 2025-09-01. The September label window is used only to construct the target.
2. The test set is held out from model fitting and preprocessing. Cross-validation is used for hyperparameter selection.
3. Oversampling is performed on the training data only. The original test set is preserved for comparison.
4. Customer segment labels are not used as lapse-model features.
5. The premium flag used for the retention list is derived from the full RFM window ending 2025-10-01. This includes the September label period. Consequently, the premium retention list is illustrative and should not be treated as a leakage-free prospective deployment evaluation.
6. The dataset is a limited historical sample. Model performance may change on future customers and different time periods.
7. Feature importance and coefficients indicate associations, not causal relationships.
8. Retention outreach decisions should consider campaign cost, customer experience, and the possibility of false-positive predictions.
9. Version Control and Project Hygiene
- Run commands from the project root.
- Keep the virtual environment in .venv/.
- Do not commit .env files, virtual-environment files, or Python cache files.
- Keep requirements.txt updated when dependencies change.
- Use Git commits to record meaningful project milestones.
- Report monetary values in INR.
10. Final Project Summary
The Instamart Customer Intelligence & Support Copilot project implements a reproducible data and machine-learning workflow.

Part A covers raw-data auditing, data cleaning, SQLite database creation, SQL analysis, pandas analysis, and automated validation.

Part B covers RFM analysis, K-Means customer segmentation, PCA, historical lapse-feature engineering, Logistic Regression and Random Forest tuning, minority-class oversampling, model interpretation, model persistence, and premium-customer retention prioritization.

Part C covers PII redaction, zero-shot and few-shot ticket classification, retry handling, response validation, token-budget enforcement, and customer-aware ticket routing.

Part D is the planned next stage for policy retrieval-augmented generation (RAG) and a tool-using ReAct support agent; it is not yet implemented or evaluated in this README.

The completed Parts A–C provide a foundation for further customer intelligence, lapse prevention, and support-copilot development.