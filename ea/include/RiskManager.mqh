//+------------------------------------------------------------------+
//|                                                  RiskManager.mqh  |
//|       Risk controls: pending orders, circuit breakers, limits    |
//+------------------------------------------------------------------+
#property strict
#include "Common.mqh"
#include "Config.mqh"
#include "Logger.mqh"
#include "PositionManager.mqh"

//+------------------------------------------------------------------+
//| Module-level state for daily loss tracking                        |
//+------------------------------------------------------------------+
static double   s_dailyStartBalance = 0;
static double   s_dailyRealizedLoss = 0;
static datetime s_lastDailyReset    = 0;

//+------------------------------------------------------------------+
//| Module-level state for drawdown peak tracking                     |
//+------------------------------------------------------------------+
static double s_peakBalance = 0;

//+------------------------------------------------------------------+
//| Risk threshold input parameters (conservative defaults)           |
//| Per CONTEXT.md: agent chooses conservative starting values       |
//+------------------------------------------------------------------+
input double   InpMaxDrawdownPercent      = 20.0;   // RISK-02: max drawdown from peak balance before circuit breaker trips
input double   InpDailyLossCapPercent     = 5.0;    // RISK-03: max daily realized loss as % of starting balance
input int      InpMaxPositionsPerSymbol   = 1;      // RISK-04: max open positions per symbol
input double   InpMinMarginBufferPercent  = 150.0;  // RISK-05: position size must leave at least this % of required margin free

//+------------------------------------------------------------------+
//| Validate that order type is a pending order (DATA-07)             |
//+------------------------------------------------------------------+
bool IsPendingOrderType(ENUM_ORDER_TYPE orderType)
{
   return(orderType == ORDER_TYPE_BUY_LIMIT       ||
          orderType == ORDER_TYPE_SELL_LIMIT      ||
          orderType == ORDER_TYPE_BUY_STOP        ||
          orderType == ORDER_TYPE_SELL_STOP       ||
          orderType == ORDER_TYPE_BUY_STOP_LIMIT  ||
          orderType == ORDER_TYPE_SELL_STOP_LIMIT);
}

//+------------------------------------------------------------------+
//| Place a pending order (DATA-07: all 6 pending order types)        |
//| Supports: buy limit, sell limit, buy stop, sell stop,            |
//|           buy stop limit, sell stop limit                         |
//| SL and TP calculated per entry price and percentage.             |
//| Uses safe defaults from Config when percentages are zero.        |
//+------------------------------------------------------------------+
TradeResult PlacePendingOrder(string symbol, ENUM_ORDER_TYPE orderType,
                               double requestedPrice, double stopLimitPrice,
                               double volume, double slPercent = 0, double tpPercent = 0)
{
   TradeResult result;
   ZeroMemory(result);
   result.symbol    = symbol;
   result.timestamp = TimeCurrent();

   // Validate order type is a pending order
   if(!IsPendingOrderType(orderType))
   {
      result.retcode = -1;
      result.comment = "Invalid pending order type";
      LogError("PlacePendingOrder", -1, result.comment);
      return(result);
   }

   // Use safe defaults if SL/TP not provided (per AI-03)
   if(slPercent == 0) slPercent = InpSafeDefaultSLPercent;
   if(tpPercent == 0) tpPercent = InpSafeDefaultTPPercent;

   // Get current prices for SL/TP calculation
   double ask = SymbolInfoDouble(symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(symbol, SYMBOL_BID);
   if(ask == 0 || bid == 0)
   {
      result.retcode = -2;
      result.comment = "Failed to get symbol prices";
      LogError("PlacePendingOrder", -2, result.comment);
      return(result);
   }

   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

   // Determine order direction for SL/TP calculation
   bool isBuy = (orderType == ORDER_TYPE_BUY_LIMIT       ||
                 orderType == ORDER_TYPE_BUY_STOP         ||
                 orderType == ORDER_TYPE_BUY_STOP_LIMIT);

   double sl, tp;
   if(isBuy)
   {
      sl = NormalizeDouble(requestedPrice * (1.0 - slPercent / 100.0), digits);
      tp = NormalizeDouble(requestedPrice * (1.0 + tpPercent / 100.0), digits);
   }
   else
   {
      sl = NormalizeDouble(requestedPrice * (1.0 + slPercent / 100.0), digits);
      tp = NormalizeDouble(requestedPrice * (1.0 - tpPercent / 100.0), digits);
   }

   // Detect filling type (same pattern as OrderManager per DATA-04)
   long fillMode = SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
   ENUM_ORDER_TYPE_FILLING filling;
   if((fillMode & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
      filling = ORDER_FILLING_FOK;
   else if((fillMode & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
      filling = ORDER_FILLING_IOC;
   else
      filling = ORDER_FILLING_RETURN;

   // Build trade request
   MqlTradeRequest request;
   ZeroMemory(request);
   request.action       = TRADE_ACTION_PENDING;
   request.symbol       = symbol;
   request.volume       = NormalizeDouble(volume, 2);
   request.type         = orderType;
   request.price        = NormalizeDouble(requestedPrice, digits);
   request.sl           = sl;
   request.tp           = tp;
   request.deviation    = 20;
   request.magic        = InpMagicNumber;
   request.comment      = "Futra Pending";
   request.type_filling = filling;

   // Stop limit orders need stoplimit price
   if(orderType == ORDER_TYPE_BUY_STOP_LIMIT || orderType == ORDER_TYPE_SELL_STOP_LIMIT)
   {
      request.stoplimit = NormalizeDouble(stopLimitPrice, digits);
   }

   MqlTradeResult mqlResult;
   ZeroMemory(mqlResult);
   ResetLastError();
   bool success = OrderSend(request, mqlResult);

   result.ticket    = mqlResult.order;
   result.volume    = volume;
   result.price     = requestedPrice;
   result.sl        = sl;
   result.tp        = tp;
   result.type      = EnumToString(orderType);
   result.retcode   = mqlResult.retcode;
   result.comment   = mqlResult.comment;

    LogTradeOpen(result);

   if(!success || mqlResult.retcode != TRADE_RETCODE_DONE)
   {
      LogError("PlacePendingOrder", mqlResult.retcode, "OrderSend failed");
   }

   return(result);
}

//+------------------------------------------------------------------+
//| Drawdown Circuit Breaker (RISK-02)                                |
//| Halts trading when equity drops below InpMaxDrawdownPercent      |
//| from peak balance (high-water mark).                              |
//+------------------------------------------------------------------+
bool CheckDrawdownLimit()
{
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);

   // Update peak balance (high-water mark)
   if(balance > s_peakBalance)
      s_peakBalance = balance;

   if(s_peakBalance <= 0)
      return(true);  // No history — allow trading

   double drawdownPercent = ((s_peakBalance - equity) / s_peakBalance) * 100.0;

   if(drawdownPercent >= InpMaxDrawdownPercent)
   {
      string msg = StringFormat(
         "Drawdown circuit breaker: equity=%.2f peak=%.2f drawdown=%.2f%% limit=%.2f%%",
         equity, s_peakBalance, drawdownPercent, InpMaxDrawdownPercent);
      LogError("CheckDrawdownLimit", 0, msg);
      return(false);  // HALT — drawdown limit breached
   }
   return(true);
}

//+------------------------------------------------------------------+
//| Reset daily loss tracking to current balance                      |
//+------------------------------------------------------------------+
void ResetDailyLossTracking()
{
   s_dailyStartBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   s_dailyRealizedLoss = 0;
   s_lastDailyReset    = TimeCurrent();
   LogInfo(StringFormat("Daily loss tracking reset. Start balance: %.2f", s_dailyStartBalance));
}

//+------------------------------------------------------------------+
//| Daily Loss Cap (RISK-03)                                          |
//| Halts trading when realized losses exceed InpDailyLossCapPercent |
//| of the daily starting balance. Auto-resets at midnight.          |
//+------------------------------------------------------------------+
bool CheckDailyLossLimit()
{
   // Reset at midnight (new trading day)
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   MqlDateTime lastDt;
   TimeToStruct(s_lastDailyReset, lastDt);

   if(dt.day != lastDt.day || dt.mon != lastDt.mon || dt.year != lastDt.year)
      ResetDailyLossTracking();

   if(s_dailyStartBalance <= 0)
      ResetDailyLossTracking();

   double dailyLossPercent = 0;
   if(s_dailyStartBalance > 0)
      dailyLossPercent = (s_dailyRealizedLoss / s_dailyStartBalance) * 100.0;

   if(dailyLossPercent >= InpDailyLossCapPercent)
   {
      string msg = StringFormat(
         "Daily loss cap: loss=%.2f (%.2f%%) limit=%.2f%% balance_start=%.2f",
         s_dailyRealizedLoss, dailyLossPercent, InpDailyLossCapPercent, s_dailyStartBalance);
      LogError("CheckDailyLossLimit", 0, msg);
      return(false);  // HALT — daily loss cap reached
   }
   return(true);
}

//+------------------------------------------------------------------+
//| Record closed trade profit for daily loss tracking                |
//| Called by EA after each trade closes.                             |
//+------------------------------------------------------------------+
void RecordClosedTradeProfit(double profit)
{
   if(profit < 0)
      s_dailyRealizedLoss += MathAbs(profit);
}

//+------------------------------------------------------------------+
//| Max Positions Per Symbol (RISK-04)                                 |
//| Ensures no more than InpMaxPositionsPerSymbol open for a symbol.  |
//+------------------------------------------------------------------+
bool CheckMaxPositionsPerSymbol(string symbol)
{
   int count = 0;
   int total = PositionsTotal();

   for(int i = total - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;

      if(!PositionSelectByTicket(ticket)) continue;

      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;

      if(PositionGetString(POSITION_SYMBOL) != symbol)
         continue;

      count++;
   }

   if(count >= InpMaxPositionsPerSymbol)
   {
      LogInfo(StringFormat(
         "Max positions for %s: %d/%d — skipping new orders for this symbol",
         symbol, count, InpMaxPositionsPerSymbol));
      return(false);
   }
   return(true);
}

//+------------------------------------------------------------------+
//| Position Sizing Validation (RISK-05)                              |
//| Validates volume against max size, min volume, and margin        |
//| availability using order_calc_margin() with configurable buffer. |
//+------------------------------------------------------------------+
bool ValidatePositionSize(string symbol, double volume)
{
   // Clamp to configured max
   if(volume > InpMaxPositionSize)
   {
      LogError("ValidatePositionSize", 0, StringFormat(
         "Volume %.2f exceeds max %.2f for %s", volume, InpMaxPositionSize, symbol));
      return(false);
   }

   // Check minimum volume
   double minVol = SymbolInfoDouble(symbol, SYMBOL_VOLUME_MIN);
   if(volume < minVol)
   {
      LogError("ValidatePositionSize", 0, StringFormat(
         "Volume %.2f below min %.2f for %s", volume, minVol, symbol));
      return(false);
   }

   // Margin check using order_calc_margin() per RISK-05
   double marginRequired = 0;
   ResetLastError();
   if(!OrderCalcMargin(ORDER_TYPE_BUY, symbol, volume,
                        SymbolInfoDouble(symbol, SYMBOL_ASK), marginRequired))
   {
      LogError("ValidatePositionSize", GetLastError(),
               StringFormat("OrderCalcMargin failed for %s", symbol));
      return(false);
   }

   double freeMargin = AccountInfoDouble(ACCOUNT_MARGIN_FREE);
   double marginWithBuffer = marginRequired * (InpMinMarginBufferPercent / 100.0);

   if(marginWithBuffer > freeMargin)
   {
      LogError("ValidatePositionSize", 0, StringFormat(
         "Insufficient margin for %s: need=%.2f (with %.0f%% buffer=%.2f) free=%.2f",
         symbol, marginRequired, InpMinMarginBufferPercent, marginWithBuffer, freeMargin));
      return(false);
   }

   return(true);
}

//+------------------------------------------------------------------+
//| Master Risk Gate (called from EA OnTick before ANY order)         |
//| Gates execute in priority order:                                   |
//|   1. CheckDrawdownLimit       — circuit breaker first              |
//|   2. CheckDailyLossLimit      — daily loss cap                     |
//|   3. CheckMaxPositionsPerSymbol — position limits per symbol       |
//|   4. ValidatePositionSize     — margin-based sizing validation     |
//+------------------------------------------------------------------+
bool IsTradingAllowed(string symbol, double volume)
{
   // Gates execute in priority order — circuit breakers first
   if(!CheckDrawdownLimit())
      return(false);
   if(!CheckDailyLossLimit())
      return(false);
   if(!CheckMaxPositionsPerSymbol(symbol))
      return(false);
   if(!ValidatePositionSize(symbol, volume))
      return(false);
   return(true);
}
//+------------------------------------------------------------------+
