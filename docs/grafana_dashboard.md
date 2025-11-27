# Grafana Dashboard Documentation

## Overview
This document outlines the setup of the Grafana dashboard for visualizing Prometheus metrics from the Learning Platform API. It includes a guide for initial setup and details on the custom panels created.

## Initial Grafana Setup Guide (Prometheus Data Source)

To get started with Grafana and connect it to your Prometheus instance:

1.  **Access Grafana UI:** Open your web browser and navigate to `http://localhost:3001` (or the port you configured).
2.  **Login:** Use the default credentials `admin`/`admin` (it's highly recommended to change these immediately).
3.  **Add Prometheus Data Source:**
    *   Click the **Gear icon** (Configuration) in the left sidebar.
    *   Select **"Data Sources"**.
    *   Click **"Add data source"**.
    *   Choose **"Prometheus"** from the list.
    *   In the "HTTP" section, set the **URL** to `http://prometheus:9090`.
    *   Ensure "Access" is set to "Server (default)".
    *   Click **"Save & Test"**. You should see a "Data source is working" message.

## Creating a Dashboard and Adding Panels

Once your Prometheus data source is configured, you can start building your custom dashboards:

1.  **Create a New Dashboard:**
    *   Click the **"+"** icon in the left sidebar.
    *   Select **"Dashboard"**.
    *   Click **"Add visualization"** to add your first panel.

2.  **Configure a Panel:**
    *   In the panel editor, ensure your **Prometheus data source** is selected.
    *   Use the **"Metric browser"** or type directly into the **"PromQL"** query field to select and query your desired metrics.
    *   **Customize:**
        *   **Panel Title:** Give your panel a descriptive name.
        *   **Visualization:** Choose the appropriate visualization type (e.g., Graph, Stat, Gauge, Table).
        *   **Units:** Set the correct units for your metric (e.g., seconds, percent, bytes).
        *   **Legend:** Configure how the series names appear.
    *   Click **"Apply"** to save the panel to your dashboard.

3.  **Add More Panels:**
    *   Click the **"+"** icon at the top of the dashboard to add more panels.
    *   Repeat step 2 for each metric you want to visualize.

4.  **Save the Dashboard:**
    *   Once you've added all your desired panels, click the **Save icon** (💾) at the top of the dashboard.
    *   Give your dashboard a meaningful name (e.g., "Learning Platform Custom Metrics") and click "Save".

## Custom Dashboard Panels

The following panels have been created to visualize key custom metrics from the Learning Platform API.

### Panel 1: Student Project Moves - Average Duration

*   **Description:** Displays the average time taken to move students between projects.
*   **PromQL Query:**
    ```promql
    rate(learning_api_student_project_move_seconds_sum[5m]) / rate(learning_api_student_project_move_seconds_count[5m])
    ```
*   **Visualization:** Time series graph
*   **Unit:** seconds (s)

### Panel 2: Student Project Moves - Success Rate

*   **Description:** Shows the success rate of student project move operations as a percentage.
*   **PromQL Query:**
    ```promql
    rate(learning_api_student_project_move_total{status="success"}[5m]) / rate(learning_api_student_project_move_total[5m]) * 100
    ```
*   **Visualization:** Stat or Gauge
*   **Unit:** Percent (0-100)

### Panel 3: Core Skill Updates - Average Duration

*   **Description:** Displays the average time taken to update core skill levels.
*   **PromQL Query:**
    ```promql
    rate(learning_api_core_skill_update_seconds_sum[5m]) / rate(learning_api_core_skill_update_seconds_count[5m])
    ```
*   **Visualization:** Time series graph
*   **Unit:** seconds (s)

### Panel 4: Core Skill Updates - Success Rate

*   **Description:** Shows the success rate of core skill update operations as a percentage.
*   **PromQL Query:**
    ```promql
    rate(learning_api_core_skill_update_total{status="success"}[5m]) / rate(learning_api_core_skill_update_total[5m]) * 100
    ```
*   **Visualization:** Stat or Gauge
*   **Unit:** Percent (0-100)

### Panel 5: Team Assignments - Average Duration

*   **Description:** Displays the average time taken to assign students to teams.
*   **PromQL Query:**
    ```promql
    rate(learning_api_team_assignment_seconds_sum[5m]) / rate(learning_api_team_assignment_seconds_count[5m])
    ```
*   **Visualization:** Time series graph
*   **Unit:** seconds (s)

### Panel 6: Team Assignments - Success Rate

*   **Description:** Shows the success rate of team assignment operations as a percentage.
*   **PromQL Query:**
    ```promql
    rate(learning_api_team_assignment_total{status="success"}[5m]) / rate(learning_api_team_assignment_total[5m]) * 100
    ```
*   **Visualization:** Stat or Gauge
*   **Unit:** Percent (0-100)