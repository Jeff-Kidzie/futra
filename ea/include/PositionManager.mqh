//+------------------------------------------------------------------+
//|                                             PositionManager.mqh  |
//|          Position management: close, close all, modify SL/TP      |
//+------------------------------------------------------------------+
#property strict
#include "Common.mqh"
#include "Config.mqh"
#include "Logger.mqh"

//+------------------------------------------------------------------+
//| Close a single position by ticket (per DATA-06)                   |
//+------------------------------------------------------------------+
bool ClosePosition(ulong ticket)
{
   if(!PositionSelectByTicket(ticket))
   {
      LogError("ClosePosition", 0,
               StringFormat("Position not found: ticket=%I64u", ticket));
      return(false);
   }

   string symbol   = PositionGetString(POSITION_SYMBOL);
   double volume   = PositionGetDouble(POSITION_VOLUME);
   long   posType  = PositionGetInteger(POSITION_TYPE);

   // Determine close order type (opposite of position)
   ENUM_ORDER_TYPE orderType;
   double closePrice;

   if(posType == POSITION_TYPE_BUY)
   {
      orderType  = ORDER_TYPE_SELL;
      closePrice = SymbolInfoDouble(symbol, SYMBOL_BID);
   }
   else
   {
      orderType  = ORDER_TYPE_BUY;
      closePrice = SymbolInfoDouble(symbol, SYMBOL_ASK);
   }

   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);
   closePrice = NormalizeDouble(closePrice, digits);

   MqlTradeRequest request;
   ZeroMemory(request);
   request.action    = TRADE_ACTION_DEAL;
   request.symbol    = symbol;
   request.volume    = volume;
   request.type      = orderType;
   request.position  = ticket;
   request.price     = closePrice;
   request.deviation = 20;
   request.comment   = "Futra close";

   // Auto-detect filling
   long fillMode = SymbolInfoInteger(symbol, SYMBOL_FILLING_MODE);
   if((fillMode & SYMBOL_FILLING_FOK) == SYMBOL_FILLING_FOK)
      request.type_filling = ORDER_FILLING_FOK;
   else if((fillMode & SYMBOL_FILLING_IOC) == SYMBOL_FILLING_IOC)
      request.type_filling = ORDER_FILLING_IOC;
   else
      request.type_filling = ORDER_FILLING_RETURN;

   MqlTradeResult result;
   ZeroMemory(result);
   ResetLastError();
   bool success = OrderSend(request, result);

   // Log the close as a trade result
   TradeResult logEntry;
   ZeroMemory(logEntry);
   logEntry.ticket    = result.order;
   logEntry.symbol    = symbol;
   logEntry.type      = (posType == POSITION_TYPE_BUY) ? "sell" : "buy";
   logEntry.volume    = volume;
   logEntry.price     = result.price;
   logEntry.sl        = 0;
   logEntry.tp        = 0;
   logEntry.retcode   = result.retcode;
   logEntry.comment   = "Position closed";
   logEntry.timestamp = TimeCurrent();
   LogTrade(logEntry);

   if(!success || result.retcode != TRADE_RETCODE_DONE)
   {
      LogError("ClosePosition", result.retcode,
               StringFormat("Failed to close position ticket=%I64u", ticket));
      return(false);
   }

   return(true);
}

//+------------------------------------------------------------------+
//| Close all positions matching the EA's magic number                |
//| Iterates in reverse to handle position array shifting.            |
//| Returns count of positions attempted to close.                    |
//+------------------------------------------------------------------+
int CloseAllPositions()
{
   int closed = 0;
   int total  = PositionsTotal();

   for(int i = total - 1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;

      if(!PositionSelectByTicket(ticket)) continue;

      // Only close positions opened by this EA
      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber)
         continue;

      ClosePosition(ticket);
      closed++;
   }

   return(closed);
}

//+------------------------------------------------------------------+
//| Modify SL/TP on an existing position (per DATA-06)                |
//+------------------------------------------------------------------+
bool ModifySLTP(ulong ticket, double newSL, double newTP)
{
   if(!PositionSelectByTicket(ticket))
   {
      LogError("ModifySLTP", 0,
               StringFormat("Position not found: ticket=%I64u", ticket));
      return(false);
   }

   string symbol = PositionGetString(POSITION_SYMBOL);
   int digits = (int)SymbolInfoInteger(symbol, SYMBOL_DIGITS);

   newSL = NormalizeDouble(newSL, digits);
   newTP = NormalizeDouble(newTP, digits);

   MqlTradeRequest request;
   ZeroMemory(request);
   request.action   = TRADE_ACTION_SLTP;
   request.symbol   = symbol;
   request.position = ticket;
   request.sl       = newSL;
   request.tp       = newTP;

   MqlTradeResult result;
   ZeroMemory(result);
   ResetLastError();
   bool success = OrderSend(request, result);

   // Log the modification
   TradeResult logEntry;
   ZeroMemory(logEntry);
   logEntry.ticket    = result.order;
   logEntry.symbol    = symbol;
   logEntry.type      = "modify";
   logEntry.volume    = 0;
   logEntry.price     = 0;
   logEntry.sl        = newSL;
   logEntry.tp        = newTP;
   logEntry.retcode   = result.retcode;
   logEntry.comment   = "SL/TP modified";
   logEntry.timestamp = TimeCurrent();
   LogTrade(logEntry);

   if(!success || result.retcode != TRADE_RETCODE_DONE)
   {
      LogError("ModifySLTP", result.retcode,
               StringFormat("Failed to modify SL/TP for ticket=%I64u", ticket));
      return(false);
   }

   return(true);
}

//+------------------------------------------------------------------+
//| Get all positions matching this EA's magic number                 |
//| Fills the provided array and sets count.                          |
//+------------------------------------------------------------------+
void GetPositions(PositionInfo &positions[], int &count)
{
   count = 0;
   int total = PositionsTotal();

   // First pass: count matching positions
   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;
      count++;
   }

   // Resize and fill
   ArrayResize(positions, count);
   int idx = 0;

   for(int i = 0; i < total; i++)
   {
      ulong ticket = PositionGetTicket(i);
      if(ticket == 0) continue;
      if(!PositionSelectByTicket(ticket)) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagicNumber) continue;

      positions[idx].ticket    = ticket;
      positions[idx].symbol    = PositionGetString(POSITION_SYMBOL);
      positions[idx].type      = (int)PositionGetInteger(POSITION_TYPE);
      positions[idx].volume    = PositionGetDouble(POSITION_VOLUME);
      positions[idx].openPrice = PositionGetDouble(POSITION_PRICE_OPEN);
      positions[idx].sl        = PositionGetDouble(POSITION_SL);
      positions[idx].tp        = PositionGetDouble(POSITION_TP);
      positions[idx].profit    = PositionGetDouble(POSITION_PROFIT);
      idx++;
   }
}
//+------------------------------------------------------------------+
