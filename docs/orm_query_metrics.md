# ORM Query Performance Metrics and Grafana Dashboard

## Overview

This document details the implementation of Prometheus metrics for tracking CPU and memory usage of Django ORM queries within the Learning Platform API, specifically focusing on the `StudentViewSet` in [`LearningAPI/views/student_view.py`](LearningAPI/views/student_view.py). It also provides comprehensive Grafana dashboard configurations to visualize these metrics.

## Implementation Approach

To gain insight into the resource consumption of individual ORM queries, the following steps were taken:

1.  **Dependency Installation:**
    -   The `psutil` library was added to [`requirements.txt`](requirements.txt) to enable system-level CPU and memory monitoring. This ensures `psutil` is installed when the Docker container is rebuilt.

2.  **Prometheus Metrics Definition:**
    -   New Prometheus metrics were defined in [`LearningAPI/views/student_view.py`](LearningAPI/views/student_view.py) to capture CPU usage, memory usage, and total execution count for ORM queries. These are:
        -   `learning_api_orm_query_cpu_percent`: A histogram to track CPU usage percentage.
        -   `learning_api_orm_query_memory_mb`: A histogram to track memory usage in Megabytes.
        -   `learning_api_orm_query_total`: A counter to track the total number of ORM queries, labeled by `query_type` and `status` (success/error).

3.  **`ORMQueryMonitor` Context Manager:**
    -   A custom Python context manager, `ORMQueryMonitor`, was created in [`LearningAPI/views/student_view.py`](LearningAPI/views/student_view.py). This context manager:
        -   Records the process's CPU and memory usage at the start and end of an ORM query block.
        -   Calculates the difference to determine resource consumption during the query.
        -   Observes the `learning_api_orm_query_cpu_percent` and `learning_api_orm_query_memory_mb` histograms.
        -   Increments the `learning_api_orm_query_total` counter, marking the query as 'success' or 'error' based on exceptions.

4.  **Wrapping ORM Queries:**
    -   Key Django ORM query operations within the `StudentViewSet` (e.g., `list`, `retrieve`, `update` methods, and various serializer `get_` methods) were wrapped with the `ORMQueryMonitor` context manager. Each wrapped block was assigned a descriptive `query_type` label (e.g., `nssuser_initial_filter`, `student_personality_get`, `capstone_annotate`).

## Grafana Dashboard Visualizations

The following panels are recommended for a Grafana dashboard to visualize the ORM query performance metrics. Ensure your Grafana instance is connected to your Prometheus data source (e.g., `http://prometheus:9090`).

### Dashboard Variables (Optional but Recommended)

Add a dashboard variable to filter by query type:

1.  **Dashboard settings** → **Variables** → **Add variable**
2.  **Name:** `query_type`
3.  **Type:** Query
4.  **Query:** `label_values(learning_api_orm_query_total, query_type)`
5.  **Multi-select:** Enable
6.  **Include All:** Enable
7.  Modify queries below to filter: `{query_type=~"$query_type"}`

---

### Panel 1: Average CPU Usage by Query Type (Time Series)

*   **Description:** Displays the average CPU percentage used by each ORM query type over time, smoothed over a 5-minute window.
*   **PromQL Query:**
    ```promql
    rate(learning_api_orm_query_cpu_percent_sum[5m]) / rate(learning_api_orm_query_cpu_percent_count[5m])
    ```
*   **Visualization:** Time series graph
*   **Unit:** Percent (0-100)
*   **Legend:** `{{query_type}}`
*   **Panel Title:** "ORM Query CPU Usage by Type (Avg over 5m)"

---

### Panel 2: Average Memory Usage by Query Type (Time Series)

*   **Description:** Displays the average memory (in MB) consumed by each ORM query type over time, smoothed over a 5-minute window.
*   **PromQL Query:**
    ```promql
    rate(learning_api_orm_query_memory_mb_sum[5m]) / rate(learning_api_orm_query_memory_mb_count[5m])
    ```
*   **Visualization:** Time series graph
*   **Unit:** Megabytes (MB) - use `bytes(IEC)` and Grafana will auto-convert.
*   **Legend:** `{{query_type}}`
*   **Panel Title:** "ORM Query Memory Usage by Type (Avg over 5m)"

---

### Panel 3: Query Execution Rate by Type (Time Series)

*   **Description:** Shows how frequently each ORM query type is executed per second, smoothed over a 5-minute window.
*   **PromQL Query:**
    ```promql
    rate(learning_api_orm_query_total[5m])
    ```
*   **Visualization:** Time series graph
*   **Unit:** Operations per second (`ops/sec`)
*   **Legend:** `{{query_type}} - {{status}}`
*   **Panel Title:** "ORM Query Execution Rate by Type"

---

### Panel 4: Top 10 Most CPU-Intensive Queries (Current Snapshot)

*   **Description:** A bar gauge showing the top 10 ORM queries with the highest average CPU usage since the service started.
*   **PromQL Query:**
    ```promql
    topk(10, learning_api_orm_query_cpu_percent_sum / learning_api_orm_query_cpu_percent_count)
    ```
*   **Visualization:** Bar gauge
*   **Unit:** Percent (0-100)
*   **Orientation:** Horizontal
*   **Display mode:** Gradient
*   **Legend:** `{{query_type}}` (configured in the query options or by using "Display name" in field overrides)
*   **Panel Title:** "Top 10 CPU-Intensive ORM Queries"

---

### Panel 5: Top 10 Most Memory-Intensive Queries (Current Snapshot)

*   **Description:** A bar gauge showing the top 10 ORM queries with the highest average memory usage since the service started.
*   **PromQL Query:**
    ```promql
    topk(10, learning_api_orm_query_memory_mb_sum / learning_api_orm_query_memory_mb_count)
    ```
*   **Visualization:** Bar gauge
*   **Unit:** Megabytes (MB)
*   **Orientation:** Horizontal
*   **Display mode:** Gradient
*   **Legend:** `{{query_type}}`
*   **Panel Title:** "Top 10 Memory-Intensive ORM Queries"

---

### Panel 6: ORM Query Performance Summary (Table)

*   **Description:** A detailed table summarizing average CPU, average memory, and total executions for all ORM query types.
*   **PromQL Queries (multiple, add as separate queries in the panel):**
    1.  **Average CPU:** `label_replace(learning_api_orm_query_cpu_percent_sum / learning_api_orm_query_cpu_percent_count, "metric", "avg_cpu_percent", "", "")`
    2.  **Average Memory:** `label_replace(learning_api_orm_query_memory_mb_sum / learning_api_orm_query_memory_mb_count, "metric", "avg_memory_mb", "", "")`
    3.  **Execution Count:** `label_replace(learning_api_orm_query_cpu_percent_count, "metric", "executions", "", "")`
    4.  **Error Count:** `label_replace(sum by (query_type) (increase(learning_api_orm_query_total{status="error"}[5m])), "metric", "errors_5m", "", "")`
*   **Visualization:** Table
*   **Transformations:**
    1.  **Merge:** Join by labels.
    2.  **Organize fields:** Rename columns to "Query Type", "Avg CPU %", "Avg Memory MB", "Executions", "Errors (5m)".
*   **Units:** Set appropriate units for each column (e.g., "percent (0-100)" for CPU, "bytes(IEC)" for Memory, "short" for Executions/Errors).
*   **Panel Title:** "ORM Query Performance Summary"

---

### Panel 7: 95th Percentile CPU and Memory Usage (Time Series)

*   **Description:** Tracks the 95th percentile of CPU and memory usage for ORM queries, useful for identifying outliers and worst-case scenarios.
*   **PromQL Queries (add as separate queries in the panel):**
    1.  **P95 CPU:** `histogram_quantile(0.95, sum by (le, query_type) (rate(learning_api_orm_query_cpu_percent_bucket[5m])))`
    2.  **P95 Memory:** `histogram_quantile(0.95, sum by (le, query_type) (rate(learning_api_orm_query_memory_mb_bucket[5m])))`
*   **Visualization:** Time series graph
*   **Units:** Set Left Y-axis to "Percent (0-100)" and Right Y-axis to "Megabytes (MB)".
*   **Legend:** `{{query_type}} - P95 CPU` and `{{query_type}} - P95 Memory`
*   **Panel Title:** "ORM Query P95 CPU & Memory Usage"

---

### Panel 8: Query Error Rate (Time Series)

*   **Description:** Visualizes the rate of failed ORM queries over time.
*   **PromQL Query:**
    ```promql
    rate(learning_api_orm_query_total{status="error"}[5m])
    ```
*   **Visualization:** Time series graph
*   **Unit:** Errors per second (`errors/sec`)
*   **Legend:** `{{query_type}}`
*   **Panel Title:** "ORM Query Error Rate"

---

## Saving Your Dashboard

Once you've configured all your panels:
1.  Click the **Save icon** (💾) at the top of the Grafana dashboard.
2.  Give your dashboard a meaningful name (e.g., "Django ORM Performance").
3.  Consider exporting the dashboard as JSON (Dashboard settings → JSON Model) for version control and easy sharing.