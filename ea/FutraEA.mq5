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
#include "include/RiskManager.mqh"

//+------------------------------------------------------------------+
//| Expert initialization function                                    |
//+------------------------------------------------------------------+
int OnInit()
{
   LogInfo("Futra EA initialized — version 1.0");

   // Initialize risk management state
   s_peakBalance = AccountInfoDouble(ACCOUNT_BALANCE);
   ResetDailyLossTracking();

   return(INIT_SUCCEEDED);
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                  |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   LogInfo(StringFormat("Futra EA shutting down, reason: %d", reason));
}

//+------------------------------------------------------------------+
//| Expert tick function — called on every price tick                 |
//| Execution loop:                                                   |
//|   1. CheckKillSwitch() — halt trading if kill switch active       |
//|   2. ReadSymbolParams() per symbol — check staleness              |
//|   3. IsTradingAllowed() — risk gate before any order execution    |
//|   4. Trading signal evaluation (placeholder for future phase)     |
//|   5. OpenBuyOrder/OpenSellOrder — execute trades with SL/TP       |
//+------------------------------------------------------------------+
void OnTick()
{
   // === STEP 1: Check kill switch every tick (per D-01) ===
   ENUM_KILL_SWITCH_STATE ks = CheckKillSwitch();

   // If kill switch requires closing all positions (per D-02)
   if(ShouldClosePositions())
   {
      int closed = CloseAllPositions();
      LogInfo(StringFormat("Kill switch: %d positions closed", closed));
      return;  // Halt trading after position close
   }

   // If kill switch active but not closing positions — halt new trades
   if(IsKillSwitchActive())
   {
      return;  // No new trades allowed while kill switch is active
   }

   // === STEP 2: Read per-symbol AI params with staleness check ===
   string symbolsList = InpSymbols;
   string symbols[];
   ushort separator = StringGetCharacter(",", 0);
   int symbolCount = StringSplit(symbolsList, separator, symbols);

   for(int i = 0; i < symbolCount; i++)
   {
      string sym = symbols[i];
      StringTrimLeft(sym);
      StringTrimRight(sym);
      if(sym == "") continue;

      SymbolParams params = ReadSymbolParams(sym);

      // === STEP 3: Determine parameters for this symbol ===
      double slPct, tpPct, posSize;

      if(IsParamsFresh(params))
      {
         // Use AI-tuned parameters from the IPC file
         slPct   = params.slPercent;
         tpPct   = params.tpPercent;
         posSize = params.maxPositionSize;
      }
      else
      {
         // Fall back to hardcoded safe defaults (per AI-03)
         slPct   = InpSafeDefaultSLPercent;
         tpPct   = InpSafeDefaultTPPercent;
         posSize = InpMaxPositionSize;
      }

      // === STEP 4: Risk gate — pre-trade risk checks before any order ===
      double volume = GetDefaultVolume(sym);
      if(!IsTradingAllowed(sym, volume))
         continue;  // Risk gate blocked — skip this symbol

      // === STEP 5: Trading signal determination ===
      // Trading signal logic will be implemented in a future phase.
      // The EA core is ready to execute when signals arrive.
      // Placeholder: for now, the EA monitors and logs but does not
      // autonomously place trades. Signal generation will be wired
      // when the AI layer produces trade signals via IPC.
   }
}
//+------------------------------------------------------------------+
