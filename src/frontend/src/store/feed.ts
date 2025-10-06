import { create } from 'zustand';
import { Track } from '@/api/types';
import { api } from '@/api/client';

interface FeedState {
  queue: Track[];
  loading: boolean;
  error: string | null;
  fetchIfLow: () => Promise<void>;
  consumeTop: (onSwipe: (track: Track) => void) => void;
  reset: () => void;
}

const MIN_QUEUE_SIZE = 3;

export const useFeedStore = create<FeedState>((set, get) => ({
  queue: [],
  loading: false,
  error: null,
  
  fetchIfLow: async () => {
    const { queue, loading } = get();
    
    if (loading || queue.length >= MIN_QUEUE_SIZE) {
      return;
    }
    
    set({ loading: true, error: null });
    
    try {
      const response = await api.feed.getNext();
      set((state) => ({
        queue: [...state.queue, ...response.tracks],
        loading: false,
      }));
    } catch (error) {
      set({
        loading: false,
        error: error instanceof Error ? error.message : 'Failed to fetch tracks',
      });
    }
  },
  
  consumeTop: (onSwipe) => {
    const { queue } = get();
    
    if (queue.length === 0) return;
    
    const [top, ...rest] = queue;
    onSwipe(top);
    set({ queue: rest });
    
    // Automatically fetch more if running low
    if (rest.length < MIN_QUEUE_SIZE) {
      get().fetchIfLow();
    }
  },
  
  reset: () => set({ queue: [], loading: false, error: null }),
}));
