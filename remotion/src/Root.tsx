import { Composition } from 'remotion';
import { NewsVideo } from './NewsVideo';

export const RemotionRoot: React.FC = () => {
    return (
        <>
            <Composition
                id="NewsVideo"
                component={NewsVideo}
                durationInFrames={300}
                fps={30}
                width={1920}
                height={1080}
                defaultProps={{
                    subtitles: [],
                    audioUrl: '',
                }}
            />
        </>
    );
};
