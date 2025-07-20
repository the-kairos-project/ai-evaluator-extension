# Help System

This folder contains the tooltip and guided help system for the AI Evaluator extension.

## File Structure

- **`helpContent.ts`** - All help text content (easy to edit without touching component logic)
- **`HelpSystem.tsx`** - React components for tooltips and guided help UI
- **`index.ts`** - Clean exports for importing the help system

## Updating Help Content

To update tooltip text, examples, or best practices:

1. **Edit only `helpContent.ts`**
2. **No need to touch component files**
3. **Content is organized by field type** (applicantTable, sourceField, etc.)

## Content Structure

Each help item has:
- `purpose` - Main explanation of what the field does
- `setup` - Instructions for configuration  
- `examples` - Real-world example values
- `bestPractices` - Tips for optimal usage
- `consequences` - Important warnings about effects

## Adding New Fields

1. Add new entry to `HELP_CONTENT` in `helpContent.ts`
2. Use the field key in `FormFieldWithTooltip` component
3. Tooltip positioning will be handled automatically

## Tooltip Positioning

- **Regular fields**: Appear below and to the left
- **Bottom fields** (`applicantField`, `logsField`): Appear above and to the left (avoids overflow)
- **Smart positioning**: Adapts based on field type automatically 