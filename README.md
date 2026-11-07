# Overview

This project implements an end-to-end Instamart customer analytics and support copilot across four parts:

- **Part A – Data cleaning and SQL analysis:** audit and clean customer, order, and product data; create a SQLite database; and perform SQL and pandas analysis.
- **Part B – Customer analytics and lapse prediction:** build RFM features, segment customers, and train models to predict customer lapse.
- **Part C – Support ticket triage:** redact personally identifiable information (PII), apply input guardrails, classify support tickets, and route them to appropriate teams.
- **Part D – Policy RAG and tool-using agent:** retrieve policy information and implement a bounded tool-using agent for order lookup, refund decisions, escalation, and checkpoint recovery.

The project uses Python, pandas, SQLite, scikit-learn, TF-IDF retrieval, and the supplied mock language-model interface.

The supplied `generate_data.py` and `mock_llm.py` are included at the repository root and are used without modification.

## Repository structure

```text
instamart-copilot/
├── data/
│   ├── raw/
│   ├── clean/
│   ├── policies/
│   └── instamart.db
├── outputs/
├── sql/
│   ├── queries.sql
│   └── analysis_queries.sql
├── src/
│   ├── clean_data.py
│   ├── raw_data_audit.py
│   ├── validate_cleaning.py
│   ├── create_database.py
│   ├── run_sql.py
│   ├── pandas_analysis.py
│   ├── customer_segmentation.py
│   ├── lapse_prediction.py
│   ├── ticket_triage.py
│   ├── rag_policy.py
│   ├── rag_overlap_comparison.py
│   ├── agent_tools.py
│   ├── agent.py
│   ├── run_agent_evaluation.py
│   ├── run_agent_limit_demos.py
│   └── run_checkpoint_demo.py
├── state/
├── generate_data.py
├── mock_llm.py
├── requirements.txt
├── .gitignore
└── README.md
```

Generated CSV files, evaluation results, model files, logs, and checkpoints are stored in `data/`, `outputs/`, and `state/`.

## Reproduce

The following commands are written for Windows Command Prompt. Run them from the repository root, in the order shown.

### 1. Clone the repository and set up Python

Replace the repository URL below with the public GitHub repository URL.

```cmd
git clone https://github.com/hociga2911-wq/instamart-copilot.git
cd instamart-copilot

python -m venv .venv
.venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 2. Generate the raw datasets

Run the supplied data generator:

```cmd
python generate_data.py
```

The generator creates the raw customer, product, order, support-ticket, and Part D agent-scenario datasets. It also provides the policy and evaluation input files used by the project.

The Part D scenario file is generated at:

```text
data/raw/agent_scenarios.csv
```

No separate scenario-generation command is required.

### 3. Run the raw data audit

```cmd
python src/raw_data_audit.py
```

This reports the raw dataset shapes, column data types, missing values, and additional customer and order data-quality checks. Audit summaries are saved under `outputs/`.

### 4. Run Part A cleaning and validation

```cmd
python src/clean_data.py
python src/validate_cleaning.py
```

The cleaning script creates the cleaned datasets under `data/clean/`. The validation script checks the cleaned customer, product, and order data.

### 5. Create the SQLite database

```cmd
python src/create_database.py
```

The database is created at:

```text
data/instamart.db
```

### 6. Run SQL and pandas analysis

```cmd
python src/run_sql.py
python src/pandas_analysis.py
```

The SQL runner executes the seven queries in `sql/queries.sql`. The pandas analysis creates summary and distribution outputs under `outputs/`.

The additional SQL analysis file is:

```text
sql/analysis_queries.sql
```

### 7. Run Part B customer segmentation and lapse prediction

```cmd
python src/customer_segmentation.py
python src/lapse_prediction.py
```

These scripts create the RFM table, customer segments, lapse cohort and features, fitted model, and retention illustration.

### 8. Run Part C ticket triage

```cmd
python src/ticket_triage.py
```

This script performs PII redaction, input guardrails, zero-shot and few-shot classification, token-budget evaluation, and final ticket routing.

### 9. Prepare Part D run logs for a clean demonstration

The Part D agent writes append-only JSONL logs and checkpoint files. If reproducing the demonstrations in an existing checkout, back up any existing logs and checkpoints first. The following commands remove previous generated agent logs and state files so the next run starts cleanly:

```cmd
if exist outputs\agent_runs.jsonl del outputs\agent_runs.jsonl
if exist outputs\refund_ledger.jsonl del outputs\refund_ledger.jsonl
if exist outputs\checkpoint_demo_ledger.jsonl del outputs\checkpoint_demo_ledger.jsonl
if exist state\*.json del state\*.json
```

These commands remove only the listed generated agent logs and JSON checkpoint files. Do not run them if you need to preserve earlier execution records.

### 10. Run Part D RAG and agent evaluations

```cmd
python src/rag_policy.py
python src/rag_overlap_comparison.py
python src/run_agent_evaluation.py
python src/run_agent_limit_demos.py
python src/run_checkpoint_demo.py
```

The scripts generate RAG evaluation results, agent scenario results, execution logs, refund ledgers, and checkpoint demonstrations.

The checkpoint demonstration uses the run ID `checkpoint_S1_demo`. It simulates an interruption and resumes from the saved state.

### 11. Verify the generated outputs

After the pipeline completes, inspect the generated files under:

```text
data/clean/
data/instamart.db
outputs/
state/
```

Important outputs include:

```text
outputs/customers_audit.csv
outputs/orders_audit.csv
outputs/products_audit.csv
outputs/sql_results.txt
outputs/revenue_pivot.csv
outputs/city_summary.csv
outputs/order_amount_distribution.csv
outputs/correlation_matrix.csv
outputs/customer_segments.csv
outputs/lapse_cohort.csv
outputs/lapse_features.csv
outputs/lapse_model.joblib
outputs/retention_list.csv
outputs/triage_results.csv
outputs/triage_zero_shot.csv
outputs/triage_few_shot.csv
outputs/triage_budget_demo.csv
outputs/rag_evaluation.csv
outputs/rag_evaluation_overlap0.csv
outputs/agent_evaluation.csv
outputs/agent_runs.jsonl
outputs/refund_ledger.jsonl
outputs/checkpoint_demo_ledger.jsonl
state/checkpoint_S1_demo.json
```

The agent evaluation and checkpoint scripts can append entries to JSONL logs. For a clean repeat of Part D, use the log-reset commands in Step 9 before running the Part D scripts.

## Part A

### Raw data audit

The supplied raw datasets contain:

| Dataset | Rows | Columns |
|---|---:|---:|
| Customers | 1,200 | 5 |
| Orders | 13,084 | 9 |
| Products | 40 | 4 |

The following table records the actual raw column types and missing-value counts reported by `src/raw_data_audit.py`.

#### Customers

| Column | Raw dtype | Missing rows | Missing % |
|---|---|---:|---:|
| customer_id | str | 0 | 0.00% |
| city | str | 0 | 0.00% |
| signup_date | str | 0 | 0.00% |
| age | float64 | 61 | 5.08% |
| gender | str | 30 | 2.50% |

#### Orders

| Column | Raw dtype | Missing rows | Missing % |
|---|---|---:|---:|
| order_id | str | 0 | 0.00% |
| customer_id | str | 0 | 0.00% |
| product_id | str | 0 | 0.00% |
| quantity | int64 | 0 | 0.00% |
| order_ts | str | 0 | 0.00% |
| status | str | 0 | 0.00% |
| discount_pct | int64 | 0 | 0.00% |
| order_amount | str | 53 | 0.41% |
| delivery_minutes | float64 | 2,541 | 19.42% |

#### Products

| Column | Raw dtype | Missing rows | Missing % |
|---|---|---:|---:|
| product_id | str | 0 | 0.00% |
| product_name | str | 0 | 0.00% |
| category | str | 0 | 0.00% |
| price_inr | int64 | 0 | 0.00% |

### Additional raw data-quality checks

#### Customer checks

| Check | Result |
|---|---:|
| Blank ages | 61 |
| Ages outside 10–100, including blanks | 67 |
| Nonblank invalid ages outside 10–100 | 6 |
| Distinct raw city spellings | 24 |
| Distinct nonblank raw gender spellings | 10 |
| Blank genders | 30 |

The 67 ages outside the valid range include the 61 missing ages. Therefore, six nonblank age values are outside the 10–100 range.

#### Order checks

| Check | Result |
|---|---:|
| Exact duplicate rows | 119 |
| Pending rows | 656 |
| Distinct order IDs | 12,309 |
| Order amounts not convertible to numeric, including missing values | 120 |
| Negative delivery times | 106 |
| Blank delivery times | 2,541 |

The 120 non-convertible order amounts include the 53 missing values shown in the column-level audit.

### Cleaning decisions

The cleaning pipeline applies the following rules:

- Standardizes inconsistent city names and spellings.
- Normalizes gender values to `male`, `female`, and `unknown`.
- Converts invalid ages to missing values and imputes missing ages using the median age for the corresponding city.
- Converts signup dates and order timestamps to date/time representations.
- Removes 119 exact duplicate order rows.
- Keeps the latest timestamped record for each order when multiple status snapshots exist.
- Converts order amounts to numeric values.
- Repairs missing or non-numeric order amounts using product price, quantity, and discount percentage:

  `price_inr × quantity × (1 - discount_pct / 100)`

- Treats negative delivery times as invalid and sets them to missing.
- Imputes missing delivery times for completed orders using the median delivery time for the relevant category.
- Leaves delivery times for cancelled orders missing.
- Excludes older pending snapshots when constructing the final order-level dataset.

### Cleaning results

| Measure | Result |
|---|---:|
| Raw order rows | 13,084 |
| Duplicate rows removed | 119 |
| Older status records removed | 656 |
| Final unique orders | 12,309 |
| Completed orders | 11,110 |
| Cancelled orders | 1,199 |
| Pending orders in final data | 0 |
| Missing final order amounts | 0 |
| Completed orders missing delivery time | 0 |
| Cancelled orders with missing delivery time | 1,199 |

The final cleaned order dataset contains 12,309 unique orders. Total completed-order revenue is **INR 2,998,668.80**.

The cleaning validation script passed all **21 validation checkpoints** in the recorded run.

### SQLite and SQL analysis

The cleaned data is stored in:

```text
data/instamart.db
```

The SQL files are:

```text
sql/queries.sql
sql/analysis_queries.sql
```

The seven queries executed by `src/run_sql.py` cover:

- High-value orders.
- Revenue by city and product category.
- Products priced above the average product price.
- Customers with no completed orders.
- Customers whose spending is above average.
- Ranking and window-function analyses.
- Daily revenue and cumulative revenue.

Key query results:

| Analysis | Result |
|---|---:|
| City-category combinations | 30 |
| Products above average price | 11 |
| Customers with no completed orders | 25 |
| Customers above average spend | 550 |
| Daily revenue records | 183 |
| Final cumulative revenue | INR 2,998,668.80 |

### Pandas analysis

The cleaned completed-order amounts have the following descriptive statistics:

| Statistic | Value |
|---|---:|
| Mean order amount | INR 269.91 |
| Median order amount | INR 135.00 |
| First quartile | INR 64.80 |
| Third quartile | INR 297.00 |
| Skewness | 4.61 |
| Upper IQR outlier fence | INR 645.30 |
| Values above the upper fence | 897 |

The distribution is strongly right-skewed. The strongest absolute correlation among the examined numeric variables was between order amount and discount percentage, at approximately **-0.095**. This is a weak association and should not be interpreted as evidence of causation.

## Part B

### RFM feature engineering

Customer-level Recency, Frequency, and Monetary (RFM) features were constructed from the cleaned order data.

The resulting RFM dataset contains **1,175 customers**.

| Measure | Result |
|---|---:|
| Median recency | 19 days |
| Minimum recency | 0 days |
| Maximum recency | 180 days |
| Mean frequency | 9.46 orders |
| Maximum frequency | 33 orders |
| Mean monetary value | INR 2,552.06 |
| Maximum monetary value | INR 14,766.55 |

### Customer segmentation

K-means clustering was evaluated for values of K from 2 through 8.

| K | Inertia | Silhouette score |
|---:|---:|---:|
| 2 | 1,820.8 | 0.465 |
| 3 | 1,268.2 | 0.445 |
| 4 | 743.1 | 0.526 |
| 5 | 617.4 | 0.481 |
| 6 | 503.2 | 0.482 |
| 7 | 408.5 | 0.416 |
| 8 | 366.5 | 0.412 |

K=4 was selected based on the strongest silhouette score among the tested values.

The resulting customer segments are:

| Segment | Customers |
|---|---:|
| Occasional | 436 |
| Loyal | 419 |
| At-Risk | 182 |
| Premium | 138 |
| **Total** | **1,175** |

PCA explained-variance ratios:

| Component | Explained variance |
|---|---:|
| PC1 | 0.634 |
| PC2 | 0.218 |
| **Combined** | **0.852** |

The first two principal components explain **85.2%** of the variance.

### Lapse prediction

The lapse prediction task uses a temporal cohort definition:

- Feature cutoff: **2025-09-01**.
- Label window: **2025-09-01 through 2025-09-30**.
- Eligible customers: **1,156**.
- Lapsed customers: **443**.
- Active customers: **713**.
- Lapse rate: **38.32%**.

The model uses 11 features constructed from information available before the feature cutoff:

1. Recency.
2. Frequency.
3. Monetary value.
4. Average discount percentage.
5. Cancellation rate.
6. Average delivery time.
7. Favourite category.
8. City.
9. Age.
10. Gender.
11. Customer tenure in days.

The feature dataset contains 1,156 rows and has no missing values.

The train/test split contains:

| Split | Rows | Active | Lapsed |
|---|---:|---:|---:|
| Training | 924 | 570 | 354 |
| Testing | 232 | 143 | 89 |

**Leakage controls:**

- Encoders, scalers, and other preprocessing steps are fitted using training data only.
- Resampling is applied to the training data only. The test set remains unchanged.
- Model features use information available before 2025-09-01; September label-window information is not used as a model feature.
- Customer segment labels from the separate Part B segmentation analysis are not used as lapse-model features.

### Model comparison

The baseline predicts every customer as active.

| Metric | Baseline |
|---|---:|
| Accuracy | 61.64% |
| Lapse F1 | 0.0000 |

Two models were evaluated: Logistic Regression and Random Forest.

Hyperparameter selection used five-fold cross-validation with lapse-class F1 as the selection metric.

| Model | Search | Best parameters | Best CV F1 |
|---|---|---|---:|
| Logistic Regression | C = 0.01, 0.1, 1, 10, 100 | C = 0.1 | 0.6392 |
| Random Forest | Depth = 3, 5, 8; leaf size = 5, 10, 20 | Depth = 3; leaf size = 5 | 0.6748 |

Test-set performance:

| Model | Precision | Recall | F1 |
|---|---:|---:|---:|
| Logistic Regression | 0.6545 | 0.8090 | 0.7236 |
| Random Forest | 0.6804 | 0.7416 | 0.7097 |

Confusion matrices, with rows representing actual classes and columns representing predicted classes in the order active, lapsed:

**Logistic Regression**

```text
[[105, 38],
 [ 17, 72]]
```

**Random Forest**

```text
[[112, 31],
 [ 23, 66]]
```

Logistic Regression was selected for its higher test-set lapse F1 and recall.

### Training-only oversampling

An additional Logistic Regression experiment oversampled the training data to balance the two classes.

| Training class | Before | After |
|---|---:|---:|
| Active | 570 | 570 |
| Lapsed | 354 | 570 |

The test set remained unchanged.

The oversampled Logistic Regression model achieved:

| Precision | Recall | F1 |
|---:|---:|---:|
| 0.5915 | 0.9438 | 0.7273 |

This experiment increased lapse recall, with a corresponding reduction in precision.

### Feature interpretation

The Random Forest's leading feature importances were:

| Feature | Importance |
|---|---:|
| Frequency | 0.352171 |
| Monetary | 0.288692 |
| Recency | 0.114974 |
| Cancellation rate | 0.053057 |
| Average discount percentage | 0.040657 |

The largest positive Logistic Regression coefficients included age (0.087905), average discount percentage (0.066551), and Personal Care category (0.056385). The largest negative coefficients included frequency (-1.349948), Electronics category (-0.329451), and Delhi city (-0.321887).

These coefficients describe the fitted model and do not establish causal relationships.

### Model persistence and retention illustration

The saved model was reloaded and produced identical predictions to the original fitted model.

A retention-prioritization illustration selected 10 customers from the Premium test cohort of 29 customers. One of those 10 customers was actually labelled as lapsed. The maximum predicted lapse probability in the selected group was 0.7170.

**Temporal limitation:** the Premium flag used for this post-hoc illustration is based on the full RFM window ending 2025-10-01, which overlaps the September label window. It is therefore an illustrative analysis, not a leakage-free prospective retention evaluation.

## Part C

### Ticket preprocessing and PII redaction

The ticket pipeline processes 164 support tickets.

| Measure | Count |
|---|---:|
| Total tickets | 164 |
| Empty tickets | 4 |
| Long tickets | 4 |
| Eligible tickets for classification | 156 |
| Estimated input tokens | 734 |

PII redaction replaces detected email addresses, phone numbers, and order IDs with placeholders.

| PII type | Replacements |
|---|---:|
| Email addresses | 55 |
| Phone numbers | 91 |
| Order IDs | 132 |
| **Total** | **278** |

Redaction is idempotent: applying it again does not repeatedly alter already-redacted values.

### Guardrails

The pipeline applies input checks before classification:

- Empty tickets are skipped.
- Tickets exceeding the configured 400-token length threshold are flagged as long.
- Eligible tickets are passed to the classification workflow.

The empty and long-ticket guardrails account for the eight tickets outside the 156-ticket eligible classification set.

### Classification comparison

Zero-shot and few-shot classification were evaluated on the same 147 successfully classified tickets.

| Measure | Zero-shot | Few-shot |
|---|---:|---:|
| Valid JSON responses | 135 | 135 |
| Keyword responses | 12 | 12 |
| Invalid responses | 9 | 9 |
| Empty tickets | 4 | 4 |
| Long tickets | 4 | 4 |
| Correct classifications | 126 | 147 |
| Accuracy | 85.71% | 100.00% |
| Total tokens | 15,172 | 23,752 |
| Tokens for classified tickets | 14,276 | 22,361 |
| Average tokens per classified ticket | 97.12 | 152.12 |

The few-shot approach achieved higher measured accuracy on this evaluation set, while using more tokens.

The zero-shot confusion matrix, with class order billing, delivery, technical, fraud, is:

```text
[[38,  0,  0,  0],
 [ 0, 36,  0,  0],
 [10,  0, 29,  0],
 [11,  0,  0, 23]]
```

### Token-budget experiment

A token-budget experiment used a budget of 6,000 tokens.

| Measure | Result |
|---|---:|
| Model responses | 62 |
| Valid JSON responses | 55 |
| Keyword responses | 4 |
| Invalid responses | 3 |
| Empty tickets | 4 |
| Long tickets | 4 |
| Total tokens used | 6,025 |
| Budget-exhausted outcomes | 94 |

The total can slightly exceed the configured budget because token usage is checked after a model response. Once the limit is detected, further model work is stopped.

### Final routing

The final few-shot triage output routes tickets as follows:

| Destination | Tickets |
|---|---:|
| support_queue | 102 |
| security_team | 34 |
| human_review | 17 |
| premium_desk | 11 |
| **Total** | **164** |

The routing workflow uses the classification and guardrail results to direct tickets to the appropriate destination. Fraud-related cases are routed to the security team, while cases requiring manual handling are sent for human review.

The supplied `mock_llm.py` is used as provided.

## Part D

### Policy RAG pipeline

The policy RAG implementation is in:

```text
src/rag_policy.py
```

The pipeline uses TF-IDF vectorization and cosine similarity to retrieve relevant policy chunks.

Configuration:

| Parameter | Value |
|---|---:|
| Chunk size | 40 |
| Chunk overlap | 10 |
| Top-K retrieval | 3 |
| Total chunks | 15 |

The 15 chunks are distributed as follows:

| Policy document | Chunks |
|---|---:|
| refund_policy.txt | 4 |
| delivery_policy.txt | 3 |
| escalation_policy.txt | 3 |
| payment_policy.txt | 3 |
| privacy_policy.txt | 2 |

For the query `refund policy late delivery`, the top three retrieved chunks all came from `refund_policy.txt`. Their cosine similarity scores were approximately 0.2719, 0.2514, and 0.2454.

The answer function retrieves the top three chunks and sends the policy context and question to the supplied `mock_llm.chat` interface. The prompt instructs the model to answer using the provided context and to use a fallback when the policy documents do not contain the answer.

The evaluation contains 14 questions: 12 answerable policy questions and two unanswerable questions.

### RAG evaluation with overlap

| Measure | Result |
|---|---:|
| Answerable questions | 12 |
| Correct expected-document retrieval | 12/12 |
| Correct expected-fact checks | 12/12 |
| Correct unanswerable fallbacks | 2/2 |

The two unanswerable questions concern the company mascot's favourite colour and the winner of a cricket world cup final. Both correctly receive the policy-not-found fallback.

Results are saved in:

```text
outputs/rag_evaluation.csv
```

### Chunk-overlap comparison

A separate experiment disables chunk overlap while keeping the retrieval evaluation questions and top-K setting unchanged.

| Measure | 10-token overlap | Zero overlap |
|---|---:|---:|
| Total chunks | 15 | 13 |
| Expected-document retrieval | 12/12 | 12/12 |
| Expected-fact checks | 12/12 | 10/12 |
| Correct unanswerable fallbacks | 2/2 | 2/2 |

With zero overlap, the following boundary-sensitive facts were not preserved in the generated answers:

- The delivery-time threshold of more than 45 minutes for a full refund.
- The 48-hour return period when a payment fails but money is deducted.

The overlap comparison shows that document retrieval alone does not guarantee that the answer contains the required fact. In this evaluation, overlap preserved useful boundary context and improved expected-fact accuracy from 10/12 to 12/12.

Results are saved in:

```text
outputs/rag_evaluation_overlap0.csv
```

### Tool definitions

The agent implementation uses five tools defined in:

```text
src/agent_tools.py
```

| Tool | Purpose |
|---|---|
| `get_order` | Retrieve an order's status, amount, and delivery time |
| `search_policy` | Retrieve relevant policy chunks |
| `calculate_refund` | Determine refund eligibility and amount |
| `issue_refund` | Issue an eligible automatic refund |
| `escalate_to_human` | Send a refund requiring approval to a human |

The tool definitions and dispatch mapping are exposed through `TOOLS_SPEC` and `TOOL_MAP`.

The agent checks order status before allowing a refund. The implemented refund rules are:

- Only completed orders are eligible for a refund.
- A completed order delivered in more than 45 minutes qualifies for a full order-amount refund.
- A completed order delivered in 45 minutes or less does not qualify for a late-delivery refund.
- Refunds up to INR 1,000 can be issued automatically.
- Refunds above INR 1,000 are escalated for human approval.
- Cancelled orders are not refunded.
- Missing orders return a not-found outcome.

The refund tool also enforces the INR 1,000 automatic-approval limit, and the escalation tool checks that the amount is above that limit.

### Agent execution and safety limits

The agent implementation is in:

```text
src/agent.py
```

The agent uses a bounded tool-calling loop with these default limits:

| Limit | Setting |
|---|---:|
| Maximum iterations | 6 |
| Token budget | 6,000 |
| Time limit | 10 seconds |

The workflow records model messages, tool calls, tool observations, token usage, and execution state. It supports checkpointing after tool observations and resuming from a saved run.

The agent also returns explicit fallback outcomes when an execution limit is reached. These include:

- `FALLBACK_MAX_ITERATIONS`
- `FALLBACK_TOKEN_LIMIT`
- `FALLBACK_TIMEOUT`

The refund ledger records refund or escalation actions as JSONL entries. Checkpoint state is saved under `state/`.

### Seven-scenario agent evaluation

The evaluation script is:

```text
src/run_agent_evaluation.py
```

All seven recorded scenarios passed.

| Scenario | Expected outcome | Actual outcome | Refund amount (INR) | Model calls | Tokens |
|---|---|---|---:|---:|---:|
| S1 | REFUND | REFUND | 128.25 | 5 | 1,522 |
| S2 | REFUND | REFUND | 135.00 | 5 | 1,522 |
| S3 | ESCALATE | ESCALATE | 1,999.00 | 5 | 1,521 |
| S4 | DENIED | DENIED | 0.00 | 4 | 1,077 |
| S5 | DENIED | DENIED | 0.00 | 3 | 674 |
| S6 | NOT_FOUND | NOT_FOUND | 0.00 | 2 | 302 |
| S7 | FALLBACK | FALLBACK_MAX_ITERATIONS | 0.00 | 6 | 3,744 |

The scenarios demonstrate:

- Automatic refunds for eligible completed orders below the approval threshold.
- Human escalation for a refund above INR 1,000.
- Denial when delivery is within 45 minutes.
- Denial for a cancelled order.
- A not-found result for an unknown order ID.
- A safe fallback when the agent reaches its maximum iteration count.

The evaluation results are saved in:

```text
outputs/agent_evaluation.csv
```

### Token and timeout demonstrations

The limit demonstration script is:

```text
src/run_agent_limit_demos.py
```

The token-limit demonstration returns `FALLBACK_TOKEN_LIMIT`. In the recorded demonstration, the agent made two model calls, used 330 tokens, and executed only the initial order lookup before stopping.

The timeout demonstration returns `FALLBACK_TIMEOUT`. It used zero model calls and zero tokens because the time limit was reached before model execution.

These demonstrations verify that the agent can stop rather than continue execution after reaching its configured limits.

### Checkpoint and resume demonstration

The checkpoint demonstration script is:

```text
src/run_checkpoint_demo.py
```

The demonstration uses the run ID:

```text
checkpoint_S1_demo
```

It simulates a crash after the second tool, `search_policy`, and then resumes from the saved checkpoint.

The resumed workflow completes successfully:

| Measure | Result |
|---|---:|
| Final outcome | REFUND |
| Refund amount | INR 128.25 |
| Model calls | 5 |
| Tokens used | 1,522 |
| Tool executions | 4 |

The tool sequence is:

1. `get_order`
2. `search_policy`
3. `calculate_refund`
4. `issue_refund`

The completed workflow does not repeat the already-recorded tool executions after resuming. Its refund ledger is stored separately in:

```text
outputs/checkpoint_demo_ledger.jsonl
```

### ReAct versus plan-and-execute

The implementation uses a ReAct-style loop: the model selects a tool, observes its result, and then decides the next step. This supports dynamic handling of different order states and policy outcomes.

The recorded evaluation workflows show that execution length varies by scenario:

| Scenario | Outcome | Model calls | Tokens |
|---|---|---:|---:|
| S1 | REFUND | 5 | 1,522 |
| S5 | DENIED | 3 | 674 |
| S6 | NOT_FOUND | 2 | 302 |

A missing order can terminate after a short lookup path, while a refund requires policy retrieval, eligibility calculation, and an appropriate action.

A plan-and-execute approach could create a plan before executing tools. That may add an initial planning call and tokens, including for simple cases that terminate early. It may also need replanning when an order is missing, cancelled, or produces an unexpected tool observation. No separate plan-and-execute implementation was benchmarked in this project, so there are no measured plan-and-execute call or token counts to compare. The ReAct-style approach was selected because it responds to tool observations while remaining bounded by iteration, token, and time limits.

### Part D output files

Important Part D artifacts include:

```text
data/raw/agent_scenarios.csv
outputs/rag_evaluation.csv
outputs/rag_evaluation_overlap0.csv
outputs/agent_evaluation.csv
outputs/agent_runs.jsonl
outputs/refund_ledger.jsonl
outputs/checkpoint_demo_ledger.jsonl
state/checkpoint_S1_demo.json
```

## Limitations and Next Steps

### Limitations

- The project uses generated datasets and a supplied mock LLM interface; results do not establish production performance.
- Customer segmentation and lapse prediction results depend on the generated data and selected cohort definition.
- The Premium retention illustration is post-hoc because its segment flag uses an RFM window that overlaps the lapse label window. It should not be treated as a prospective evaluation.
- Few-shot ticket classification performed better on the measured evaluation set but used more tokens than zero-shot classification.
- The token-budget experiment can exceed the configured limit slightly because usage is checked after a model response.
- TF-IDF retrieval is lexical and may not retrieve semantically related passages as effectively as an embedding-based retriever.
- RAG answer quality depends on chunk boundaries and context completeness. The zero-overlap comparison demonstrates that a relevant document can be retrieved while a required fact is still omitted from the answer.
- The agent uses a mock model and local data. Its refund and escalation actions are demonstrations, not integrations with a real payment provider or customer account system.
- The JSONL refund ledger is an append-only demonstration log. Re-running action workflows against an existing ledger can add more entries, so evaluation runs should use a clean state when reproducibility is required.
- The ReAct workflow was implemented and evaluated; a separate plan-and-execute implementation was not built or benchmarked.

### Next steps

- Evaluate the analytics and prediction pipelines on additional, independently generated or approved real-world datasets.
- Validate lapse prediction on later time periods to measure temporal generalization.
- Improve retention evaluation by defining customer segments strictly from information available before the prediction cutoff.
- Explore richer text representations and retrieval methods while retaining retrieval and answer-quality checks.
- Add more policy questions that test boundary conditions, conflicting evidence, and unanswerable requests.
- Extend agent tests to cover additional order states, tool failures, and interrupted executions.
- Add stronger operational controls before connecting any real refund or payment system, including authorization, human approval, idempotency, and audit review.
- Monitor model accuracy, token usage, fallback rates, and tool execution outcomes as the system evolves.