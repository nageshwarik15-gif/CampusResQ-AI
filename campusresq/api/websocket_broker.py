"""
WebSocket Real-Time Event Protocol Broker
Aliases centralized EventBus for API routing.
Conforms strictly to IEEE 1016-2009 SDD §7.2 and SRS §4.4.
"""

from ..events import event_bus as ws_broker

__all__ = ["ws_broker"]
