<div style="align:center"><h1>Finance RAG Pipeline</h1></div>

This is the model will take the input is the query related to the financial field specificly for stock to answer about the based knowledge question or analysis the specific stocks using 1 year historical data prices with 1 year news related to the stock symbol

---

## I. Prerequisite

#### A. Install the Requirements Dependencies
<details>
  <summary><b>Method 1: Install using pip (Manual)</b></summary>
  <br>
  <ul>
    <li>Make sure you have Python installed on your system.</li>
    <li>Open a terminal or command prompt.</li>
    <li>Navigate to the project directory where the <code>requirements.txt</code> file is located.</li>
    <li>Run the following command to install the required packages:</li>
  </ul>

<pre style="margin-left: 2em;"><code>pip install -r requirements.txt</code></pre>
</details>

<details>
  <summary><b>Method 2: Install using Script (Automatically)</b></summary>
  <ul>
    <li>Double-click the <code>Install.bat</code> file to automatically install the required packages (Windows only).</li>
  </ul>
</details>

#### B. Update the API Keys inside the assistant/.env file
- Open the `.env` file located in the `root` directory.
- Replace the placeholder values with your actual API keys for OpenAI, Finnhub, and Financial Modeling Prep.

- Save the changes to the `.env` file.

    ```plaintext
    OPENAI_API_KEY=your_openai_api_key
    FINNHUB_API_KEY=your_finnhub_api_key
    FMP_API_KEY=your_financial_modeling_prep_api_key
    ```

    ![image](./documents/images/Set_Up_API_Keys.png)

#### C. Run the Script

<details>
    <summary><b>Method 1: Run the code in terminal (Manual)</b></summary>
    <br>
    <ul>
        <li><b>Step 1: Update the sqlite Database</b></li>
    </ul>
    <pre style="margin-left: 2em;"><code>python manage.py migrate</code></pre>
    <ul>
        <li><b>Step 2: Run the Django Server</b></li>
    </ul>
    <pre style="margin-left: 2em;"><code>python manage.py runserver</code></pre>
</details>

<details>
    <summary><b>Method 2: Run the code using Script (Automatically)</b></summary>
    <br>
    <ul>
        <li>Double-click the <code>Analysis_Server.bat</code> file to automatically run the server (Windows only).</li>
    </ul>
</details>

---

## II. Sample Output

#### A. Output for Ticker Analysis Services
- **Input Query**: What is the current price of Nvidia?

![image](./documents/images/Output_Specific_Stock.png)

#### B. Output for General Knowledge Services
- **Input Query**: What is a P/E ratio?

![image](./documents/images/General_Financial_Concept.png)
