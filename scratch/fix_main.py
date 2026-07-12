import re

filepath = r"c:\Users\sche-\Desktop\Programmieren Projekte\finance-ai-bot\backend\main.py"

with open(filepath, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update simple def routes to async def and add awaits
replacements = [
    # get_status
    (r"def get_status\(\):", "async def get_status():"),
    (r"db_data = get_predictions_from_db\(\)", "db_data = await get_predictions_from_db()"),
    
    # get_predictions
    (r"def get_predictions\(\):", "async def get_predictions():"),
    
    # get_watchlist
    (r"def get_watchlist\(\):", "async def get_watchlist():"),
    (r"return get_all_assets\(\)", "return await get_all_assets()"),
    
    # add_watchlist_item
    (r"def add_watchlist_item\(item: WatchlistItem, background_tasks: BackgroundTasks\):", 
     "async def add_watchlist_item(item: WatchlistItem, background_tasks: BackgroundTasks):"),
    (r"if asset_exists\(symbol\):", "if await asset_exists(symbol):"),
    (r"success = add_asset\(symbol, name, asset_type\)", "success = await add_asset(symbol, name, asset_type)"),
    
    # delete_watchlist_item
    (r"def delete_watchlist_item\(symbol: str\):", "async def delete_watchlist_item(symbol: str):"),
    (r"success = delete_asset\(symbol_upper\)", "success = await delete_asset(symbol_upper)"),
    
    # get_portfolio
    (r"def get_portfolio\(portfolio_id: int = 1\):", "async def get_portfolio(portfolio_id: int = 1):"),
    (r"return get_portfolio_from_db\(portfolio_id\)", "return await get_portfolio_from_db(portfolio_id)"),
    
    # add_portfolio_item_route
    (r"def add_portfolio_item_route\(item: PortfolioItem, portfolio_id: int = 1\):",
     "async def add_portfolio_item_route(item: PortfolioItem, portfolio_id: int = 1):"),
    (r"success = save_portfolio_item\(item.symbol, item.quantity, item.buy_price, portfolio_id\)",
     "success = await save_portfolio_item(item.symbol, item.quantity, item.buy_price, portfolio_id)"),
     
    # delete_portfolio_item_route
    (r"def delete_portfolio_item_route\(symbol: str, portfolio_id: int = 1\):",
     "async def delete_portfolio_item_route(symbol: str, portfolio_id: int = 1):"),
    (r"success = delete_portfolio_item\(symbol, portfolio_id\)",
     "success = await delete_portfolio_item(symbol, portfolio_id)"),
     
    # get_portfolios_route
    (r"def get_portfolios_route\(\):", "async def get_portfolios_route():"),
    (r"return get_portfolios\(\)", "return await get_portfolios()"),
    
    # create_portfolio_route
    (r"def create_portfolio_route\(req: PortfolioCreateRequest\):",
     "async def create_portfolio_route(req: PortfolioCreateRequest):"),
    (r"success = create_portfolio\(req.name\)", "success = await create_portfolio(req.name)"),
    
    # delete_portfolio_route
    (r"def delete_portfolio_route\(portfolio_id: int\):", "async def delete_portfolio_route(portfolio_id: int):"),
    (r"success = delete_portfolio\(portfolio_id\)", "success = await delete_portfolio(portfolio_id)"),
    
    # get_settings_route
    (r"def get_settings_route\(\):", "async def get_settings_route():"),
    (r'"custom_prompt": get_setting\("custom_prompt", ""\),', '"custom_prompt": await get_setting("custom_prompt", ""),'),
    (r'"ai_tone": get_setting\("ai_tone", "professionell"\),', '"ai_tone": await get_setting("ai_tone", "professionell"),'),
    (r'"telegram_bot_token": get_setting\("telegram_bot_token", ""\),', '"telegram_bot_token": await get_setting("telegram_bot_token", ""),'),
    (r'"telegram_chat_id": get_setting\("telegram_chat_id", ""\),', '"telegram_chat_id": await get_setting("telegram_chat_id", ""),'),
    (r'"discord_webhook_url": get_setting\("discord_webhook_url", ""\),', '"discord_webhook_url": await get_setting("discord_webhook_url", ""),'),
    (r'"email_smtp_server": get_setting\("email_smtp_server", ""\),', '"email_smtp_server": await get_setting("email_smtp_server", ""),'),
    (r'"email_smtp_port": get_setting\("email_smtp_port", ""\),', '"email_smtp_port": await get_setting("email_smtp_port", ""),'),
    (r'"email_sender": get_setting\("email_sender", ""\),', '"email_sender": await get_setting("email_sender", ""),'),
    (r'"email_password": get_setting\("email_password", ""\),', '"email_password": await get_setting("email_password", ""),'),
    (r'"email_recipient": get_setting\("email_recipient", ""\)', '"email_recipient": await get_setting("email_recipient", "")'),
    
    # save_settings_route
    (r"def save_settings_route\(settings: SettingsRequest\):", "async def save_settings_route(settings: SettingsRequest):"),
    (r"success_prompt = save_setting\(\"custom_prompt\", settings.custom_prompt\)", "success_prompt = await save_setting(\"custom_prompt\", settings.custom_prompt)"),
    (r"success_tone = save_setting\(\"ai_tone\", settings.ai_tone\)", "success_tone = await save_setting(\"ai_tone\", settings.ai_tone)"),
    (r"save_setting\(\"telegram_bot_token\", settings.telegram_bot_token\)", "await save_setting(\"telegram_bot_token\", settings.telegram_bot_token)"),
    (r"save_setting\(\"telegram_chat_id\", settings.telegram_chat_id\)", "await save_setting(\"telegram_chat_id\", settings.telegram_chat_id)"),
    (r"save_setting\(\"discord_webhook_url\", settings.discord_webhook_url\)", "await save_setting(\"discord_webhook_url\", settings.discord_webhook_url)"),
    (r"save_setting\(\"email_smtp_server\", settings.email_smtp_server\)", "await save_setting(\"email_smtp_server\", settings.email_smtp_server)"),
    (r"save_setting\(\"email_smtp_port\", settings.email_smtp_port\)", "await save_setting(\"email_smtp_port\", settings.email_smtp_port)"),
    (r"save_setting\(\"email_sender\", settings.email_sender\)", "await save_setting(\"email_sender\", settings.email_sender)"),
    (r"save_setting\(\"email_password\", settings.email_password\)", "await save_setting(\"email_password\", settings.email_password)"),
    (r"save_setting\(\"email_recipient\", settings.email_recipient\)", "await save_setting(\"email_recipient\", settings.email_recipient)"),
    
    # get_transactions_route
    (r"def get_transactions_route\(portfolio_id: int\):", "async def get_transactions_route(portfolio_id: int):"),
    (r"return get_transactions\(portfolio_id\)", "return await get_transactions(portfolio_id)"),
    
    # add_transaction_route
    (r"def add_transaction_route\(portfolio_id: int, tx: TransactionRequest\):",
     "async def add_transaction_route(portfolio_id: int, tx: TransactionRequest):"),
    (r"success = add_transaction\(", "success = await add_transaction("),
    
    # delete_transaction_route
    (r"def delete_transaction_route\(portfolio_id: int, tx_id: int\):",
     "async def delete_transaction_route(portfolio_id: int, tx_id: int):"),
    (r"success = delete_transaction\(tx_id, portfolio_id\)", "success = await delete_transaction(tx_id, portfolio_id)"),
    
    # Target allocations
    (r"alloc = get_target_allocation\(portfolio_id\)", "alloc = await get_target_allocation(portfolio_id)"),
    (r"success = save_target_allocation\(portfolio_id, alloc_dict\)", "success = await save_target_allocation(portfolio_id, alloc_dict)"),
    
    # Rebalance
    (r"target_alloc = get_target_allocation\(portfolio_id\)", "target_alloc = await get_target_allocation(portfolio_id)"),
    (r"holdings = get_portfolio_from_db\(portfolio_id\)", "holdings = await get_portfolio_from_db(portfolio_id)"),
    (r"predictions_data = \(get_predictions_from_db\(\)\)", "predictions_data = (await get_predictions_from_db())"),
    (r"advice = generate_rebalancing_advice\(portfolio_id, total_value, allocations, holdings_detail\)",
     "advice = await generate_rebalancing_advice(portfolio_id, total_value, allocations, holdings_detail)"),
     
    # get_prediction_accuracy
    (r"def get_prediction_accuracy\(\):", "async def get_prediction_accuracy():"),
    (r"conn = get_db_connection\(\)\s+cursor = conn.cursor\(\)", "conn = await get_db_connection()\n        cursor = await conn.cursor()"),
    (r"cursor\.execute\(\"\"\"", "await cursor.execute(\"\"\""),
    (r"rows = cursor\.fetchall\(\)", "rows = await cursor.fetchall()"),
    (r"conn\.close\(\)", "await conn.close()"),
    
    # handle_chat_query
    (r"def handle_chat_query\(req: ChatRequest, background_tasks: BackgroundTasks\):",
     "async def handle_chat_query(req: ChatRequest, background_tasks: BackgroundTasks):"),
    (r"add_chat_message\(portfolio_id, \"user\", msg\)", "await add_chat_message(portfolio_id, \"user\", msg)"),
    (r"add_transaction\(portfolio_id, symbol, 'BUY', qty, price, current_date\)",
     "await add_transaction(portfolio_id, symbol, 'BUY', qty, price, current_date)"),
    (r"add_chat_message\(portfolio_id, \"bot\", response_text\)", "await add_chat_message(portfolio_id, \"bot\", response_text)"),
    (r"holdings = get_portfolio_from_db\(portfolio_id\)", "holdings = await get_portfolio_from_db(portfolio_id)"),
    (r"predictions_data = get_predictions_from_db\(\)", "predictions_data = await get_predictions_from_db()"),
    (r"add_transaction\(portfolio_id, symbol, 'SELL', item\[\"quantity\"\], sell_price, current_date\)",
     "await add_transaction(portfolio_id, symbol, 'SELL', item[\"quantity\"], sell_price, current_date)"),
    (r"add_asset\(symbol, ticker_info\[\"name\"\], ticker_info\[\"type\"\]\)",
     "await add_asset(symbol, ticker_info[\"name\"], ticker_info[\"type\"])"),
    (r"delete_asset\(symbol\)", "await delete_asset(symbol)"),
    (r"predictions_data = get_predictions_from_db\(\).get\(\"predictions\", \{\}\)", 
     "predictions_data = (await get_predictions_from_db()).get(\"predictions\", {})"),
    (r"portfolio_data = get_portfolio_from_db\(portfolio_id\)", "portfolio_data = await get_portfolio_from_db(portfolio_id)"),
    (r"ai_response = generate_chat_response\(msg, portfolio_data, predictions_data, portfolio_id=portfolio_id\)",
     "ai_response = await generate_chat_response(msg, portfolio_data, predictions_data, portfolio_id=portfolio_id)"),
     
    # get_backtest_history
    (r"def get_backtest_history\(\):", "async def get_backtest_history():"),
    
    # get_alerts
    (r"def get_alerts\(\):", "async def get_alerts():"),
    (r"return get_all_alerts\(\)", "return await get_all_alerts()"),
    
    # create_new_alert
    (r"def create_new_alert\(alert: AlertRequest\):", "async def create_new_alert(alert: AlertRequest):"),
    (r"success = add_alert\(alert.symbol, alert.alert_type, alert.target_value\)",
     "success = await add_alert(alert.symbol, alert.alert_type, alert.target_value)"),
     
    # delete_alert_route
    (r"def delete_alert_route\(alert_id: int\):", "async def delete_alert_route(alert_id: int):"),
    (r"success = delete_alert\(alert_id\)", "success = await delete_alert(alert_id)"),
    
    # get_triggered_alerts_route
    (r"def get_triggered_alerts_route\(\):", "async def get_triggered_alerts_route():"),
    (r"return get_triggered_alerts\(\)", "return await get_triggered_alerts()"),
    
    # get_portfolio_dividends
    (r"def get_portfolio_dividends\(portfolio_id: int = 1\):", "async def get_portfolio_dividends(portfolio_id: int = 1):"),
    (r"holdings = get_portfolio_from_db\(portfolio_id\)", "holdings = await get_portfolio_from_db(portfolio_id)"),
    (r"predictions = get_predictions_from_db\(\).get\(\"predictions\", \{\}\)", 
     "predictions = (await get_predictions_from_db()).get(\"predictions\", {})"),
     
    # get_portfolio_chat_route
    (r"def get_portfolio_chat_route\(portfolio_id: int\):", "async def get_portfolio_chat_route(portfolio_id: int):"),
    (r"return get_chat_history\(portfolio_id\)", "return await get_chat_history(portfolio_id)"),
    
    # delete_portfolio_chat_route
    (r"def delete_portfolio_chat_route\(portfolio_id: int\):", "async def delete_portfolio_chat_route(portfolio_id: int):"),
    (r"success = clear_chat_history\(portfolio_id\)", "success = await clear_chat_history(portfolio_id)"),
    
    # Test routes
    (r"def test_telegram_route\(req: TestNotificationRequest\):", "async def test_telegram_route(req: TestNotificationRequest):"),
    (r"success = send_telegram_notification\(req.message\)", "success = await send_telegram_notification(req.message)"),
    
    (r"def test_discord_route\(req: TestNotificationRequest\):", "async def test_discord_route(req: TestNotificationRequest):"),
    (r"success = send_discord_notification\(req.message\)", "success = await send_discord_notification(req.message)"),
    
    (r"def test_email_route\(req: TestNotificationRequest\):", "async def test_email_route(req: TestNotificationRequest):"),
    (r"success = send_email_notification\(\"AlphaPulse AI Test E-Mail\", f\"<h3>Test</h3><p>\{req.message\}</p>\"\)",
     "success = await send_email_notification(\"AlphaPulse AI Test E-Mail\", f\"<h3>Test</h3><p>{req.message}</p>\")"),
]

for pat, repl in replacements:
    content, count = re.subn(pat, repl, content)
    print(f"Replaced {pat} -> {count} times")

# Double check any manual replacements that need special care:
# get_backtest_history connection
content = content.replace(
    '        conn = get_db_connection()\n        cursor = conn.cursor()',
    '        conn = await get_db_connection()\n        cursor = await conn.cursor()'
).replace(
    '        cursor.execute("""\n            SELECT h.symbol, h.price AS pred_price, h.recommendation, h.confidence, h.last_updated, p.name, p.price AS current_price',
    '        await cursor.execute("""\n            SELECT h.symbol, h.price AS pred_price, h.recommendation, h.confidence, h.last_updated, p.name, p.price AS current_price'
).replace(
    '        rows = cursor.fetchall()\n        conn.close()',
    '        rows = await cursor.fetchall()\n        await conn.close()'
)

with open(filepath, "w", encoding="utf-8") as f:
    f.write(content)

print("Finished modifying main.py")
