# (WIP) Delhi Climate Outlook: 1951 — 2100 🌡️
### Multi-Factor Temperature Projection Dashboard

An interactive dashboard that models the multi-layered drivers behind Delhi's rising temperatures through the year 2100. Rather than utilising a generic flat warming projection, this engine dynamically integrates global climate data with localised land-use master plans and UN demographic forecasts to construct a hyper-local climate simulation.

🔗 **[Live Interactive Dashboard](https://delhiclimate.streamlit.app/)**

> ⚠️ **Deployment Note:** This application is deployed on a free resource tier via Streamlit Community Cloud. If the application has been inactive for a few days, it may go to "sleep" to conserve server energy. If you see a sleeping state screen, simply click the **"Wake up app"** button, and the live interface will spin back up in roughly 30 seconds.

---

## 📊 Core Datasets In Use
The architecture synthesises data from three foundational local data structures:

| Data Asset | Type | Strategic Purpose |
| :--- | :--- | :--- |
| `DelhiHistoricData19702024.csv` | Weather | Establishes the 50-year base seasonal climatology to retain monthly variations (e.g., maintaining sharp pre-monsoon heat peaks). |
| `DelhiLULC.xlsx - Sheet1.csv` | Land Use | Correlates chronological "Built-up" area growth (in Lakh Hectares) with rising minimum baseline temperatures to isolate local UHI sensitivity. |
| `Indiapop.csv` | Demographics | Houses UN India projections through 2100. Applies a dynamic, capped migration share ($2.8\%$) to bridge localised warming forecasts beyond the 2041 infrastructure cap. |

---

## 🛠️ Tech Stack & Architecture
* **Language:** Python 3.x
* **Core Interface:** Streamlit (UI Engine)
* **Statistical Modeling:** Scikit-Learn (Linear Regression Core Engine)
* **Data Processing:** Pandas & NumPy
* **Data Visualization:** Plotly Graph Objects (High-Contrast Presentation Layer)
