//+------------------------------------------------------------------+
//|                                                      FutraEA.mq5 |
//|                   Futra AI-Powered Trading Expert Advisor        |
//|                                       Version 1.0                |
//+------------------------------------------------------------------+
#property copyright "Futra Trading System"
#property link      "https://github.com/futra"
#property version   "1.0"

//+------------------------------------------------------------------+
//| Module includes                                                   |
//+------------------------------------------------------------------+
#include "include/Common.mqh"
#include "include/Config.mqh"
#include "include/Logger.mqh"
#include "include/KillSwitch.mqh"
#include "include/OrderManager.mqh"
#include "include/PositionManager.mqh"
#include "include/IPCReader.mqh"

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit()
{
   // Stub — module initialization wiring will be implemented in Task 3
   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   // Stub — cleanup wiring will be implemented in Task 3
}

//+------------------------------------------------------------------+
//| Expert tick function — called on every price tick                 |
//| Execution loop will be wired in Task 3:                           |
//|   1. CheckKillSwitch() — halt trading if kill switch active       |
//|   2. ReadSymbolParams() per symbol — check staleness              |
//|   3. Trading signal evaluation (placeholder for future phase)     |
//|   4. OpenBuyOrder/OpenSellOrder — execute trades with SL/TP       |
//+------------------------------------------------------------------+
void OnTick()
{
   // Stub — execution loop will be wired in Task 3
}
//+------------------------------------------------------------------+
