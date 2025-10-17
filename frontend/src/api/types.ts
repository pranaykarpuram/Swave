export type Track = {
  id: string;
  title: string;
  artist: string;
  album: string;
  artworkUrl: string;
  previewUrl: string | null;
  reasons?: string[];
};

export type FeedResponse = {
  batchId: string;
  tracks: Track[];
};

export type Playlist = {
  id: string;
  name: string;
  trackCount: number;
  updatedAt: string;
};

export type PlaylistDetail = {
  id: string;
  name: string;
  tracks: Track[];
};

export type SwipeEvent = {
  trackId: string;
  type: 'like' | 'reject';
  timestamp: number;
};

export type AuthProvider = 'spotify' | 'apple';
