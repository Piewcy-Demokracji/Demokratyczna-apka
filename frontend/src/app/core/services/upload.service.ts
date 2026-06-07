import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface UploadImageResponse {
  image_path: string;
}

@Injectable({
  providedIn: 'root'
})
/** Service for image uploads and storage helper utilities used throughout the app. */
export class UploadService {
  private apiUrl = 'https://demokratyczny-backend.azurewebsites.net/api/upload';
  private baseUrl = 'https://demokratyczny-backend.azurewebsites.net';

  readonly maxFileSizeBytes = 5 * 1024 * 1024;
  readonly acceptedMimeTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp', 'image/bmp'];

  constructor(private http: HttpClient) {}

  /**
   * Upload an image file to the backend and receive a stored image path.
   *
   * @param file The image file to upload.
   * @returns An observable containing the upload response with image_path.
   */
  uploadImage(file: File): Observable<UploadImageResponse> {
    const formData = new FormData();
    formData.append('file', file);
    return this.http.post<UploadImageResponse>(`${this.apiUrl}/image`, formData);
  }

  /**
   * Request deletion of an unreferenced uploaded image.
   *
   * @param path The image path to delete.
   * @returns An observable that completes when deletion succeeds.
   */
  deleteImage(path: string): Observable<void> {
    const params = new HttpParams().set('path', path);
    return this.http.delete<void>(`${this.apiUrl}/image`, { params });
  }

  /**
   * Build a publicly accessible URL for an uploaded image path.
   *
   * @param path The stored image path.
   * @returns A full image URL or null when no path is provided.
   */
  getImageUrl(path: string | null | undefined): string | null {
    if (!path) {
      return null;
    }
    return `${this.baseUrl}/${path}`;
  }

  /**
   * Validate selected image file type and size.
   *
   * @param file The selected file to validate.
   * @returns A validation error string or null when the file is valid.
   */
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