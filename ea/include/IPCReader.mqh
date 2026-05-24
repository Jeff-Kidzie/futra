//+------------------------------------------------------------------+
//|                                                  IPCReader.mqh   |
//|        Read per-symbol AI params files with staleness check       |
//+------------------------------------------------------------------+
#property strict
#include "Common.mqh"
#include "Config.mqh"

//+------------------------------------------------------------------+
//| Per-symbol parameters read from {SYMBOL}_params.json              |
//+------------------------------------------------------------------+
struct SymbolParams
{
   string   symbol;            // Trading symbol (e.g., "EURUSD")
   datetime timestamp;         // File timestamp (for staleness check)
   double   slPercent;         // Stop-loss as % of entry price
   double   tpPercent;         // Take-profit as % of entry price
   double   maxPositionSize;   // Maximum lot size for this symbol
   string   regime;            // Market regime classification
   double   confidence;        // AI confidence score (0.0 - 1.0)
   bool     isFresh;           // True if timestamp within staleness window
};

//+------------------------------------------------------------------+
//| Per-symbol read cache to avoid re-reading on every tick           |
//+------------------------------------------------------------------+
static SymbolParams s_cachedParams[20];   // Up to 20 symbols
static string       s_cachedSymbols[20];  // Symbol names for cache lookup
static datetime     s_lastReadTime[20];   // Last read time per symbol
static int          s_cacheCount = 0;     // Number of cached symbols

//+------------------------------------------------------------------+
//| Find a symbol's index in the cache, or -1 if not cached           |
//+------------------------------------------------------------------+
int FindCacheIndex(string symbol)
{
   for(int i = 0; i < s_cacheCount; i++)
   {
      if(s_cachedSymbols[i] == symbol)
         return(i);
   }
   return(-1);
}

//+------------------------------------------------------------------+
//| Read per-symbol params file with staleness check (per D-06, D-08) |
//| Uses 1-second read throttle to avoid excessive file I/O.          |
//| Falls back to empty/isFresh=false when file missing or stale.      |
//+------------------------------------------------------------------+
SymbolParams ReadSymbolParams(string symbol)
{
   SymbolParams result;
   result.symbol = symbol;
   result.isFresh = false;
   result.slPercent = 0;
   result.tpPercent = 0;
   result.maxPositionSize = 0;
   result.regime = "";
   result.confidence = 0;

   // Check cache for 1-second throttle
   int cacheIdx = FindCacheIndex(symbol);
   if(cacheIdx >= 0)
   {
      if(TimeCurrent() - s_lastReadTime[cacheIdx] < 1)
      {
         return(s_cachedParams[cacheIdx]);
      }
   }

   // Build file path: Futra/{SYMBOL}_params.json
   string filePath = StringFormat("%s%s_params.json", IPC_DIRECTORY, symbol);

   ResetLastError();
   int handle = FileOpen(filePath, FILE_TXT|FILE_READ|FILE_SHARE_READ);

   if(handle == INVALID_HANDLE)
   {
      // File doesn't exist — caller falls back to Config defaults (AI-03)
      return(result);
   }

   // Read full file content
   string fileContent = FileReadString(handle);
   FileClose(handle);

   // Manual JSON parsing — extract known fields
   bool parseOk = false;

   // Parse "timestamp" field
   int tsPos = StringFind(fileContent, "\"timestamp\"");
   if(tsPos >= 0)
   {
      int colonPos = StringFind(fileContent, ":", tsPos);
      if(colonPos >= 0)
      {
         // Extract timestamp string between quotes after colon
         int quoteStart = StringFind(fileContent, "\"", colonPos + 1);
         if(quoteStart >= 0)
         {
            int quoteEnd = StringFind(fileContent, "\"", quoteStart + 1);
            if(quoteEnd >= 0)
            {
               string tsStr = StringSubstr(fileContent, quoteStart + 1,
                                           quoteEnd - quoteStart - 1);
               result.timestamp = StringToTime(tsStr);
               parseOk = true;
            }
         }
      }
   }

   if(!parseOk)
   {
      // Could not parse timestamp — treat as stale, fall back to defaults
      Print("IPCReader: failed to parse timestamp from ", filePath);
      return(result);
   }

   // Parse "sl_percent"
   int slPos = StringFind(fileContent, "\"sl_percent\"");
   if(slPos >= 0)
   {
      int colonPos = StringFind(fileContent, ":", slPos);
      if(colonPos >= 0)
      {
         string afterColon = StringSubstr(fileContent, colonPos + 1);
         StringTrimLeft(afterColon);
         result.slPercent = StringToDouble(afterColon);
      }
   }

   // Parse "tp_percent"
   int tpPos = StringFind(fileContent, "\"tp_percent\"");
   if(tpPos >= 0)
   {
      int colonPos = StringFind(fileContent, ":", tpPos);
      if(colonPos >= 0)
      {
         string afterColon = StringSubstr(fileContent, colonPos + 1);
         StringTrimLeft(afterColon);
         result.tpPercent = StringToDouble(afterColon);
      }
   }

   // Parse "max_position_size"
   int mpsPos = StringFind(fileContent, "\"max_position_size\"");
   if(mpsPos >= 0)
   {
      int colonPos = StringFind(fileContent, ":", mpsPos);
      if(colonPos >= 0)
      {
         string afterColon = StringSubstr(fileContent, colonPos + 1);
         StringTrimLeft(afterColon);
         result.maxPositionSize = StringToDouble(afterColon);
      }
   }

   // Parse "regime"
   int regPos = StringFind(fileContent, "\"regime\"");
   if(regPos >= 0)
   {
      int colonPos = StringFind(fileContent, ":", regPos);
      if(colonPos >= 0)
      {
         int quoteStart = StringFind(fileContent, "\"", colonPos + 1);
         if(quoteStart >= 0)
         {
            int quoteEnd = StringFind(fileContent, "\"", quoteStart + 1);
            if(quoteEnd >= 0)
            {
               result.regime = StringSubstr(fileContent, quoteStart + 1,
                                            quoteEnd - quoteStart - 1);
            }
         }
      }
   }

   // Parse "confidence"
   int confPos = StringFind(fileContent, "\"confidence\"");
   if(confPos >= 0)
   {
      int colonPos = StringFind(fileContent, ":", confPos);
      if(colonPos >= 0)
      {
         string afterColon = StringSubstr(fileContent, colonPos + 1);
         StringTrimLeft(afterColon);
         result.confidence = StringToDouble(afterColon);
      }
   }

   // Staleness check (per D-06)
   if(TimeCurrent() - result.timestamp > InpParamsStalenessSeconds)
   {
      result.isFresh = false;
   }
   else
   {
      result.isFresh = true;
   }

   // Update cache
   if(cacheIdx >= 0)
   {
      s_cachedParams[cacheIdx] = result;
      s_lastReadTime[cacheIdx] = TimeCurrent();
   }
   else if(s_cacheCount < 20)
   {
      s_cachedSymbols[s_cacheCount] = symbol;
      s_cachedParams[s_cacheCount] = result;
      s_lastReadTime[s_cacheCount] = TimeCurrent();
      s_cacheCount++;
   }

   return(result);
}

//+------------------------------------------------------------------+
//| Convenience: check if params are fresh (within staleness window)  |
//+------------------------------------------------------------------+
bool IsParamsFresh(SymbolParams &params)
{
   return(params.isFresh);
}
//+------------------------------------------------------------------+
