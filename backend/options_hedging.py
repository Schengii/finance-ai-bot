import math
import logging

logger = logging.getLogger(__name__)

def norm_cdf(x: float) -> float:
    """Kumulative Verteilungsfunktion der Standardnormalverteilung ohne Scipy."""
    return (1.0 + math.erf(x / math.sqrt(2.0))) / 2.0

def norm_pdf(x: float) -> float:
    """Wahrscheinlichkeitsdichte der Standardnormalverteilung ohne Scipy."""
    return math.exp(-0.5 * x * x) / math.sqrt(2.0 * math.pi)

def black_scholes(S: float, K: float, T: float, r: float, sigma: float, option_type: str = "call") -> dict:
    """
    Berechnet die Optionspreise und Griechen (Delta, Gamma, Vega, Theta) nach dem Black-Scholes-Modell.
    - S: Aktueller Aktienkurs
    - K: Basispreis (Strike Price)
    - T: Restlaufzeit in Jahren (z.B. 0.25 für 3 Monate)
    - r: Risikofreier Zinssatz (z.B. 0.03 für 3%)
    - sigma: Implizite / Historische Volatilität (z.B. 0.25 für 25%)
    - option_type: 'call' oder 'put'
    """
    if T <= 0 or sigma <= 0 or S <= 0 or K <= 0:
        return {
            "price": 0.0,
            "delta": 0.0,
            "gamma": 0.0,
            "vega": 0.0,
            "theta": 0.0
        }

    d1 = (math.log(S / K) + (r + 0.5 * sigma ** 2) * T) / (sigma * math.sqrt(T))
    d2 = d1 - sigma * math.sqrt(T)

    if option_type.lower() == "call":
        price = S * norm_cdf(d1) - K * math.exp(-r * T) * norm_cdf(d2)
        delta = norm_cdf(d1)
    else: # put
        price = K * math.exp(-r * T) * norm_cdf(-d2) - S * norm_cdf(-d1)
        delta = -norm_cdf(-d1)

    gamma = norm_pdf(d1) / (S * sigma * math.sqrt(T))
    vega = (S * norm_pdf(d1) * math.sqrt(T)) / 100.0 # pro 1% Volatilität
    
    if option_type.lower() == "call":
        theta = (- (S * norm_pdf(d1) * sigma) / (2 * math.sqrt(T)) - r * K * math.exp(-r * T) * norm_cdf(d2)) / 365.0
    else:
        theta = (- (S * norm_pdf(d1) * sigma) / (2 * math.sqrt(T)) + r * K * math.exp(-r * T) * norm_cdf(-d2)) / 365.0

    return {
        "price": round(float(price), 2),
        "delta": round(float(delta), 4),
        "gamma": round(float(gamma), 4),
        "vega": round(float(vega), 4),
        "theta": round(float(theta), 4)
    }


def generate_hedging_recommendations(portfolio_value: float, holdings: list, risk_tolerance: str = "Medium") -> dict:
    """
    Erstellt mathematisch fundierte Options-Hedging-Strategien zur Depotabsicherung gegen Crashes (> 10% Drawdown).
    """
    if portfolio_value <= 0 or not holdings:
        return {
            "portfolio_value": portfolio_value,
            "strategies": [],
            "summary": "Keine offenen Positionen zum Absichern vorhanden."
        }

    # Annahmen für Marktabsicherung
    r = 0.03 # 3% Zinssatz
    avg_vol = 0.22 # 22% Volatilität
    t_days = 90 # 3 Monate Laufzeit
    T = t_days / 365.0

    strategies = []

    # 1. Protective Put (Direkte Absicherung nach unten)
    strike_put = portfolio_value * 0.95 # 5% Out of the Money
    bs_put = black_scholes(portfolio_value, strike_put, T, r, avg_vol, option_type="put")
    cost_put = bs_put["price"]
    pct_cost_put = (cost_put / portfolio_value) * 100

    strategies.append({
        "name": "Protective Put (Depot-Vollversicherung)",
        "type": "protective_put",
        "description": "Kauf einer Put-Option auf 95% des Depotwerts. Garantiert maximale Verluste von 5% in den nächsten 90 Tagen.",
        "strike_price": round(strike_put, 2),
        "expiry_days": t_days,
        "estimated_cost": cost_put,
        "cost_percentage": round(pct_cost_put, 2),
        "greeks": {
            "delta": bs_put["delta"],
            "gamma": bs_put["gamma"],
            "vega": bs_put["vega"],
            "theta": bs_put["theta"]
        }
    })

    # 2. Covered Call Income (Stillhalter-Strategie zur Ertragsoptimierung)
    strike_call = portfolio_value * 1.08 # 8% Out of the Money
    bs_call = black_scholes(portfolio_value, strike_call, T, r, avg_vol, option_type="call")
    premium_received = bs_call["price"]
    pct_premium = (premium_received / portfolio_value) * 100

    strategies.append({
        "name": "Covered Call (Zusatz-Rendite / Puffer)",
        "type": "covered_call",
        "description": "Verkauf von Call-Optionen bei +8% Kursziel. Generiert sofortige Prämien-Einnahmen als Risikopuffer.",
        "strike_price": round(strike_call, 2),
        "expiry_days": t_days,
        "estimated_premium_received": premium_received,
        "premium_percentage": round(pct_premium, 2),
        "greeks": {
            "delta": bs_call["delta"],
            "gamma": bs_call["gamma"],
            "vega": bs_call["vega"],
            "theta": bs_call["theta"]
        }
    })

    # 3. Zero-Cost Collar (Kostenneutrale Absicherung)
    collar_cost = cost_put - premium_received
    strategies.append({
        "name": "Zero-Cost Collar (Kostenneutrale Absicherung)",
        "type": "collar",
        "description": "Kombination aus Protective Put (-5%) und Covered Call (+8%). Die Call-Prämie finanziert den Put-Schutz nahezu vollständig.",
        "net_cost": round(collar_cost, 2),
        "net_cost_percentage": round((collar_cost / portfolio_value) * 100, 2)
    })

    return {
        "portfolio_value": round(portfolio_value, 2),
        "strategies": strategies,
        "summary": f"Für ein Depotvolumen von {portfolio_value:.2f} € wird eine Zero-Cost Collar oder Protective Put Strategie zur Absicherung empfohlen."
    }
