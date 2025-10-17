import { useEffect, useState, useCallback, useRef } from 'react';
import { useFeedStore } from '@/store/feed';
import { useUIStore } from '@/store/ui';
import { api } from '@/api/client';
import { SwipeCard } from '@/components/SwipeCard';
import { Loader2 } from 'lucide-react';

export const Feed = () => {
  const { queue, loading, fetchIfLow, consumeTop } = useFeedStore();
  const toast = useUIStore((state) => state.toast);
  const [isPlaying, setIsPlaying] = useState(false);
  const [progress, setProgress] = useState(0);
  const audioRef = useRef<HTMLAudioElement | null>(null);
  const progressInterval = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    fetchIfLow();
  }, [fetchIfLow]);

  const handlePlayPreview = useCallback((url: string | null) => {
    // Stop current audio
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
      setIsPlaying(false);
      setProgress(0);
    }

    if (progressInterval.current) {
      clearInterval(progressInterval.current);
      progressInterval.current = null;
    }

    if (!url) {
      toast('No preview available for this track');
      return;
    }

    // Create and play new audio
    const audio = new Audio(url);
    audioRef.current = audio;

    audio.play().then(() => {
      setIsPlaying(true);

      // Update progress
      progressInterval.current = setInterval(() => {
        if (audio.duration) {
          const prog = (audio.currentTime / audio.duration) * 100;
          setProgress(prog);

          if (audio.ended) {
            setIsPlaying(false);
            setProgress(0);
            if (progressInterval.current) {
              clearInterval(progressInterval.current);
            }
          }
        }
      }, 100);
    }).catch(() => {
      toast('Failed to play preview');
    });

    return () => {
      audio.pause();
      if (progressInterval.current) {
        clearInterval(progressInterval.current);
      }
    };
  }, [toast]);

  const handlePlayPause = () => {
    if (!audioRef.current) return;

    if (isPlaying) {
      audioRef.current.pause();
      setIsPlaying(false);
    } else {
      audioRef.current.play();
      setIsPlaying(true);
    }
  };

  const handleSwipe = async (type: 'like' | 'reject') => {
    consumeTop(async (track) => {
      await api.events.save(track.id, type);
      toast(type === 'like' ? '❤️ Liked!' : '✕ Passed');
    });
  };

  if (loading && queue.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <Loader2 className="w-12 h-12 text-primary animate-spin" />
      </div>
    );
  }

  if (queue.length === 0) {
    return (
      <div className="min-h-screen flex flex-col bg-background">
        <div className="flex-1 flex items-center justify-center p-6">
          <div className="text-center space-y-4">
            <h2 className="text-2xl font-bold text-foreground">No more tracks!</h2>
            <p className="text-muted-foreground">Check back later for new recommendations</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col bg-background">
      {/* Header */}
      <header className="p-6 text-center">
        <h1 className="text-2xl font-bold text-foreground">Discover</h1>
      </header>

      {/* Card Stack */}
      <div className="flex-1 relative px-4 pb-8">
        {queue.slice(0, 3).map((track, index) => (
          <div
            key={track.id}
            className="absolute inset-0"
            style={{
              zIndex: 3 - index,
              transform: `scale(${1 - index * 0.05}) translateY(${index * -10}px)`,
              opacity: index === 0 ? 1 : 0.5,
              pointerEvents: index === 0 ? 'auto' : 'none',
            }}
          >
            {index === 0 && (
              <SwipeCard
                track={track}
                onSwipeLeft={() => handleSwipe('reject')}
                onSwipeRight={() => handleSwipe('like')}
                onPlayPreview={handlePlayPreview}
              />
            )}
            {index > 0 && (
              <div className="w-full max-w-md h-[600px] mx-auto bg-card rounded-3xl shadow-card" />
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
