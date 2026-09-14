import asyncio
from typing import Any, Callable, Dict, List, Type
import logging

logger = logging.getLogger("flux_events")


class DomainEvent:
    pass


EventHandler = Callable[[Any], Any]


class EventBus:
    """
    Lightweight in-process asynchronous domain event bus.
    Allows services to publish domain events without tight coupling.
    """
    def __init__(self):
        self._subscribers: Dict[Type[DomainEvent], List[EventHandler]] = {}

    def subscribe(self, event_type: Type[DomainEvent], handler: EventHandler) -> None:
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    async def publish(self, event: DomainEvent) -> None:
        event_type = type(event)
        handlers = self._subscribers.get(event_type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
            except Exception as e:
                logger.error(f"Error handling event {event_type.__name__} in {handler.__name__}: {e}")


event_bus = EventBus()
