import type { Page } from './browser/BrowserPage';
import type { StillImageFormat, VideoImageFormat } from './image-format';
export declare const takeFrame: ({ freePage, imageFormat, jpegQuality, width, height, output, scale, wantsBuffer, timeoutInMilliseconds, }: {
    freePage: Page;
    imageFormat: VideoImageFormat | StillImageFormat;
    jpegQuality: number | undefined;
    height: number;
    width: number;
    output: string | null;
    scale: number;
    wantsBuffer: boolean;
    timeoutInMilliseconds: number;
}) => Promise<Buffer | null>;
