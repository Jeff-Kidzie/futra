//+------------------------------------------------------------------+
//|                                                  KillSwitch.mqh  |
//|    File-based kill switch — polled every tick from EA OnTick     |
//+------------------------------------------------------------------+
#property strict
#include "Common.mqh"
#include "Config.mqh"
#include "Logger.mqh"

//+------------------------------------------------------------------+
//| Module-level static state (persists across OnTick calls)          |
//+------------------------------------------------------------------+
static bool     s_killSwitchActive       = false;
static bool     s_closePositions         = false;
static datetime s_killSwitchActivatedAt  = 0;
static datetime s_lastKillSwitchCheck    = 0;

//+------------------------------------------------------------------+
//| Poll the kill_switch.json file and return the EA state.          |
//| Called every tick from EA OnTick. Rate-limited to 500ms.         |
//| Per D-01, D-02, D-04: file-based signal with close_positions     |
//| flag and auto-reset timeout.                                     |
//+------------------------------------------------------------------+
ENUM_KILL_SWITCH_STATE CheckKillSwitch()
{
   // Rate-limit file I/O to at most once every 500ms
   datetime now = TimeCurrent();
   if(now - s_lastKillSwitchCheck < 1)
   {
      // Within rate-limit window — return cached state
      if(s_killSwitchActive)
      {
         return(s_closePositions ? KS_ACTIVE_CLOSE_ALL : KS_ACTIVE_NO_CLOSE);
      }
      return(KS_INACTIVE);
   }
   s_lastKillSwitchCheck = now;

   // Check for auto-reset timeout (per D-04)
   if(s_killSwitchActive)
   {
      int elapsedMinutes = (int)((now - s_killSwitchActivatedAt) / 60);
      if(elapsedMinutes >= InpKillSwitchTimeoutMinutes)
      {
         // Timeout exceeded — auto-reset to inactive
         s_killSwitchActive = false;
         s_closePositions = false;
         s_killSwitchActivatedAt = 0;
         LogInfo("Kill switch auto-reset after timeout");
         return(KS_INACTIVE);
      }
   }

   // Try to open the kill switch file
   ResetLastError();
   int handle = FileOpen(KILL_SWITCH_FILE, FILE_TXT|FILE_READ|FILE_SHARE_READ);

   if(handle == INVALID_HANDLE)
   {
      // File doesn't exist or can't be read — treat as inactive
      // If kill switch was previously active, check timeout (above already handled)
      return(KS_INACTIVE);
   }

   // Read file content
   string fileContent = FileReadString(handle);
   FileClose(handle);

   // Manual JSON parsing — search for "active" and "close_positions" keys
   bool parseOk = false;
   bool activeVal = false;
   bool closePosVal = false;

   // Find "active" key
   int activePos = StringFind(fileContent, "\"active\"");
   if(activePos >= 0)
   {
      // Look for the value after the colon
      int colonPos = StringFind(fileContent, ":", activePos);
      if(colonPos >= 0)
      {
         // Skip whitespace after colon
         string afterColon = StringSubstr(fileContent, colonPos + 1);
         StringTrimLeft(afterColon);
         if(StringFind(afterColon, "true") == 0)
         {
            activeVal = true;
            parseOk = true;
         }
         else if(StringFind(afterColon, "false") == 0)
         {
            activeVal = false;
            parseOk = true;
         }
      }
   }

   // If we couldn't parse the "active" key, treat as inactive (safe default per AI-03)
   if(!parseOk)
   {
      LogError("CheckKillSwitch", 0,
               "Kill switch file parse error — cannot find 'active' key");
      return(KS_INACTIVE);
   }

   // Find "close_positions" key
   int closePos = StringFind(fileContent, "\"close_positions\"");
   if(closePos >= 0)
   {
      int colonPos = StringFind(fileContent, ":", closePos);
      if(colonPos >= 0)
      {
         string afterColon = StringSubstr(fileContent, colonPos + 1);
         StringTrimLeft(afterColon);
         if(StringFind(afterColon, "true") == 0)
            closePosVal = true;
      }
   }

   if(activeVal)
   {
      s_killSwitchActive = true;
      s_closePositions = closePosVal;
      s_killSwitchActivatedAt = now;
      LogInfo(StringFormat("Kill switch activated: close_positions=%s",
             closePosVal ? "true" : "false"));

      if(closePosVal)
      {
         return(KS_ACTIVE_CLOSE_ALL);
      }
      return(KS_ACTIVE_NO_CLOSE);
   }

   // active=false — treat as inactive, reset state
   s_killSwitchActive = false;
   s_closePositions = false;
   s_killSwitchActivatedAt = 0;
   return(KS_INACTIVE);
}

//+------------------------------------------------------------------+
//| Quick check: is the kill switch currently active?                 |
//| Used by other modules to gate trading without re-reading file.    |
//+------------------------------------------------------------------+
bool IsKillSwitchActive()
{
   return(s_killSwitchActive);
}

//+------------------------------------------------------------------+
//| Should positions be closed when kill switch is active?            |
//| Used by EA OnTick to decide whether to close all positions.       |
//+------------------------------------------------------------------+
bool ShouldClosePositions()
{
   return(s_closePositions);
}

//+------------------------------------------------------------------+
//| Manually reset the kill switch to inactive state.                 |
//| Used for testing or admin override.                               |
//+------------------------------------------------------------------+
void ResetKillSwitch()
{
   s_killSwitchActive = false;
   s_closePositions = false;
   s_killSwitchActivatedAt = 0;
   LogInfo("Kill switch manually reset");
}
//+------------------------------------------------------------------+
