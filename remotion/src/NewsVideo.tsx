import React from 'react';
import { AbsoluteFill, Audio, useCurrentFrame, useVideoConfig, Img, interpolate } from 'remotion';

export interface Subtitle {
    start: number;
    end: number;
    text: string;
}

export interface Scene {
    timestamp: number;
    imagePath: string;
}

export interface NewsVideoProps {
    subtitles: Subtitle[];
    audioUrl: string;
    scenes?: Scene[];
}

export const NewsVideo: React.FC<NewsVideoProps> = ({ subtitles, audioUrl, scenes = [] }) => {
    const frame = useCurrentFrame();
    const { fps } = useVideoConfig();
    const time = frame / fps;

    // Find current subtitle based on time
    const currentSubtitle = subtitles.find(
        (s) => time >= s.start && time < s.end
    );

    // Find current scene based on time
    const currentScene = scenes.length > 0
        ? scenes.reduce((prev, curr) => {
            return (curr.timestamp <= time && curr.timestamp > prev.timestamp) ? curr : prev;
        }, scenes[0])
        : null;

    // Calculate ken-burns zoom effect
    const sceneIndex = currentScene ? scenes.indexOf(currentScene) : 0;
    const sceneStartFrame = currentScene ? currentScene.timestamp * fps : 0;
    const framesSinceSceneStart = frame - sceneStartFrame;
    const zoom = interpolate(
        framesSinceSceneStart,
        [0, 300], // 10 seconds at 30fps
        [1.0, 1.1],
        { extrapolateRight: 'clamp' }
    );

    return (
        <AbsoluteFill style={{ backgroundColor: '#1a1a2e' }}>
            {/* Scene background image */}
            {currentScene && (
                <AbsoluteFill>
                    <Img
                        src={currentScene.imagePath}
                        style={{
                            width: '100%',
                            height: '100%',
                            objectFit: 'cover',
                            transform: `scale(${zoom})`,
                            opacity: 0.85,
                        }}
                    />
                    {/* Dark overlay for better subtitle readability */}
                    <AbsoluteFill style={{ backgroundColor: 'rgba(0, 0, 0, 0.3)' }} />
                </AbsoluteFill>
            )}

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
