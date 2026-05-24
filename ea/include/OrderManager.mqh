//+------------------------------------------------------------------+
//|                                                OrderManager.mqh  |
//|           Market order execution with SL/TP on every order        |
//+------------------------------------------------------------------+
#property strict
#include "Common.mqh"
#include "Config.mqh"
#include "Logger.mqh"

//+------------------------------------------------------------------+
//| Auto-detect supported order filling type for a symbol             |
//| Tries ORDER_FILLING_FOK first, then IOC, then RETURN (per DATA-04)|
//+------------------------------------------------------------------+
ENUM_ORDER_TYPE_FILLING DetectFillingMode(string symbol)
{
   long fillMode = SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);

   if((fillMode & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
      return(ORDER_FILLING_FOK);
   if((fillMode & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
      return(ORDER_FILLING_IOC);

   return(ORDER_FILLING_RETURN);
}

//+------------------------------------------------------------------+
//| Calculate normalized volume clamped to symbol min/max/step        |
//+------------------------------------------------------------------+
double GetDefaultVolume(string symbol)
{
   double vol = InpMaxPositionSize;

   double volMin  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   double volMax  = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MAX);
   double volStep = SymbolInfoDouble(symbol, SYMBOL_VOLUME_STEP);

   if(vol < volMin) vol = volMin;
   if(vol > volMax) vol = volMax;

   // Normalize to volume step
   int steps = (int)MathRound((vol - volMin) / volStep);
   vol = volMin + steps * volStep;

   return(vol);
}

//+------------------------------------------------------------------+
//| Open a market buy order with SL and TP (per DATA-04, DATA-05)     |
//| Falls back to safe defaults from Config when percentages are 0    |
//| (AI-03: hardcoded safe defaults when AI params unavailable)       |
//+------------------------------------------------------------------+
TradeResult OpenBuyOrder(string symbol, double volume, double slPercent = 0, double tpPercent = 0)
{
   TradeResult tradeResult;
   ZeroMemory(tradeResult);
   tradeResult.symbol = symbol;
   tradeResult.type = "buy";
   tradeResult.volume = volume;

   // Use safe defaults when AI percentages are zero (AI-03)
   if(slPercent == 0) slPercent = InpSafeDefaultSLPercent;
   if(tpPercent == 0) tpPercent = InpSafeDefaultTPPercent;

   // Get current ask price
   ResetLastError();
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   if(ask == 0)
   {
      tradeResult.retcode = -1;
      tradeResult.comment = "SymbolInfoDouble ASK failed";
      tradeResult.timestamp = TimeCurrent();
      LogError("OpenBuyOrder", GetLastError(), "SymbolInfoDouble ASK returned 0");
      return(tradeResult);
   }

   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

   // Calculate SL/TP
   double sl = NormalizeDouble(ask * (1.0 - slPercent / 100.0), digits);
   double tp = NormalizeDouble(ask * (1.0 + tpPercent / 100.0), digits);

   tradeResult.price = ask;
   tradeResult.sl = sl;
   tradeResult.tp = tp;

   // Build trade request
   MqlTradeRequest request;
   ZeroMemory(request);
   request.action    = TRADE_ACTION_DEAL;
   request.symbol    = symbol;
   request.volume    = volume;
   request.type      = ORDER_TYPE_BUY;
   request.price     = ask;
   request.sl        = sl;
   request.tp        = tp;
   request.deviation = 20;
   request.magic     = InpMagicNumber;
   request.comment   = "Futra";
   request.type_filling = DetectFillingMode(symbol);

   // Execute trade
   MqlTradeResult result;
   ZeroMemory(result);
   ResetLastError();
   bool success = OrderSend(request, result);

   tradeResult.ticket    = result.order;
   tradeResult.price     = result.price;
   tradeResult.retcode   = result.retcode;
   tradeResult.comment   = result.comment;
   tradeResult.timestamp = TimeCurrent();

   // Log every trade result (per DATA-08)
   LogTrade(tradeResult);

   if(!success || result.retcode != TRADE_RETCODE_DONE)
   {
      LogError("OpenBuyOrder", result.retcode, "OrderSend failed");
   }

   return(tradeResult);
}

//+------------------------------------------------------------------+
//| Open a market sell order with SL and TP (per DATA-04, DATA-05)    |
//| SL/TP are inverted for sell orders: SL above, TP below entry     |
//+------------------------------------------------------------------+
TradeResult OpenSellOrder(string symbol, double volume, double slPercent = 0, double tpPercent = 0)
{
   TradeResult tradeResult;
   ZeroMemory(tradeResult);
   tradeResult.symbol = symbol;
   tradeResult.type = "sell";
   tradeResult.volume = volume;

   // Use safe defaults when AI percentages are zero (AI-03)
   if(slPercent == 0) slPercent = InpSafeDefaultSLPercent;
   if(tpPercent == 0) tpPercent = InpSafeDefaultTPPercent;

   // Get current bid price
   ResetLastError();
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   if(bid == 0)
   {
      tradeResult.retcode = -1;
      tradeResult.comment = "SymbolInfoDouble BID failed";
      tradeResult.timestamp = TimeCurrent();
      LogError("OpenSellOrder", GetLastError(), "SymbolInfoDouble BID returned 0");
      return(tradeResult);
   }

   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

   // Calculate SL/TP (inverted for sell: SL above, TP below)
   double sl = NormalizeDouble(bid * (1.0 + slPercent / 100.0), digits);
   double tp = NormalizeDouble(bid * (1.0 - tpPercent / 100.0), digits);

   tradeResult.price = bid;
   tradeResult.sl = sl;
   tradeResult.tp = tp;

   // Build trade request
   MqlTradeRequest request;
   ZeroMemory(request);
   request.action    = TRADE_ACTION_DEAL;
   request.symbol    = symbol;
   request.volume    = volume;
   request.type      = ORDER_TYPE_SELL;
   request.price     = bid;
   request.sl        = sl;
   request.tp        = tp;
   request.deviation = 20;
   request.magic     = InpMagicNumber;
   request.comment   = "Futra";
   request.type_filling = DetectFillingMode(symbol);

   // Execute trade
   MqlTradeResult result;
   ZeroMemory(result);
   ResetLastError();
   bool success = OrderSend(request, result);

   tradeResult.ticket    = result.order;
   tradeResult.price     = result.price;
   tradeResult.retcode   = result.retcode;
   tradeResult.comment   = result.comment;
   tradeResult.timestamp = TimeCurrent();

   // Log every trade result (per DATA-08)
   LogTrade(tradeResult);

   if(!success || result.retcode != TRADE_RETCODE_DONE)
   {
      LogError("OpenSellOrder", result.retcode, "OrderSend failed");
   }

   return(tradeResult);
}
//+------------------------------------------------------------------+
