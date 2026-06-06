import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface UploadImageResponse {
  image_path: string;
}

@Injectable({
  providedIn: 'root'
})
export class UploadService {
  private apiUrl = 'https://demokratyczny-backend.azurewebsites.net/api/upload';
  private baseUrl = 'https://demokratyczny-backend.azurewebsites.net';

  readonly maxFileSizeBytes = 5 * 1024 * 1024;
  readonly acceptedMimeTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'];

  constructor(private http: HttpClient) {}

  uploadImage(file: File): Observable<UploadImageResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<UploadImageResponse>(`${this.apiUrl}/image`, formData);
  }

  deleteImage(path: string): Observable<void> {
    const params = new HttpParams().set('path', path);
    return this.http.delete<void>(`${this.apiUrl}/image`, { params });
  }

  beaconCleanup(paths: string[]): void {
    if (paths.length === 0) {
      return;
    }
    const token = localStorage.getItem('token');
    if (!token) {
      return;
    }
    const url = `${this.apiUrl}/cleanup?token=${encodeURIComponent(token)}`;
    const blob = new Blob([JSON.stringify(paths)], { type: 'application/json' });
    navigator.sendBeacon(url, blob);
  }

  getImageUrl(path: string | null | undefined): string | null {
    if (!path) {
      return null;
    }
    return `${this.baseUrl}/${path}`;
  }

  validateFile(file: File): string | null {
    if (!this.acceptedMimeTypes.includes(file.type)) {
      return 'Nieobsługiwany format pliku. Dozwolone: JPG, PNG, GIF, WEBP, BMP.';
    }
    if (file.size > this.maxFileSizeBytes) {
      return `Plik jest zbyt duży (max ${this.maxFileSizeBytes / (1024 * 1024)} MB).`;
    }
    return null;
  }
}