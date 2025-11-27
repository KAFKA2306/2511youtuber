export declare const Log: {
    formatLogs: (logLevel: import("@remotion/renderer").LogLevel, options: import("@remotion/renderer").LogOptions & {
        tag?: string;
    }, args: Parameters<typeof console.log>) => string[];
    trace: (options: import("@remotion/renderer").LogOptions & {
        tag?: string;
    }, message?: any, ...optionalParams: any[]) => boolean | void;
    verbose: (options: import("@remotion/renderer").LogOptions & {
        tag?: string;
    }, message?: any, ...optionalParams: any[]) => boolean | void;
    info: (options: import("@remotion/renderer").LogOptions, message?: any, ...optionalParams: any[]) => boolean | void;
    warn: (options: import("@remotion/renderer").LogOptions, message?: any, ...optionalParams: any[]) => boolean | void;
    error: (options: import("@remotion/renderer").LogOptions & {
        tag?: string;
    }, message?: any, ...optionalParams: any[]) => boolean | void;
};
