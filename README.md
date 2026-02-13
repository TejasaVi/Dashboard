# Flask Skeleton Application

## Run locally
```bash
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python run.py
```

## Broker integrations

Set these environment variables before running app.

### Zerodha
- `ZERODHA_API_KEY`
- `ZERODHA_API_SECRET`
- Optional: `ZERODHA_ACCESS_TOKEN`

### Fyers
- `FYERS_CLIENT_ID`
- `FYERS_SECRET_KEY`
- `FYERS_REDIRECT_URI` (example: `http://127.0.0.1:5000/api/fyers/callback`)
- Optional: `FYERS_ACCESS_TOKEN`

### Stoxkart
- `STOXKART_CLIENT_ID`
- `STOXKART_SECRET_KEY`
- `STOXKART_REDIRECT_URI` (example: `http://127.0.0.1:5000/api/stoxkart/callback`)
- `STOXKART_AUTH_BASE_URL`
- Optional: `STOXKART_TOKEN_URL`
- Optional: `STOXKART_API_BASE_URL`
- Optional: `STOXKART_ACCESS_TOKEN`


## Debug logging
- Application debug logs are written to `logs/app_debug.log`.
- Incoming API requests are logged with method, path, args, and payload data.
- Outgoing API responses are logged with status and body.
- External HTTP calls made via `requests` are logged with params/data/json and response body.

## API routes

### Zerodha
- `GET /api/zerodha/login-url`
- `GET /api/zerodha/callback` (recommended Kite redirect URL)
- `GET /zerodha/callback` (compatibility route if Kite app is configured without `/api`)
- `GET /api/zerodha/status`
- `GET /api/zerodha/profile`

### Fyers
- `GET /api/fyers/login-url`
- `GET /api/fyers/callback` (configure this URL in Fyers app settings)
- `GET /api/fyers/status`
- `GET /api/fyers/profile`

### Stoxkart
- `GET /api/stoxkart/login-url`
- `GET /api/stoxkart/callback`
- `GET /api/stoxkart/status`
- `GET /api/stoxkart/profile`

### Multi-broker execution
- `GET /api/brokers/status`
- `GET /api/brokers/active`
- `POST /api/brokers/switch`
- `POST /api/brokers/configure` (set API keys/secrets at runtime)
- `POST /api/brokers/disconnect` (clear broker session / disconnect in-memory token)
- `POST /api/brokers/place-order`
- `POST /api/brokers/execute-strategy`
- Send `brokers` as array, and broker-specific symbols when needed (`fyers_symbol`, `stoxkart_symbol`)
- Optional: `failover_enabled=true` to try selected brokers in sequence using active broker priority

## Trading architecture
- Unified broker interface with adapters: Zerodha/Fyers/Stoxkart
- Broker switcher for active platform selection
- Abstract order execution engine
- Strategy router (single, iron_condor, call_spread, put_spread, calendar)
- Failover system for resilient execution


## Runtime broker credential input
- Open **/broker-setup** to provide API keys/secrets for Zerodha, Fyers, and Stoxkart.
- Credentials are applied in-memory through `POST /api/brokers/configure`.
- After saving keys, click **Connect** to complete OAuth/login where required.
