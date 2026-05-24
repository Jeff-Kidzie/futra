//+------------------------------------------------------------------+
//|                                                      Logger.mqh  |
//|           Trade and error logging to JSONL file on disk          |
//+------------------------------------------------------------------+
#property strict
#include "Common.mqh"

//+------------------------------------------------------------------+
//| Build an ISO8601-style timestamp string from TimeCurrent()       |
//| MT5 doesn't natively do ISO8601, so we construct it manually.    |
//+------------------------------------------------------------------+
string GetCurrentTimestamp()
{
   datetime t = TimeCurrent();
   string datePart = TimeToString(t, TIME_DATE);    // yyyy.mm.dd
   string timePart = TimeToString(t, TIME_SECONDS); // hh:mm:ss
   // Convert MQL5 date format "yyyy.mm.dd" to "yyyy-mm-dd"
   StringReplace(datePart, ".", "-");
   return(StringFormat("%sT%sZ", datePart, timePart));
}

//+------------------------------------------------------------------+
//| Append a TradeResult as a JSON line to trade_log.jsonl           |
//| Manual JSON construction — MQL5 has no native JSON library.      |
//| On FileOpen failure, outputs to Print() only (no crash).         |
//+------------------------------------------------------------------+
void LogTrade(TradeResult &result)
{
   string timestamp = GetCurrentTimestamp();
   string jsonLine = StringFormat(
      "{\"ticket\":%I64u,\"symbol\":\"%s\",\"type\":\"%s\","
      "\"volume\":%.2f,\"price\":%.5f,\"sl\":%.5f,\"tp\":%.5f,"
      "\"retcode\":%d,\"comment\":\"%s\",\"timestamp\":\"%s\"}",
      result.ticket, result.symbol, result.type,
      result.volume, result.price, result.sl, result.tp,
      result.retcode, result.comment, timestamp
   );

   // TRADE_LOG_FILE already includes "Futra/" prefix
   ResetLastError();
   int handle = FileOpen(TRADE_LOG_FILE, FILE_TXT|FILE_READ|FILE_WRITE|FILE_SHARE_READ);

   if(handle == INVALID_HANDLE)
   {
      Print("LogTrade: FileOpen failed for ", TRADE_LOG_FILE,
            ", error: ", GetLastError(),
            " | Trade: ticket=", result.ticket,
            ", retcode=", result.retcode);
      return;
   }

   // Seek to end for append
   FileSeek(handle, 0, SEEK_END);
   FileWrite(handle, jsonLine);
   FileClose(handle);
}

//+------------------------------------------------------------------+
//| Log an error entry to the trade log (same file, JSONL)           |
//+------------------------------------------------------------------+
void LogError(string context, int errorCode, string details)
{
   string timestamp = GetCurrentTimestamp();
   string jsonLine = StringFormat(
      "{\"level\":\"error\",\"context\":\"%s\",\"errorCode\":%d,"
      "\"details\":\"%s\",\"timestamp\":\"%s\"}",
      context, errorCode, details, timestamp
   );

   // TRADE_LOG_FILE already includes "Futra/" prefix
   ResetLastError();
   int handle = FileOpen(TRADE_LOG_FILE, FILE_TXT|FILE_READ|FILE_WRITE|FILE_SHARE_READ);

   if(handle == INVALID_HANDLE)
   {
      Print("LogError: FileOpen failed for ", TRADE_LOG_FILE,
            ", error: ", GetLastError(),
            " | ", context, ": ", details);
      return;
   }

   FileSeek(handle, 0, SEEK_END);
   FileWrite(handle, jsonLine);
   FileClose(handle);
}

//+------------------------------------------------------------------+
//| Log an informational message to the trade log                    |
//+------------------------------------------------------------------+
void LogInfo(string message)
{
   string timestamp = GetCurrentTimestamp();
   string jsonLine = StringFormat(
      "{\"level\":\"info\",\"message\":\"%s\",\"timestamp\":\"%s\"}",
      message, timestamp
   );

   // TRADE_LOG_FILE already includes "Futra/" prefix
   ResetLastError();
   int handle = FileOpen(TRADE_LOG_FILE, FILE_TXT|FILE_READ|FILE_WRITE|FILE_SHARE_READ);

   if(handle == INVALID_HANDLE)
   {
      Print("LogInfo: FileOpen failed for ", TRADE_LOG_FILE,
            ", error: ", GetLastError(),
            " | ", message);
      return;
   }

   FileSeek(handle, 0, SEEK_END);
   FileWrite(handle, jsonLine);
   FileClose(handle);
}
//+------------------------------------------------------------------+
