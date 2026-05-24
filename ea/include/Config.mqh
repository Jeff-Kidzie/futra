//+------------------------------------------------------------------+
//|                                                      Config.mqh  |
//|            Hardcoded safe default parameters for the EA          |
//+------------------------------------------------------------------+
#property strict
#include "Common.mqh"

//+------------------------------------------------------------------+
//| Safe default parameters — used when AI parameters are unavailable|
//| Per AI-03: EA must continue trading with hardcoded safe defaults |
//| when the AI layer is offline or params files are missing/stale.  |
//+------------------------------------------------------------------+

// Default stop-loss as percentage of entry price (2.0 = 2%)
input double   InpSafeDefaultSLPercent = 2.0;

// Default take-profit as percentage of entry price (4.0 = 4%)
input double   InpSafeDefaultTPPercent = 4.0;

// Maximum position size in lots per trade
input double   InpMaxPositionSize = 0.1;

// Kill switch auto-reset timeout in minutes (per D-04)
input int      InpKillSwitchTimeoutMinutes = 30;

// Maximum age of params files before considered stale (per D-06)
input int      InpParamsStalenessSeconds = 60;

// Comma-separated list of trading symbols
input string   InpSymbols = "EURUSD,GBPUSD,USDJPY";

// Unique magic number to identify orders placed by this EA
input int      InpMagicNumber = 20260501;
//+------------------------------------------------------------------+
