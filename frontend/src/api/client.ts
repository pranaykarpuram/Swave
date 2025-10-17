/**
 * API Client
 * 
 * This module provides a type-safe wrapper around the mock API.
 * When you're ready to connect to your real backend, simply replace
 * the import statements to point to your actual API endpoints.
 */

import * as mocks from './mocks';
import type { FeedResponse, Playlist, PlaylistDetail, AuthProvider } from './types';

export const api = {
  feed: {
    getNext: (): Promise<FeedResponse> => mocks.mockFetchNextFeed(),
  },
  
  events: {
    save: (trackId: string, type: 'like' | 'reject'): Promise<void> => 
      mocks.mockSaveEvent(trackId, type),
  },
  
  playlists: {
    list: (): Promise<Playlist[]> => mocks.mockListPlaylists(),
    get: (id: string): Promise<PlaylistDetail> => mocks.mockGetPlaylist(id),
    generateDaily: (): Promise<PlaylistDetail> => mocks.mockGenerateDailyPlaylist(),
    export: (id: string): Promise<{ ok: true }> => mocks.mockExportPlaylist(id),
  },
  
  auth: {
    connect: (provider: AuthProvider): Promise<{ ok: true }> => 
      mocks.mockAuthConnect(provider),
    refreshTaste: (): Promise<{ ok: true }> => mocks.mockRefreshTaste(),
  },
};
