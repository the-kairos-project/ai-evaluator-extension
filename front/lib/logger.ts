export enum LogLevel { ERROR = 0, WARN = 1, INFO = 2, DEBUG = 3 }

// Adjust currentLevel as needed; consider exposing via config or environment
const currentLevel: LogLevel = LogLevel.DEBUG;

function logAt(level: LogLevel, ...args: any[]): void {
  if (level <= currentLevel) {
    switch (level) {
      case LogLevel.ERROR:
        console.error(...args);
        break;
      case LogLevel.WARN:
        console.warn(...args);
        break;
      case LogLevel.INFO:
        console.info(...args);
        break;
      case LogLevel.DEBUG:
        console.debug(...args);
        break;
    }
  }
}

export const Logger = {
  error: (...args: any[]): void => logAt(LogLevel.ERROR, ...args),
  warn:  (...args: any[]): void => logAt(LogLevel.WARN,  ...args),
  info:  (...args: any[]): void => logAt(LogLevel.INFO,  ...args),
  debug: (...args: any[]): void => logAt(LogLevel.DEBUG, ...args),
};