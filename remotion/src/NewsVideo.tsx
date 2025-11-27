import React from 'react';
import { AbsoluteFill, Audio, useCurrentFrame, useVideoConfig } from 'remotion';

export interface Subtitle {
    start: number;
    end: number;
    text: string;
}

export interface NewsVideoProps {
    subtitles: Subtitle[];
    audioUrl: string;
}

export const NewsVideo: React.FC<NewsVideoProps> = ({ subtitles, audioUrl }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();
    const time = frame / fps;

    // Find current subtitle based on time
    const currentSubtitle = subtitles.find(
        (s) => time >= s.start && time < s.end
    );

    return (
        <AbsoluteFill style={{ backgroundColor: '#1a1a2e' }}>
            {audioUrl && <Audio src={audioUrl} />}

            {/* Subtitle display */}
            {currentSubtitle && (
                <div
                    style={{
                        position: 'absolute',
                        bottom: 100,
                        width: '100%',
                        textAlign: 'center',
                        padding: '0 80px',
                    }}
                >
                    <div
                        style={{
                            display: 'inline-block',
                            backgroundColor: 'rgba(0, 0, 0, 0.8)',
                            color: 'white',
                            fontSize: 48,
                            fontWeight: 'bold',
                            padding: '20px 40px',
                            borderRadius: 8,
                            lineHeight: 1.4,
                        }}
                    >
                        {currentSubtitle.text}
                    </div>
                </div>
            )}

            {/* Brand watermark */}
            <div
                style={{
                    position: 'absolute',
                    top: 40,
                    right: 40,
                    fontSize: 24,
                    color: 'rgba(255, 255, 255, 0.6)',
                    fontWeight: 'bold',
                }}
            >
                2511youtuber
            </div>
        </AbsoluteFill>
    );
};
