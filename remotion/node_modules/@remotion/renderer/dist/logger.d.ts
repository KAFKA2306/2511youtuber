import type { LogLevel } from './log-level';
export declare const INDENT_TOKEN: string;
export type LogOptions = {
    indent: boolean;
    logLevel: LogLevel;
};
type VerboseLogOptions = LogOptions & {
    tag?: string;
};
export declare const verboseTag: (str: string) => string;
export declare const secondverboseTag: (str: string) => string;
export declare const Log: {
    formatLogs: (logLevel: LogLevel, options: VerboseLogOptions, args: Parameters<typeof console.log>) => string[];
    trace: (options: VerboseLogOptions, message?: any, ...optionalParams: any[]) => boolean | void;
    verbose: (options: VerboseLogOptions, message?: any, ...optionalParams: any[]) => boolean | void;
    info: (options: LogOptions, message?: any, ...optionalParams: any[]) => boolean | void;
    warn: (options: LogOptions, message?: any, ...optionalParams: any[]) => boolean | void;
    error: (options: VerboseLogOptions, message?: any, ...optionalParams: any[]) => boolean | void;
};
export {};
