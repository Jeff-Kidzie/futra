//+------------------------------------------------------------------+
//|                                                     Common.mqh   |
//|                              Shared types, enums, and constants  |
//+------------------------------------------------------------------+
#property strict

//+------------------------------------------------------------------+
//| Kill switch state enumeration                                    |
//+------------------------------------------------------------------+
enum ENUM_KILL_SWITCH_STATE
{
   KS_INACTIVE,           // No kill switch active — trading allowed
   KS_ACTIVE_NO_CLOSE,    // Kill switch active — halt new trades, keep positions
   KS_ACTIVE_CLOSE_ALL    // Kill switch active — close all positions, then halt
};

//+------------------------------------------------------------------+
//| Trade direction enumeration                                      |
//+------------------------------------------------------------------+
enum ENUM_TRADE_DIRECTION
{
   TRADE_BUY,             // Long / buy direction
   TRADE_SELL             // Short / sell direction
};

//+------------------------------------------------------------------+
//| Trade result struct — logged after every OrderSend               |
//+------------------------------------------------------------------+
struct TradeResult
{
   ulong    ticket;       // Order ticket number
   string   symbol;       // Trading symbol (e.g., "EURUSD")
   string   type;         // "buy" or "sell"
   double   volume;       // Trade volume in lots
   double   price;        // Execution price
   double   sl;           // Stop-loss price
   double   tp;           // Take-profit price
   int      retcode;      // MT5 return code (10009 = TRADE_RETCODE_DONE)
   string   comment;      // Order comment / error description
   datetime timestamp;    // Time of trade execution
};

//+------------------------------------------------------------------+
//| Position info struct — used for position tracking                |
//+------------------------------------------------------------------+
struct PositionInfo
{
   ulong    ticket;       // Position ticket number
   string   symbol;       // Trading symbol
   int      type;         // POSITION_TYPE_BUY (0) or POSITION_TYPE_SELL (1)
   double   volume;       // Position volume in lots
   double   openPrice;    // Entry price
   double   sl;           // Current stop-loss
   double   tp;           // Current take-profit
   double   profit;       // Current floating profit
};

//+------------------------------------------------------------------+
//| IPC file path constants (relative to MQL5/Files/)                |
//+------------------------------------------------------------------+
#define IPC_DIRECTORY     "Futra/"
#define KILL_SWITCH_FILE  "Futra/kill_switch.json"
#define TRADE_LOG_FILE    "Futra/trade_log.jsonl"
#define EA_STATE_FILE     "Futra/ea_state.json"
//+------------------------------------------------------------------+
