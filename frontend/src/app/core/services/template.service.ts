import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface TemplateOption {
  id: number;
  text: string;
  image_path?: string | null;
}

export interface TemplateOptionInput {
  text: string;
  image_path?: string | null;
}

export interface Template {
  id: number;
  title: string;
  description?: string;
  can_be_public: boolean;
  is_publish?: boolean;
  created_by: number;
  creator_username?: string;
  options: TemplateOption[];
}

export interface CreateTemplateRequest {
  title: string;
  description?: string;
  can_be_public: boolean;
  options: TemplateOptionInput[];
}

@Injectable({
  providedIn: 'root'
})
export class TemplateService {
  private apiUrl = 'https://demokratyczny-backend.azurewebsites.net/api/templates';

  constructor(private http: HttpClient) {}

  getTemplates(filter?: string): Observable<Template[]> {
    const options = filter ? { params: { filter } } : {};
    return this.http.get<Template[]>(this.apiUrl, options);
  }

  getTemplate(id: number): Observable<Template> {
    return this.http.get<Template>(`${this.apiUrl}/${id}`);
  }

  createTemplate(template: CreateTemplateRequest): Observable<Template> {
    return this.http.post<Template>(this.apiUrl, template);
  }

  updateTemplate(id: number, template: CreateTemplateRequest): Observable<Template> {
    return this.http.put<Template>(`${this.apiUrl}/${id}`, template);
  }

  updateTemplateCanBePublic(id: number, canBePublic: boolean): Observable<Template> {
    return this.http.patch<Template>(`${this.apiUrl}/${id}/can-be-public`, null, {
      params: { can_be_public: String(canBePublic) }
    });
  }

  deleteTemplate(id: number): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${id}`);
  }

  publishTemplate(id: number): Observable<{id: number; message: string}> {
    return this.http.post<{id: number; message: string}>(`${this.apiUrl}/${id}/publish`, {});
  }

  getAdminReviewTemplates(): Observable<Template[]> {
    return this.http.get<Template[]>(`${this.apiUrl}/admin/review`);
  }

  getAdminReviewTemplate(id: number): Observable<Template> {
    return this.http.get<Template>(`${this.apiUrl}/admin/review/${id}`);
  }

  getPublicTemplates(): Observable<Template[]> {
    return this.http.get<Template[]>(`${this.apiUrl}/public`);
  }

  publishFromAdminReview(id: number): Observable<{id: number; message: string}> {
    return this.http.post<{id: number; message: string}>(`${this.apiUrl}/admin/review/${id}/publish`, {});
  }

  rejectFromAdminReview(id: number): Observable<{message: string}> {
    return this.http.post<{message: string}>(`${this.apiUrl}/admin/review/${id}/reject`, {});
  }
}