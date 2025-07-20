# SPAR AI Evaluator - Development Guidelines

## Important Guidelines for Claude
- NEVER commit changes without explicit permission
- Always run type-checking and linting before submitting changes
- Explain significant performance optimizations
- Break large changes into smaller logical commits

## Commands
- Build/run: `bun run start` or `bun run start:applications`
- Deploy: `bun run deploy`
- Type checking: `bun run type-check`
- Linting: `bun run lint`
- Tests: `bun run test`
- Single test: `bun run jest -t "test name pattern"`

## Code Style
- TypeScript with React functional components
- 2-space indentation
- Semicolons required
- Single quotes for strings
- PascalCase for components, interfaces, types
- camelCase for variables, functions, properties
- Explicit type annotations for parameters and returns
- Use React.FC typing for components
- Props interfaces defined near component usage
- Organize imports: external packages first, then internal

## Error Handling
- Use try/catch blocks with specific error messages
- Implement retries with pRetry for network operations
- Log errors with descriptive context

## Documentation
- JSDoc for functions
- Inline comments for complex logic
- TODO comments for planned improvements

## Architecture
- Frontend/ contains React components (UI layer)
- Lib/ contains business logic and API integrations