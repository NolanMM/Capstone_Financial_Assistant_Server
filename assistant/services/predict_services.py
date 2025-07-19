import os
from datetime import datetime, timedelta
import numpy as np
import pandas as pd
import requests
import torch
import torch.nn as nn
from sklearn.preprocessing import MinMaxScaler

DROPOUT = 0.5
HORIZON = 5
CHK_PATH = "assistant/services/lstm_best.pth"

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

try:
    chkpt = torch.load(CHK_PATH, map_location=device)
    feature_cols = chkpt["feature_order"]
    hidden_dim = chkpt["hidden_dim"]
    num_layers = chkpt["num_layers"]
    WINDOW_SIZE = chkpt["window"]
    TARGET = "Return_1D"
except FileNotFoundError:
    raise RuntimeError(f"Checkpoint file not found at {CHK_PATH}. Please ensure the model file is in the correct directory.")

def fetch_all_history(ticker: str, api_key: str) -> pd.DataFrame:
    all_chunks = []
    to_date = datetime.today().date()
    chunk_size = 30

    while True:
        from_date = to_date - timedelta(days=int(chunk_size*1.5))
        url = (
            f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}"
            f"?from={from_date:%Y-%m-%d}&to={to_date:%Y-%m-%d}"
            f"&apikey={api_key}"
        )
        resp = requests.get(url, timeout=30)
        resp.raise_for_status()
        data = resp.json().get("historical", [])
        if not data:
            break

        df_chunk = pd.DataFrame(data)[["date","open","high","low","close","volume"]]
        df_chunk["date"] = pd.to_datetime(df_chunk["date"])
        all_chunks.append(df_chunk)

        earliest = df_chunk["date"].min().date()
        if (to_date - earliest).days < 2:
            break
        to_date = earliest - timedelta(days=1)

    df = pd.concat(all_chunks, ignore_index=True)
    df = df.drop_duplicates(subset="date").sort_values("date").reset_index(drop=True)

    df["Return_3D"]     = df["close"].pct_change(periods=3).shift(-3)
    df["Return_1D"]     = df["close"].pct_change()
    df["Volatility_3D"] = df["Return_1D"].rolling(window=3).std()

    return df.dropna(subset=["Return_3D","Volatility_3D"]).reset_index(drop=True)

# --- LSTM Model Definition ---
class LSTMModel(nn.Module):
    def __init__(self, input_dim, hidden_dim, num_layers, dropout=0.5):
        super().__init__()
        self.lstm = nn.LSTM(input_dim, hidden_dim, num_layers,
                            dropout=dropout, batch_first=True)
        self.fc   = nn.Linear(hidden_dim, 1)

    def forward(self, x):
        # x: (batch, seq_len, input_dim)
        h0 = torch.zeros(self.lstm.num_layers, x.size(0),
                         self.lstm.hidden_size, device=x.device)
        c0 = torch.zeros_like(h0)
        out, _ = self.lstm(x, (h0, c0))
        return self.fc(out[:, -1, :]).squeeze(-1) # output last time step

model = LSTMModel(
    input_dim  = len(feature_cols), 
    hidden_dim = hidden_dim,
    num_layers = num_layers,
    dropout    = DROPOUT
).to(device)

model.load_state_dict(chkpt["model_state"])
model.eval()

def compute_indicators(df):
    delta = df["Close"].diff()
    gain, loss = delta.clip(lower=0), -delta.clip(upper=0)
    ru = gain.ewm(span=14).mean(); rd = loss.ewm(span=14).mean() # 14-day EMA
    rs = ru/rd
    df["RSI"] = 100 - 100/(1+rs)

    ema12 = df["Close"].ewm(span=12).mean() # 12-day EMA
    ema26 = df["Close"].ewm(span=26).mean() # 26-day EMA
    macd = ema12 - ema26
    df["MACD"]        = macd
    df["MACD_Signal"] = macd.ewm(span=9).mean()
    df["MACD_Hist"]   = df["MACD"] - df["MACD_Signal"] # MACD histogram

    sma20 = df["Close"].rolling(20).mean()
    std20 = df["Close"].rolling(20).std()
    df["BB_Mid"], df["BB_Upper"], df["BB_Lower"] = sma20, sma20+2*std20, sma20-2*std20

    df["Return_1D"] = df["Close"].pct_change().shift(-1)
    df["lag1_ret"]  = df["Return_1D"].shift(1)
    return df.dropna()

def prepare_quarterly(df, feats, tgt, window): # Scale quarterly data 
    df2 = df.copy()
    df2["Quarter"] = df2.index.to_period("Q") 
    scalers, chunks = {}, []
    for q, g in df2.groupby("Quarter"): # group by quarter
        if len(g) < window: 
            continue
        m = MinMaxScaler()
        arr = m.fit_transform(g[feats + [tgt]].values) 
        chunks.append(pd.DataFrame(arr, index=g.index, columns=feats+[tgt])) 
        scalers[str(q)] = m
    df_s = pd.concat(chunks).sort_index().dropna() # concatenate all quarters
    return scalers, df_s

def build_all_windows(df_s, feats, tgt, window): # Build sliding windows
    X = []
    data = df_s[feats].values
    for i in range(window, len(df_s)): 
        X.append(data[i-window:i])
    return np.array(X)

def forecast_future_scaled(net, window_scaled, horizon): # Forecast future returns using the trained model
    arr, preds = window_scaled.copy(), []
    for _ in range(horizon):
        inp = torch.tensor(arr).float().unsqueeze(0).to(device)
        with torch.no_grad():
            p = net(inp).item()
        preds.append(p)
        # roll the window
        new_row = arr[-1].copy()
        new_row[-1] = p
        arr = np.vstack([arr[1:], new_row])
    return np.array(preds)

def get_prediction(ticker: str, fmp_api_key: str) -> dict:

    raw_df = fetch_all_history(ticker.upper(), fmp_api_key)

    df = (
        raw_df.rename(columns={
            "open":"Open", "high":"High", "low":"Low",
            "close":"Close", "volume":"Volume"
        })
        .set_index("date")
    )

    df = compute_indicators(df)

    scalers_q, df_scaled = prepare_quarterly(df, feature_cols, TARGET, WINDOW_SIZE)

    X_all = build_all_windows(df_scaled, feature_cols, TARGET, WINDOW_SIZE) 
    last_window = X_all[-1]

    fc_scaled = forecast_future_scaled(model, last_window, HORIZON)
    q_last = str(df_scaled.index[-1].to_period("Q"))
    m = scalers_q[q_last]

    minv, maxv = m.data_min_[-1], m.data_max_[-1] # get min/max for the last quarter
    raw_rets = fc_scaled * (maxv - minv) + minv
    pct_rets = raw_rets * 100

    last_price = df["Close"].iloc[-1]
    price_forecast = [last_price * (1 + raw_rets[0])]
    for r in raw_rets[1:]:
        price_forecast.append(price_forecast[-1] * (1 + r))
    
    days = np.arange(1, HORIZON+1)
    return {
        "ticker": ticker.upper(),
        "dates": [datetime.today() + pd.Timedelta(days=d) for d in days],
        "predicted_prices": np.round(price_forecast, 4).tolist(),
        "predicted_returns_pct": np.round(pct_rets, 4).tolist()
    }