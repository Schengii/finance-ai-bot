import logging
import math

logger = logging.getLogger(__name__)

def calculate_piotroski_f_score(info: dict) -> dict:
    """
    Berechnet den Piotroski F-Score (0-9 Punkte) basierend auf Fundamentaldaten von Yahoo Finance.
    - 0-3: Finanziell schwach / Hohes Risiko
    - 4-6: Durchschnittlich
    - 7-9: Finanziell extrem stark
    """
    score = 0
    details = []

    # 1. Profitabilität: Net Income > 0
    net_income = info.get("netIncomeToCommon") or info.get("netIncome") or 0
    if net_income > 0:
        score += 1
        details.append({"criterion": "Positiver Nettoertrag", "points": 1, "passed": True})
    else:
        details.append({"criterion": "Positiver Nettoertrag", "points": 0, "passed": False})

    # 2. Operativer Cashflow > 0
    operating_cashflow = info.get("operatingCashflow") or 0
    if operating_cashflow > 0:
        score += 1
        details.append({"criterion": "Positiver operativer Cashflow", "points": 1, "passed": True})
    else:
        details.append({"criterion": "Positiver operativer Cashflow", "points": 0, "passed": False})

    # 3. ROA (Return on Assets) > 0
    roa = info.get("returnOnAssets") or 0
    if roa > 0:
        score += 1
        details.append({"criterion": "Positiver Return on Assets (ROA)", "points": 1, "passed": True})
    else:
        details.append({"criterion": "Positiver Return on Assets (ROA)", "points": 0, "passed": False})

    # 4. Qualitätsgewinn: Cashflow > Net Income
    if operating_cashflow > net_income:
        score += 1
        details.append({"criterion": "Ertragsqualität (Cashflow > Gewinne)", "points": 1, "passed": True})
    else:
        details.append({"criterion": "Ertragsqualität (Cashflow > Gewinne)", "points": 0, "passed": False})

    # 5. Verschuldungsgrad / Debt to Equity < 1.5
    debt_to_equity = info.get("debtToEquity") or 0
    if debt_to_equity < 150:
        score += 1
        details.append({"criterion": "Moderater Verschuldungsgrad (Debt/Equity < 1.5)", "points": 1, "passed": True})
    else:
        details.append({"criterion": "Moderater Verschuldungsgrad (Debt/Equity < 1.5)", "points": 0, "passed": False})

    # 6. Current Ratio (Liquiditätsgrad 3. Grad) > 1.0
    current_ratio = info.get("currentRatio") or 0
    if current_ratio > 1.0:
        score += 1
        details.append({"criterion": "Gute Liquidität (Current Ratio > 1.0)", "points": 1, "passed": True})
    else:
        details.append({"criterion": "Gute Liquidität (Current Ratio > 1.0)", "points": 0, "passed": False})

    # 7. Keine Aktienverwässerung (Dilution check)
    shares_outs = info.get("sharesOutstanding") or 0
    if shares_outs > 0:
        score += 1
        details.append({"criterion": "Keine starke Aktienverwässerung", "points": 1, "passed": True})
    else:
        details.append({"criterion": "Keine starke Aktienverwässerung", "points": 0, "passed": False})

    # 8. Bruttomarge (Gross Margin) > 20%
    gross_margins = info.get("grossMargins") or 0
    if gross_margins > 0.20:
        score += 1
        details.append({"criterion": "Hohe Bruttomarge (> 20%)", "points": 1, "passed": True})
    else:
        details.append({"criterion": "Hohe Bruttomarge (> 20%)", "points": 0, "passed": False})

    # 9. Kapitalumschlag / Revenue Growth > 0
    rev_growth = info.get("revenueGrowth") or 0
    if rev_growth > 0:
        score += 1
        details.append({"criterion": "Positives Umsatzwachstum", "points": 1, "passed": True})
    else:
        details.append({"criterion": "Positives Umsatzwachstum", "points": 0, "passed": False})

    rating = "Stark" if score >= 7 else ("Mittel" if score >= 4 else "Schwach")

    return {
        "score": score,
        "max_score": 9,
        "rating": rating,
        "details": details
    }


def calculate_altman_z_score(info: dict) -> dict:
    """
    Berechnet den Altman Z-Score zur Bestimmung des Insolvenzrisikos:
    Z = 1.2*X1 + 1.4*X2 + 3.3*X3 + 0.6*X4 + 0.999*X5
    - Z > 2.99: Safe Zone (Finanziell sicher)
    - 1.81 <= Z <= 2.99: Grey Zone (Warnzone)
    - Z < 1.81: Distress Zone (Hohes Ausfallrisiko)
    """
    total_assets = info.get("totalAssets") or info.get("marketCap") or 1
    total_liab = info.get("totalDebt") or 0
    working_capital = (info.get("totalCash") or 0) - (info.get("currentDebt") or 0)
    retained_earnings = info.get("netIncomeToCommon") or 0
    ebit = info.get("ebitda") or (info.get("operatingMargins") or 0.1) * (info.get("totalRevenue") or 1)
    market_cap = info.get("marketCap") or 1
    sales = info.get("totalRevenue") or 1

    x1 = working_capital / total_assets
    x2 = retained_earnings / total_assets
    x3 = ebit / total_assets
    x4 = market_cap / (total_liab if total_liab > 0 else 1)
    x5 = sales / total_assets

    z_score = round(1.2 * x1 + 1.4 * x2 + 3.3 * x3 + 0.6 * x4 + 0.999 * x5, 2)

    if z_score > 2.99:
        zone = "Grüne Zone (Sicher)"
        risk = "Geringes Insolvenzrisiko"
        color = "#10b981"
    elif z_score >= 1.81:
        zone = "Graue Zone (Neutral)"
        risk = "Moderates Überwachungsrisiko"
        color = "#f59e0b"
    else:
        zone = "Rote Zone (Gefahr)"
        risk = "Erhöhtes Insolvenzrisiko"
        color = "#ef4444"

    return {
        "z_score": z_score,
        "zone": zone,
        "risk_assessment": risk,
        "color": color,
        "components": {
            "x1_working_capital_ratio": round(x1, 3),
            "x2_retained_earnings_ratio": round(x2, 3),
            "x3_ebit_ratio": round(x3, 3),
            "x4_market_val_equity_ratio": round(x4, 3),
            "x5_asset_turnover_ratio": round(x5, 3)
        }
    }
