# PyWhy Project Memory

## Code Standards

### Event Data Format
- **Always use data dictionary format**: `event.data = {'var_name': 'x', 'value': 10}`
- **Never use legacy args tuple format**: Legacy format has been removed
- **Always use EventType enum**: `event.event_type == EventType.ASSIGN`
- **Never use string comparisons**: ~~`event.event_type == "assign"`~~

### No Backward Compatibility
- Do not implement backward compatibility code for old event formats
- Use only one consistent data structure throughout the codebase
- Remove any legacy format support when encountered

## Testing
- Test assertion helpers should only expect the current data dictionary format
- All event type comparisons must use EventType enum values
- Event data access should use `event.data.get('key')` pattern

## Current Architecture
- **Instrumenter**: Creates events with data dictionary format
- **Tracer**: Records events with EventType enum values  
- **DSL**: Builds events using consistent data dictionary format
- **Tests**: Assert against data dictionary format only