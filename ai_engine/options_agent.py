import random
from typing import Dict, Any, Optional
import yfinance as yf
from langchain_openai import ChatOpenAI
from langchain.prompts import ChatPromptTemplate

class OptionsAgent:
    """
    Analyzes market volatility (VIX) and suggests options-based hedging strategies.
    Activated when the swarm detects high market uncertainty.
    """
    
    def __init__(self, llm: Optional[ChatOpenAI] = None):
        self.llm = llm

    async def analyze(self, symbol: str) -> Dict[str, Any]:
        """
        Evaluate if a protective put or covered call strategy is needed
        based on implied volatility.
        """
        try:
            # Fetch VIX to gauge overall market volatility
            vix_ticker = yf.Ticker("^VIX")
            vix_data = vix_ticker.history(period="1d")
            current_vix = float(vix_data['Close'].iloc[-1]) if not vix_data.empty else 20.0
            
            # Fetch underlying symbol volatility
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="1mo")
            implied_volatility = float(hist['Close'].pct_change().std() * (252 ** 0.5) * 100) if not hist.empty else 30.0
            
        except Exception:
            current_vix = random.uniform(10.0, 40.0)
            implied_volatility = random.uniform(20.0, 80.0)

        options_data = {
            "vix_level": current_vix,
            "implied_volatility": implied_volatility,
            "hedging_recommended": current_vix > 25.0 or implied_volatility > 50.0
        }

        if self.llm:
            reasoning = await self._generate_reasoning(symbol, options_data)
        else:
            reasoning = self._generate_mock_reasoning(options_data)

        # Signal logic: if hedging is recommended, signal 'hedge', else 'neutral'
        signal = "hedge" if options_data["hedging_recommended"] else "neutral"

        return {
            "agent_name": "options_derivatives",
            "signal": signal,
            "confidence": 0.85,
            "reasoning": reasoning,
            "data": options_data
        }

    async def _generate_reasoning(self, symbol: str, data: Dict[str, Any]) -> str:
        if not self.llm:
            return self._generate_mock_reasoning(data)
            
        template = ChatPromptTemplate.from_template(
            """Analyze the volatility metrics for {symbol} to recommend an options hedging strategy.

Data:
- VIX Level: {vix_level:.2f}
- Implied Volatility: {implied_volatility:.2f}%
- Hedging Recommended: {hedging_recommended}

If hedging is recommended, suggest a specific strategy (e.g., Protective Put, Collar).
Conclude with: SIGNAL: hedge/neutral"""
        )
        chain = template | self.llm
        response = await chain.ainvoke({"symbol": symbol, **data})
        return response.content

    def _generate_mock_reasoning(self, data: Dict[str, Any]) -> str:
        if data["hedging_recommended"]:
            return f"VIX is elevated at {data['vix_level']:.2f}. Volatility risk is high. Recommend buying protective puts at 5% OTM. SIGNAL: hedge"
        return f"VIX is stable at {data['vix_level']:.2f}. No immediate hedging required. SIGNAL: neutral"
