"""
Utilities for analyzing and matching trace events.
Provides tools for filtering, counting, and validating trace event sequences.
"""
from typing import List
from .instrumenter import TraceEvent, EventType


class EventMatcher:
    """Utility for matching and validating trace events"""
    
    @staticmethod
    def has_event_type(events: List[TraceEvent], event_type: EventType) -> bool:
        """Check if events contain a specific event type"""
        return any(event.event_type == event_type.value for event in events)
        
    @staticmethod
    def count_event_type(events: List[TraceEvent], event_type: EventType) -> int:
        """Count events of a specific type"""
        return sum(1 for event in events if event.event_type == event_type.value)
        
    @staticmethod
    def find_events(events: List[TraceEvent], **filters) -> List[TraceEvent]:
        """Find events matching the given filters"""
        matches = []
        for event in events:
            match = True
            for key, value in filters.items():
                if key == 'event_type':
                    if event.event_type != value:
                        match = False
                        break
                elif key in event.data:
                    if event.data[key] != value:
                        match = False
                        break
                else:
                    match = False
                    break
            if match:
                matches.append(event)
        return matches
        
    @staticmethod
    def assert_sequence(events: List[TraceEvent], expected_types: List[EventType]) -> bool:
        """Assert that events follow the expected sequence of types"""
        if len(events) != len(expected_types):
            return False
        return all(
            event.event_type == expected.value 
            for event, expected in zip(events, expected_types)
        )