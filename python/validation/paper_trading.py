"""Paper trading — runs the AI engine on a schedule against an MT5 demo account.

Paper trading is NOT a simulation. It runs the EXACT same AI pipeline as
production but on an MT5 demo account where the EA executes real orders
with virtual money.

Requirements:
- MT5 running and logged into a demo account
- FutraEA attached to charts on that MT5 instance
- IPC_DIR configured to point to that MT5's MQL5/Files/Futra/ directory
- AI engine configured with appropriate symbols and timeframe

Per BACK-05: Forward-testing without real capital.
"""
import logging
import time
from pathlib import Path
from typing import Optional

from ..config import PAPER_TRADING_INTERVAL_SECONDS

logger = logging.getLogger(__name__)


class PaperTrader:
    """Schedules AI engine evaluation on a demo MT5 account.
    
    The AI engine (from Phase 2) writes per-symbol IPC params files.
    The EA (from Phase 1) reads those files and executes trades.
    PaperTrader is just the scheduler — it tells the engine to run periodically.
    """
    
    def __init__(
        self,
        engine=None,  # AIEngine instance (from python.ai.engine)
        symbols: list[str] | None = None,
        interval_seconds: int = PAPER_TRADING_INTERVAL_SECONDS,
    ):
        """Initialize the paper trader.
        
        Args:
            engine: AIEngine instance. If None, must be set before calling run_cycle().
            symbols: Trading symbols. If None, uses engine.symbols.
            interval_seconds: Seconds between evaluation cycles (default: 3600 = 1 hour)
        """
        self.engine = engine
        self.symbols = symbols or (engine.symbols if engine else [])
        self.interval_seconds = interval_seconds
        self._running = False
        self._cycle_count = 0
    
    def run_cycle(self) -> list[dict]:
        """Run one evaluation cycle across all symbols.
        
        Delegates to AIEngine.run_once() which:
        1. Fetches latest OHLCV data via MT5 Python API
        2. Computes features for each symbol
        3. Detects regime and adapts parameters
        4. Writes IPC params files ({SYMBOL}_params.json)
        5. Returns list of evaluation results
        
        The EA reads the params files and executes trades on the demo account.
        
        Returns:
            List of result dicts from AIEngine.evaluate_symbol().
            Empty list if no symbols or engine is None.
        
        Raises:
            ValueError: If engine is None (caller must provide an engine)
        """
        if self.engine is None:
            raise ValueError("PaperTrader has no AIEngine. Set engine before calling run_cycle().")
        
        logger.info(f"Paper trading cycle {self._cycle_count + 1} starting...")
        
        try:
            results = self.engine.run_once()
            self._cycle_count += 1
            
            # Summary
            successes = [r for r in results if r is not None]
            failures = len(results) - len(successes)
            
            logger.info(
                f"Paper trading cycle {self._cycle_count} complete: "
                f"{len(successes)} symbols evaluated, {failures} skipped/failed"
            )
            
            for r in successes:
                logger.info(
                    f"  {r['symbol']}: regime={r['regime']} "
                    f"conf={r.get('confidence', 'N/A')} "
                    f"sl={r['adapted']['sl_pips']}pips "
                    f"tp={r['adapted']['tp_pips']}pips "
                    f"lot={r['adapted']['lot_size']}"
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Paper trading cycle failed: {e}", exc_info=True)
            return []
    
    def start(self):
        """Start the paper trading loop. Runs indefinitely until stopped.
        
        Call stop() to halt the loop, or use KeyboardInterrupt (Ctrl+C).
        """
        if self.engine is None:
            raise ValueError("PaperTrader has no AIEngine. Set engine before calling start().")
        
        self._running = True
        logger.info(
            f"Paper trading started: {len(self.symbols)} symbols, "
            f"interval={self.interval_seconds}s"
        )
        
        try:
            while self._running:
                self.run_cycle()
                
                if self._running:
                    logger.debug(f"Sleeping {self.interval_seconds}s until next cycle...")
                    time.sleep(self.interval_seconds)
                    
        except KeyboardInterrupt:
            logger.info("Paper trading stopped by user (KeyboardInterrupt)")
            self._running = False
        except Exception as e:
            logger.error(f"Paper trading loop error: {e}", exc_info=True)
            self._running = False
        
        logger.info(f"Paper trading stopped after {self._cycle_count} cycles")
    
    def stop(self):
        """Stop the paper trading loop gracefully."""
        self._running = False
        logger.info("PaperTrader stop requested")
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    @property
    def cycle_count(self) -> int:
        return self._cycle_count
