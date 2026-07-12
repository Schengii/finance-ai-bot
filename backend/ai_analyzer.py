import os
import json
import logging
from backend.config import GEMINI_API_KEY
from backend.db import get_setting

logger = logging.getLogger(__name__)


# Try importing the new google-genai SDK first
try:
    # pyrefly: ignore [missing-import]
    from google import genai
    # pyrefly: ignore [missing-import]
    from google.genai import types
    HAS_NEW_GENAI = True
except ImportError:
    HAS_NEW_GENAI = False

# Fallback to the legacy google-generativeai SDK
try:
    # pyrefly: ignore [missing-import]
    import google.generativeai as legacy_genai
    HAS_LEGACY_GENAI = True
except ImportError:
    HAS_LEGACY_GENAI = False

# Initialize Client
client = None
if GEMINI_API_KEY:
    if HAS_NEW_GENAI:
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            logger.info("Gemini SDK (google-genai) erfolgreich mit API-Key initialisiert.")
        except Exception as e:
            logger.error(f"Fehler beim Initialisieren des neuen Gemini SDKs: {e}")
    elif HAS_LEGACY_GENAI:
        try:
            legacy_genai.configure(api_key=GEMINI_API_KEY)
            logger.info("Gemini SDK (google-generativeai, veraltet) mit API-Key konfiguriert.")
        except Exception as e:
            logger.error(f"Fehler beim Konfigurieren des veralteten Gemini SDKs: {e}")
else:
    logger.warning("Kein GEMINI_API_KEY in der Konfiguration gefunden. Der Bot läuft im Demo-Modus mit simulierten KI-Prognosen.")


def get_mock_prediction(asset_info, market_data):
    """Erstellt eine plausible simulierte Prognose für den Demo-Modus."""
    symbol = asset_info["symbol"]
    rsi = market_data.get("rsi", 50)
    change_7d = market_data.get("price_change_7d", 0)
    
    # Eine einfache Heuristik für Mock-Empfehlungen
    if rsi < 35:
        recommendation = "Starker Kauf"
        confidence = 82
        sentiment = 0.6
        risk = "Mittel"
        reason = f"Der RSI von {rsi} deutet darauf hin, dass {symbol} stark überverkauft ist. Es gibt eine gute technische Kaufgelegenheit für eine kurzfristige Erholung."
        drivers = ["Überverkaufter Zustand (RSI)", "Stabile fundamentale Unterstützung"]
        risks = ["Möglicher anhaltender Abwärtstrend"]
    elif rsi > 70:
        recommendation = "Verkauf"
        confidence = 75
        sentiment = -0.4
        risk = "Mittel"
        reason = f"Mit einem RSI von {rsi} befindet sich {symbol} im überkauften Bereich. Gewinnmitnahmen sind wahrscheinlich."
        drivers = ["Kurzfristiges Momentum stößt an Grenzen"]
        risks = ["Gefahr von Gewinnmitnahmen"]
    elif change_7d > 5:
        recommendation = "Kauf"
        confidence = 68
        sentiment = 0.5
        risk = "Hoch"
        reason = f"{symbol} zeigt einen starken Aufwärtstrend in der letzten Woche (+{change_7d}%). Das Momentum ist positiv, aber der Einstieg birgt durch den Anstieg leicht erhöhtes Risiko."
        drivers = ["Starkes wöchentliches Momentum", "Positive Marktstimmung"]
        risks = ["Gewinnmitnahmen nach starkem Lauf"]
    else:
        recommendation = "Halten"
        confidence = 60
        sentiment = 0.1
        risk = "Gering"
        reason = f"{symbol} konsolidiert sich derzeit auf aktuellem Niveau. Es gibt momentan keine klaren technischen oder nachrichtenbasierten Impulse für signifikante Bewegungen."
        drivers = ["Seitwärtsbewegung stabilisiert Kurs"]
        risks = ["Mangel an kurzfristigen Katalysatoren"]

    return {
        "symbol": symbol,
        "name": asset_info["name"],
        "type": asset_info["type"],
        "price": market_data["current_price"],
        "price_change_1d": market_data["price_change_1d"],
        "price_change_7d": market_data["price_change_7d"],
        "price_change_30d": market_data["price_change_30d"],
        "rsi": rsi,
        "technical_trend": market_data["technical_trend"],
        "recommendation": recommendation,
        "confidence": confidence,
        "sentiment_score": sentiment,
        "risk_level": risk,
        "ai_explanation": reason,
        "key_drivers": drivers,
        "key_risks": risks,
        "last_updated": market_data.get("last_updated", "")
    }

async def analyze_asset_with_ai(asset_info, market_data, news_items):
    """
    Analysiert Kurse, technische Indikatoren und Nachrichten mit Gemini 

    und liefert eine fundierte Anlageempfehlung.
    """
    symbol = asset_info["symbol"]
    name = asset_info["name"]
    
    # Falls kein API-Key hinterlegt oder kein SDK installiert ist, nutze Mock-Daten
    if not GEMINI_API_KEY or (not HAS_NEW_GENAI and not HAS_LEGACY_GENAI):
        prediction = get_mock_prediction(asset_info, market_data)
        return prediction

    logger.info(f"Führe KI-Analyse für {symbol} mit Gemini durch...")
    
    # Einstellungen aus der Datenbank laden
    custom_prompt = await get_setting('custom_prompt', '')
    ai_tone = await get_setting('ai_tone', 'professionell')
    
    # News für den Prompt aufbereiten
    news_text = ""
    for idx, item in enumerate(news_items[:5]):
        news_text += f"{idx+1}. Titel: {item['title']}\n   Quelle/Publisher: {item['publisher']}\n   Zusammenfassung: {item['summary']}\n\n"
        
    if not news_text:
        news_text = "Keine aktuellen Nachrichten verfügbar."

    prompt = f"""
Du bist ein professioneller Finanzanalyst und KI-Investment-Berater.
Deine Aufgabe ist es, die Marktlage und die Nachrichten zu folgender Aktie bzw. Kryptowährung zu bewerten.

NUTZER-EINSTELLUNGEN FÜR DEINEN STIL / DEINE TONALITÄT:
- Tonalität: {ai_tone}
- Spezifische Anweisungen / Fokus: {custom_prompt}

Name: {name} ({symbol})
Kategorie: {asset_info['type']}

AKTUELLE MARKTDATEN:
- Aktueller Preis: {market_data['current_price']}
- Kursänderung (1 Tag): {market_data['price_change_1d']}%
- Kursänderung (7 Tage): {market_data['price_change_7d']}%
- Kursänderung (30 Tage): {market_data['price_change_30d']}%

TECHNISCHE INDIKATOREN:
- Gleitender Durchschnitt 20 Tage (SMA 20): {market_data['sma_20']}
- Gleitender Durchschnitt 50 Tage (SMA 50): {market_data['sma_50']}
- Relativer Stärke Index (RSI 14): {market_data['rsi']} (Wert unter 30 ist überverkauft, über 70 überkauft)
- MACD Wert: {market_data['macd']} (Signal-Linie: {market_data['macd_signal']}, Historie: {market_data['macd_hist']})
- Technischer Trend-Typ: {market_data['technical_trend']}

AKTUELLE NACHRICHTEN & THEMEN:
{news_text}

Analysiere die Daten und erstelle eine fundierte Prognose unter Berücksichtigung der gewünschten Tonalität ({ai_tone}) und der spezifischen Anweisungen.
Deine Antwort MUSS ein gültiges JSON-Objekt sein. Antworte AUSSCHLIESSLICH mit diesem JSON-Objekt. Verwende genau folgendes Schema:

{{
  "recommendation": "Starker Kauf" | "Kauf" | "Halten" | "Verkauf" | "Starker Verkauf",
  "confidence": <Zahl zwischen 0 und 100, wie sicher du dir bei der Prognose bist>,
  "sentiment_score": <Zahl zwischen -1.0 (extrem negativ) und 1.0 (extrem positiv) für die Nachrichtenstimmung>,
  "risk_level": "Gering" | "Mittel" | "Hoch" | "Sehr Hoch",
  "ai_explanation": "<Eine detaillierte, verständliche Erklärung auf Deutsch, warum du diese Empfehlung gibst (mindestens 3-4 Sätze). Antworte in der gewünschten Tonalität und berücksichtige die spezifischen Anweisungen. Gehe auf die News und die technischen Indikatoren ein.>",
  "key_drivers": ["Treiber 1", "Treiber 2", ...],
  "key_risks": ["Risiko 1", "Risiko 2", ...]
}}
"""

    try:
        if HAS_NEW_GENAI and client:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                )
            )
            response_text = response.text
        elif HAS_LEGACY_GENAI:
            model = legacy_genai.GenerativeModel("gemini-1.5-flash")
            
            generation_config = {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
            
            response = model.generate_content(prompt, generation_config=generation_config)
            response_text = response.text
        else:
            raise RuntimeError("Keine Gemini-Bibliothek installiert.")
            
        result_json = json.loads(response_text.strip())
        
        # Kombiniere KI-Antwort mit Marktdaten
        prediction = {
            "symbol": symbol,
            "name": name,
            "type": asset_info["type"],
            "price": market_data["current_price"],
            "price_change_1d": market_data["price_change_1d"],
            "price_change_7d": market_data["price_change_7d"],
            "price_change_30d": market_data["price_change_30d"],
            "rsi": market_data["rsi"],
            "technical_trend": market_data["technical_trend"],
            "recommendation": result_json.get("recommendation", "Halten"),
            "confidence": result_json.get("confidence", 50),
            "sentiment_score": result_json.get("sentiment_score", 0.0),
            "risk_level": result_json.get("risk_level", "Mittel"),
            "ai_explanation": result_json.get("ai_explanation", "Keine Erklärung verfügbar."),
            "key_drivers": result_json.get("key_drivers", []),
            "key_risks": result_json.get("key_risks", []),
            "last_updated": market_data.get("last_updated", "")
        }
        return prediction
        
    except Exception as e:
        logger.error(f"Fehler bei der Gemini-Analyse für {symbol}: {e}")
        # Nutze Fallback-Mockdaten, damit die App nicht abstürzt
        return get_mock_prediction(asset_info, market_data)


def generate_daily_summary(portfolio_data, predictions_data, strategy="Ausgewogen"):
    """Erstellt eine knappe Tageszusammenfassung für das Portfolio."""
    holdings = portfolio_data or []
    if not holdings:
        return {
            "headline": "Portfolio ist noch leer",
            "summary": "Füge erste Positionen hinzu, um eine tägliche Zusammenfassung zu erhalten.",
            "recommendations": [],
            "strategy": strategy,
        }

    total_value = 0.0
    total_cost = 0.0
    positives = []
    risks = []

    for holding in holdings:
        symbol = str(holding.get("symbol", "")).upper()
        quantity = float(holding.get("quantity", 0) or 0)
        buy_price = float(holding.get("buy_price", 0) or 0)
        pred = predictions_data.get(symbol, {}) if predictions_data else {}
        current_price = pred.get("price") or buy_price
        current_value = quantity * float(current_price)
        cost_value = quantity * buy_price
        total_value += current_value
        total_cost += cost_value

        recommendation = pred.get("recommendation", "Halten")
        if recommendation in ["Starker Kauf", "Kauf"]:
            positives.append(f"{symbol} wird aktuell positiv bewertet ({recommendation}).")
        elif recommendation in ["Verkauf", "Starker Verkauf"]:
            risks.append(f"{symbol} zeigt ein riskanteres Setup ({recommendation}).")

    pnl = total_value - total_cost
    pnl_pct = (pnl / total_cost * 100.0) if total_cost else 0.0
    headline = "Portfolio verhalten sich stabil" if pnl >= 0 else "Portfolio braucht Aufmerksamkeit"
    summary = (
        f"Dein {strategy}-Portfolio hat aktuell einen geschätzten Wert von {total_value:,.2f} und einen {pnl_pct:+.1f}% "
        f"{'Gewinn' if pnl >= 0 else 'Verlust'} gegenüber den Anschaffungskosten."
    )
    if positives:
        summary += " Starke Positionen: " + " ".join(positives[:2])
    if risks:
        summary += " Risiken: " + " ".join(risks[:2])

    recommendations = []
    if positives:
        recommendations.append("Schau dir die positiven Positionen im Detail an und prüfe, ob zusätzliche Skalierung sinnvoll ist.")
    if risks:
        recommendations.append("Reduziere im Zweifel das Risiko bei schwachen Positionen und halte Liquidität für neue Chancen bereit.")
    if not recommendations:
        recommendations.append("Die aktuelle Verteilung scheint ausgewogen. Beobachte die Marktbewegungen im Tagesverlauf.")

    return {
        "headline": headline,
        "summary": summary,
        "recommendations": recommendations,
        "strategy": strategy,
    }


async def generate_chat_response(query, portfolio_data, predictions_data, portfolio_id=1):
    """Generiert eine Antwort auf eine Nutzerfrage basierend auf Portfolio, Prognosen und Chatverlauf."""
    
    if not GEMINI_API_KEY or (not HAS_NEW_GENAI and not HAS_LEGACY_GENAI):
        # Fallback Mock responses for Demo-Modus
        q_lower = query.lower()
        if "portfol" in q_lower or "bestand" in q_lower or "invest" in q_lower:
            return (
                "**Demo-Modus:** Dein Portfolio sieht gut diversifiziert aus. "
                "Für eine höhere Rendite könntest du überlegen, den Anteil von Technologie-Werten leicht zu erhöhen. "
                "Wenn du deine Strategie defensiver ausrichten willst, sind Rohstoffe wie Gold eine Überlegung wert. "
                "\n\n*Hinweis: Dies ist eine simulierte Antwort im Demo-Modus. Richte einen Gemini API-Key ein, um echte KI-Antworten zu erhalten.*"
            )
        for symbol in predictions_data.keys():
            if symbol.lower() in q_lower:
                pred = predictions_data[symbol]
                return (
                    f"**Demo-Modus:** Zur Aktie **{symbol}** ({pred['name']}) liegt aktuell eine Empfehlung von **{pred['recommendation']}** vor. "
                    f"Die Konfidenz beträgt {pred['confidence']}% bei einer {pred['risk_level']}en Risikostufe. "
                    f"Die KI begründet dies wie folgt: \"{pred['ai_explanation']}\""
                )
        return (
            "**Demo-Modus:** Hallo! Ich bin dein AlphaPulse KI-Assistent. Ich kann deine Fragen zu deinem Portfolio "
            "und deiner Watchlist beantworten. Richte einen Gemini API-Key in deiner `.env` ein, um echte Gespräche zu führen!"
        )

    # Context construction
    portfolio_str = ""
    if portfolio_data:
        portfolio_str = "Portfolio des Nutzers (Aktuelle Bestände):\n"
        for item in portfolio_data:
            portfolio_str += f"- Ticker: {item['symbol']}, Menge: {item['quantity']}, Kaufpreis: {item['buy_price']}€\n"
    else:
        portfolio_str = "Der Nutzer hat aktuell keine Assets im Portfolio.\n"
        
    predictions_str = "Überwachte Assets (Watchlist) & KI-Analysen:\n"
    for symbol, pred in predictions_data.items():
        predictions_str += (
            f"- Ticker: {symbol} ({pred['name']})\n"
            f"  Aktueller Preis: {pred['price']}€\n"
            f"  Empfehlung: {pred['recommendation']} (Konfidenz: {pred['confidence']}%)\n"
            f"  Risikostufe: {pred['risk_level']}, Sentiment: {pred['sentiment_score']}\n"
            f"  KI-Begründung: {pred['ai_explanation']}\n"
        )
        
    # Chatverlauf aus DB laden
    from backend.db import get_chat_history
    history = await get_chat_history(portfolio_id)
    history_str = ""
    if history:
        history_str = "Bisheriger Chatverlauf:\n"
        # Nimm die letzten 8 Nachrichten für den Kontext (ohne die allerletzte, die ist die aktuelle Frage)
        context_msgs = history[-9:-1] if len(history) > 1 else []
        for msg in context_msgs:
            role = "Nutzer" if msg["sender"] == "user" else "KI"
            history_str += f"{role}: {msg['message']}\n"
        history_str += "\n"

    # Einstellungen aus der Datenbank laden
    custom_prompt = await get_setting('custom_prompt', '')
    ai_tone = await get_setting('ai_tone', 'professionell')

    prompt = f"""Du bist "AlphaPulse AI", ein hochentwickelter KI-Finanzberater. 

NUTZER-EINSTELLUNGEN FÜR DEINEN STIL / DEINE TONALITÄT:
- Tonalität: {ai_tone}
- Spezifische Anweisungen / Fokus: {custom_prompt}

Deine Aufgabe ist es, Fragen des Nutzers kompetent, sachlich, freundlich und auf Deutsch zu beantworten unter Berücksichtigung der gewünschten Tonalität ({ai_tone}) und Anweisungen.
Du hast Zugriff auf die folgenden aktuellen Daten des Nutzers:

{portfolio_str}

{predictions_str}

{history_str}

Beantworte die folgende Frage des Nutzers präzise, hilfreich und in der gewünschten Tonalität. Falls der Nutzer nach Finanzberatung fragt, füge am Ende deiner Antwort einen kurzen rechtlichen Hinweis hinzu, dass dies keine professionelle Anlageberatung ist.

Nutzerfrage: "{query}"
Antwort:"""

    try:
        if HAS_NEW_GENAI and client:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            return response.text.strip()
        elif HAS_LEGACY_GENAI:
            model = legacy_genai.GenerativeModel("gemini-1.5-flash")
            response = model.generate_content(prompt)
            return response.text.strip()
        else:
            return "Demo-Modus: Ich kann dir im Demo-Modus leider keine echten KI-Antworten geben. Bitte trage einen GEMINI_API_KEY in deiner .env Datei ein!"
    except Exception as e:
        logger.error(f"Fehler bei Generierung der Chat-Antwort: {e}")
        return f"Entschuldigung, bei der Verarbeitung deiner Frage ist ein Fehler aufgetreten: {str(e)}"


def get_mock_rebalancing_advice(total_value, allocations, holdings_detail):
    """Generiert programmatische Rebalancing-Vorschläge und Erklärung für den Demo-Modus oder Fallback."""
    proposals = []
    overweighted = []
    underweighted = []
    
    # Identifiziere Über- und Untergewichtungen
    for cat, data in allocations.items():
        diff_val = data["difference_value"]
        diff_pct = data["difference_percentage"]
        if diff_val > 5.0: # Über 5 EUR Abweichung
            overweighted.append((cat, diff_val, diff_pct))
        elif diff_val < -5.0:
            underweighted.append((cat, abs(diff_val), diff_pct))
            
    # Vorschläge für Verkäufe generieren (Umschichtung von Übergewichteten)
    for cat, diff_val, diff_pct in overweighted:
        cat_holdings = [h for h in holdings_detail if h["type"] == cat]
        if not cat_holdings:
            continue
        
        # Sortiere nach Empfehlung (Verkauf zuerst) oder Name
        cat_holdings.sort(key=lambda x: 0 if x.get("recommendation") in ["Verkauf", "Starker Verkauf"] else 1)
        
        # Verteile den Verkaufsbetrag auf die Holdings dieser Kategorie
        remaining_to_sell = diff_val
        for h in cat_holdings:
            if remaining_to_sell <= 1.0:
                break
            h_val = h["quantity"] * h["current_price"]
            sell_val = min(remaining_to_sell, h_val)
            sell_qty = sell_val / h["current_price"]
            
            proposals.append({
                "type": "SELL",
                "symbol": h["symbol"],
                "value": round(sell_val, 2),
                "quantity": round(sell_qty, 4),
                "reason": f"Kategorie '{cat}' ist übergewichtet (+{diff_pct:.1f}%). Reduzierung des Bestands um {sell_val:.2f} € zur Gewinnmitnahme."
            })
            remaining_to_sell -= sell_val

    # Vorschläge für Käufe generieren (Umschichtung in Untergewichtete)
    # Standard-Symbole für Kategorien, falls keine Holdings vorhanden sind
    default_symbols = {
        "stock": "AAPL",
        "crypto": "BTC-USD",
        "commodity": "GC=F"
    }
    
    for cat, diff_val, diff_pct in underweighted:
        cat_holdings = [h for h in holdings_detail if h["type"] == cat]
        
        if not cat_holdings:
            # Schlage Kauf eines Standard-Assets vor
            symbol = default_symbols.get(cat, "AAPL")
            price = 100.0 # fallback
            if symbol == "BTC-USD": price = 65000.0
            elif symbol == "GC=F": price = 2300.0
            
            buy_qty = diff_val / price
            proposals.append({
                "type": "BUY",
                "symbol": symbol,
                "value": round(diff_val, 2),
                "quantity": round(buy_qty, 4),
                "reason": f"Kategorie '{cat}' ist untergewichtet ({diff_pct:.1f}%). Aufbau einer Einstiegsposition in {symbol} empfohlen."
            })
        else:
            # Bevorzuge Assets mit Kaufempfehlung
            cat_holdings.sort(key=lambda x: 0 if x.get("recommendation") in ["Kauf", "Starker Kauf"] else 1)
            buy_val_per_asset = diff_val / len(cat_holdings)
            for h in cat_holdings:
                buy_qty = buy_val_per_asset / h["current_price"]
                proposals.append({
                    "type": "BUY",
                    "symbol": h["symbol"],
                    "value": round(buy_val_per_asset, 2),
                    "quantity": round(buy_qty, 4),
                    "reason": f"Kategorie '{cat}' ist untergewichtet ({diff_pct:.1f}%). Aufstockung von {h['symbol']} zur Wiederherstellung der Allokation."
                })

    # Erzeuge deutsche Erklärung
    explanation_parts = ["**Automatisches Portfolio-Rebalancing:**\n"]
    if not proposals:
        explanation_parts.append("Ihr Portfolio entspricht derzeit genau der gewünschten Ziel-Allokation. Es sind keine Anpassungen erforderlich.")
    else:
        explanation_parts.append("Um Ihre Ziel-Allokation wiederherzustellen, empfiehlt der Rebalancing Advisor folgende Umschichtungen:\n")
        for cat, diff_val, diff_pct in overweighted:
            explanation_parts.append(f"- **{cat.capitalize()}** ist um **{diff_pct:.1f}%** ({diff_val:.2f} €) überrepräsentiert. Gewinne sollten hier realisiert werden.")
        for cat, diff_val, diff_pct in underweighted:
            explanation_parts.append(f"- **{cat.capitalize()}** ist um **{diff_pct:.1f}%** ({diff_val:.2f} €) unterrepräsentiert. Hier sollte gezielt nachgekauft werden.")
            
        explanation_parts.append("\n*Hinweis: Dies ist eine algorithmisch generierte Empfehlung, da entweder kein Gemini API-Schlüssel konfiguriert ist oder die KI-Analyse nicht erreichbar war.*")

    return {
        "proposals": proposals,
        "ai_explanation": "\n".join(explanation_parts)
    }


async def generate_rebalancing_advice(portfolio_id, total_value, allocations, holdings_detail):
    """Generiert KI-gestützte Rebalancing-Vorschläge basierend auf Abweichungen und Prognosen."""
    # Falls kein API-Key oder genai SDK, nutze Mock-Fallback
    if not GEMINI_API_KEY or (not HAS_NEW_GENAI and not HAS_LEGACY_GENAI):
        return get_mock_rebalancing_advice(total_value, allocations, holdings_detail)
        
    # Baue Kontext für den Prompt
    allocations_str = ""
    for cat, data in allocations.items():
        allocations_str += (
            f"- Kategorie '{cat}': Ist-Wert: {data['current_value']:.2f} € ({data['current_percentage']:.1f}%), "
            f"Soll-Wert: {data['target_percentage']:.1f}%, Abweichung: {data['difference_percentage']:.1f}% "
            f"({data['difference_value']:.2f} €)\n"
        )
        
    holdings_str = ""
    for h in holdings_detail:
        holdings_str += (
            f"- Ticker: {h['symbol']} ({h['name']}), Kategorie: {h['type']}\n"
            f"  Bestand: {h['quantity']} x {h['current_price']:.2f} € = {h['quantity']*h['current_price']:.2f} €\n"
            f"  KI-Prognose/Empfehlung: {h.get('recommendation', 'N/A')}, RSI: {h.get('rsi', 'N/A')}, Trend: {h.get('technical_trend', 'N/A')}\n"
        )
        
    custom_prompt = await get_setting('custom_prompt', '')
    ai_tone = await get_setting('ai_tone', 'professionell')
    
    prompt = f"""
Du bist ein erstklassiger KI-Investment-Berater. Deine Aufgabe ist es, dem Nutzer beim Rebalancing seines Portfolios zu helfen.
Der Nutzer möchte eine bestimmte Zielallokation einhalten.

NUTZER-EINSTELLUNGEN FÜR DEINEN STIL / DEINE TONALITÄT:
- Tonalität: {ai_tone}
- Spezifische Anweisungen: {custom_prompt}

GESAMTWERT DES PORTFOLIOS: {total_value:.2f} €

ALLOKATIONS-ABWEICHUNGEN:
{allocations_str}

AKTUELLER PORTFOLIO-BESTAND & KI-ANALYSEN:
{holdings_str}

Deine Analyse soll konkrete Kauf- und Verkaufsvorschläge generieren, um die Zielallokationen wiederherzustellen.
- Verkaufe vorzugsweise Anteile von überbewerteten Kategorien (Abweichung > 0) und insbesondere von Assets mit neutralen oder negativen Prognosen ("Verkauf", "Halten").
- Kaufe vorzugsweise Anteile für unterbewertete Kategorien (Abweichung < 0) und insbesondere von Assets mit positiven Prognosen ("Kauf", "Starker Kauf").
- Falls in einer unterbewerteten Kategorie noch kein Asset existiert, schlage ein passendes Asset (z. B. BTC für Krypto, AAPL für Aktien, Gold GC=F für Rohstoffe) vor.

Deine Antwort MUSS ein gültiges JSON-Objekt sein. Antworte AUSSCHLIESSLICH mit diesem JSON-Objekt. Verwende genau folgendes Schema:

{{
  "proposals": [
    {{
      "type": "BUY" | "SELL",
      "symbol": "SYMBOL",
      "value": <Betrag in EUR, z. B. 150.50>,
      "quantity": <Menge des Assets als Kommazahl, z. B. 2.5>,
      "reason": "<Grund für diesen Umschichtungsvorschlag auf Deutsch unter Berücksichtigung von Prognosen/RSI/Trends.>"
    }},
    ...
  ],
  "ai_explanation": "<Detaillierter Rebalancing-Report auf Deutsch, der die Umschichtungen begründet, Marktchancen aufzeigt und dem Nutzer die nächsten Schritte erklärt. Verwende die gewünschte Tonalität ({ai_tone}) und beachte die spezifischen Anweisungen.>"
}}
"""

    try:
        if HAS_NEW_GENAI and client:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.2,
                )
            )
            response_text = response.text
        elif HAS_LEGACY_GENAI:
            model = legacy_genai.GenerativeModel("gemini-1.5-flash")
            generation_config = {
                "response_mime_type": "application/json",
                "temperature": 0.2
            }
            response = model.generate_content(prompt, generation_config=generation_config)
            response_text = response.text
        else:
            raise RuntimeError("Kein Gemini SDK vorhanden.")
            
        return json.loads(response_text.strip())
    except Exception as e:
        logger.error(f"Fehler bei der Generierung der KI-Rebalancing-Empfehlung: {e}")
        return get_mock_rebalancing_advice(total_value, allocations, holdings_detail)
